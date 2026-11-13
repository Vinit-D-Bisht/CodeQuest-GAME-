import hashlib
import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(BASE_DIR, "codequest.db")

SAVE_JSON = os.path.join(DATA_DIR, "save.json")
STATS_JSON = os.path.join(DATA_DIR, "stats.json")
SETTINGS_JSON = os.path.join(DATA_DIR, "settings.json")
LEADERBOARD_JSON = os.path.join(DATA_DIR, "leaderboard.json")

_current_user_id = None

PLAYER_DEFAULT = {
    "player": "",
    "xp": 0,
    "coins": 0,
    "avatar": "😎",
    "last_reward": "",
}

STATS_DEFAULT = {
    "games_played": 0,
    "questions_answered": 0,
    "correct_answers": 0,
}

SETTINGS_DEFAULT = {
    "sound": True,
    "timer": True,
}


def get_current_user_id():
    return _current_user_id


def set_current_user_id(user_id):
    global _current_user_id
    _current_user_id = user_id


def _now():
    return datetime.now().isoformat(timespec="seconds")


def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120000,
    )
    return f"{salt}${digest.hex()}"


def verify_password(password, stored):
    if not stored or "$" not in stored:
        return False
    salt, _digest = stored.split("$", 1)
    return secrets.compare_digest(hash_password(password, salt), stored)


def xp_to_level(xp):
    try:
        xp = int(xp)
    except (TypeError, ValueError):
        xp = 0
    if xp < 100:
        return 1
    if xp < 250:
        return 2
    if xp < 500:
        return 3
    if xp < 1000:
        return 4
    if xp < 2000:
        return 5
    return 6


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL DEFAULT '',
                coins INTEGER NOT NULL DEFAULT 0,
                xp INTEGER NOT NULL DEFAULT 0,
                level INTEGER NOT NULL DEFAULT 1,
                avatar TEXT NOT NULL DEFAULT '😎',
                last_reward TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                last_login TEXT
            );

            CREATE TABLE IF NOT EXISTS stats (
                user_id INTEGER PRIMARY KEY,
                games_played INTEGER NOT NULL DEFAULT 0,
                questions_answered INTEGER NOT NULL DEFAULT 0,
                correct_answers INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS settings (
                user_id INTEGER PRIMARY KEY,
                sound INTEGER NOT NULL DEFAULT 1,
                timer INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                language TEXT NOT NULL,
                level INTEGER NOT NULL,
                score INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                UNIQUE (user_id, language, level),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                badge TEXT NOT NULL,
                unlocked_at TEXT NOT NULL,
                UNIQUE (user_id, badge),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS leaderboard (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT NOT NULL UNIQUE,
                score INTEGER NOT NULL,
                best_score INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        _ensure_leaderboard_schema(conn)


def _ensure_leaderboard_schema(conn):
    columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(leaderboard)").fetchall()
    }
    if "best_score" not in columns:
        conn.execute(
            "ALTER TABLE leaderboard ADD COLUMN best_score INTEGER NOT NULL DEFAULT 0"
        )
        conn.execute(
            "UPDATE leaderboard SET best_score = score WHERE best_score = 0 AND score > 0"
        )
        conn.execute(
            "UPDATE leaderboard SET best_score = score WHERE best_score IS NULL"
        )

    rows = conn.execute(
        """
        SELECT id, name, COALESCE(best_score, score, 0) AS s
        FROM leaderboard
        ORDER BY name ASC, s DESC, id ASC
        """
    ).fetchall()
    seen = set()
    extra_ids = []
    for row in rows:
        name = row["name"]
        if name in seen:
            extra_ids.append(row["id"])
        else:
            seen.add(name)
    if extra_ids:
        conn.execute(
            f"DELETE FROM leaderboard WHERE id IN ({','.join('?' * len(extra_ids))})",
            extra_ids,
        )

    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_leaderboard_name ON leaderboard(name)"
    )


def _upsert_leaderboard(conn, user_id, name, score):
    name = (name or "").strip()
    if not name:
        return
    try:
        score = int(score)
    except (TypeError, ValueError):
        return

    conn.execute(
        """
        INSERT INTO leaderboard (user_id, name, score, best_score, created_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            best_score = MAX(leaderboard.best_score, excluded.best_score),
            score = MAX(leaderboard.score, excluded.score),
            user_id = COALESCE(excluded.user_id, leaderboard.user_id)
        """,
        (user_id, name, score, score, _now()),
    )


def _trim_leaderboard(conn):
    rows = conn.execute(
        """
        SELECT id FROM leaderboard
        ORDER BY COALESCE(best_score, score) DESC, id ASC
        """
    ).fetchall()
    extra_ids = [row["id"] for row in rows[10:]]
    if extra_ids:
        conn.execute(
            f"DELETE FROM leaderboard WHERE id IN ({','.join('?' * len(extra_ids))})",
            extra_ids,
        )


def _meta_get(conn, key):
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def _meta_set(conn, key, value):
    conn.execute(
        "INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )


def _load_json_file(path, fallback):
    if not os.path.exists(path):
        return fallback
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
    except (json.JSONDecodeError, OSError):
        return fallback
    return data if data is not None else fallback


def _create_user_row(conn, username, password_hash, coins=0, xp=0, avatar="😎", last_reward=""):
    now = _now()
    cur = conn.execute(
        """
        INSERT INTO users (
            username, password_hash, coins, xp, level, avatar, last_reward, created_at, last_login
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            username,
            password_hash,
            int(coins),
            int(xp),
            xp_to_level(xp),
            avatar or "😎",
            last_reward or "",
            now,
            None,
        ),
    )
    user_id = cur.lastrowid
    conn.execute(
        "INSERT INTO stats (user_id, games_played, questions_answered, correct_answers) VALUES (?, 0, 0, 0)",
        (user_id,),
    )
    conn.execute(
        "INSERT INTO settings (user_id, sound, timer) VALUES (?, 1, 1)",
        (user_id,),
    )
    return user_id


def migrate_json_if_needed():
    init_db()
    with get_connection() as conn:
        if _meta_get(conn, "json_migrated") == "1":
            return

        save_data = _load_json_file(SAVE_JSON, {})
        stats_data = _load_json_file(STATS_JSON, {})
        settings_data = _load_json_file(SETTINGS_JSON, {})
        board = _load_json_file(LEADERBOARD_JSON, [])

        username = ""
        if isinstance(save_data, dict):
            username = str(save_data.get("player", "")).strip()

        user_id = None
        if username:
            existing = conn.execute(
                "SELECT id FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            if existing:
                user_id = existing["id"]
            else:
                user_id = _create_user_row(
                    conn,
                    username=username,
                    password_hash="",
                    coins=save_data.get("coins", 0) if isinstance(save_data, dict) else 0,
                    xp=save_data.get("xp", 0) if isinstance(save_data, dict) else 0,
                    avatar=save_data.get("avatar", "😎") if isinstance(save_data, dict) else "😎",
                    last_reward=save_data.get("last_reward", "") if isinstance(save_data, dict) else "",
                )

            if isinstance(stats_data, dict):
                conn.execute(
                    """
                    UPDATE stats
                    SET games_played = ?, questions_answered = ?, correct_answers = ?
                    WHERE user_id = ?
                    """,
                    (
                        int(stats_data.get("games_played", 0) or 0),
                        int(stats_data.get("questions_answered", 0) or 0),
                        int(stats_data.get("correct_answers", 0) or 0),
                        user_id,
                    ),
                )

            if isinstance(settings_data, dict):
                conn.execute(
                    "UPDATE settings SET sound = ?, timer = ? WHERE user_id = ?",
                    (
                        1 if settings_data.get("sound", True) else 0,
                        1 if settings_data.get("timer", True) else 0,
                        user_id,
                    ),
                )

        if isinstance(board, list):
            for entry in board:
                if not isinstance(entry, dict):
                    continue
                name = str(entry.get("name", "")).strip()
                if not name:
                    continue
                try:
                    score = int(entry.get("score", 0) or 0)
                except (TypeError, ValueError):
                    continue
                row = conn.execute(
                    "SELECT id FROM users WHERE username = ?",
                    (name,),
                ).fetchone()
                _upsert_leaderboard(conn, row["id"] if row else None, name, score)

        _meta_set(conn, "json_migrated", "1")


def _ensure_related_rows(conn, user_id):
    conn.execute(
        "INSERT OR IGNORE INTO stats (user_id, games_played, questions_answered, correct_answers) VALUES (?, 0, 0, 0)",
        (user_id,),
    )
    conn.execute(
        "INSERT OR IGNORE INTO settings (user_id, sound, timer) VALUES (?, 1, 1)",
        (user_id,),
    )


def register_user(username, password):
    username = (username or "").strip()
    if not username:
        return False, "Please enter a username."
    if not password:
        return False, "Please enter a password."

    init_db()
    try:
        with get_connection() as conn:
            existing = conn.execute(
                "SELECT id FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            if existing:
                return False, "That username is already taken."
            user_id = _create_user_row(
                conn,
                username=username,
                password_hash=hash_password(password),
            )
            conn.execute(
                "UPDATE users SET last_login = ? WHERE id = ?",
                (_now(), user_id),
            )
    except sqlite3.IntegrityError:
        return False, "That username is already taken."

    set_current_user_id(user_id)
    return True, "Account created."


def login_user(username, password):
    username = (username or "").strip()
    if not username:
        return False, "Please enter a username."
    if not password:
        return False, "Please enter a password."

    init_db()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if not row:
            return False, "Account not found. Register first."

        stored = row["password_hash"] or ""
        if stored:
            if not verify_password(password, stored):
                return False, "Incorrect password."
        else:
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (hash_password(password), row["id"]),
            )

        conn.execute(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (_now(), row["id"]),
        )
        user_id = row["id"]
        _ensure_related_rows(conn, user_id)

    set_current_user_id(user_id)
    return True, "Logged in."


def logout_user():
    set_current_user_id(None)


def load_player():
    user_id = get_current_user_id()
    if not user_id:
        return PLAYER_DEFAULT.copy()

    init_db()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT username, xp, coins, avatar, last_reward FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

    if not row:
        logout_user()
        return PLAYER_DEFAULT.copy()

    return {
        "player": row["username"] or "",
        "xp": int(row["xp"] or 0),
        "coins": int(row["coins"] or 0),
        "avatar": row["avatar"] or PLAYER_DEFAULT["avatar"],
        "last_reward": row["last_reward"] or "",
    }


def save_player(data):
    user_id = get_current_user_id()
    if not user_id or not isinstance(data, dict):
        return

    xp = int(data.get("xp", 0) or 0)
    coins = int(data.get("coins", 0) or 0)
    avatar = data.get("avatar") or PLAYER_DEFAULT["avatar"]
    last_reward = data.get("last_reward") or ""

    init_db()
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE users
            SET xp = ?, coins = ?, level = ?, avatar = ?, last_reward = ?
            WHERE id = ?
            """,
            (xp, coins, xp_to_level(xp), avatar, last_reward, user_id),
        )


def load_stats():
    user_id = get_current_user_id()
    if not user_id:
        return STATS_DEFAULT.copy()

    init_db()
    with get_connection() as conn:
        _ensure_related_rows(conn, user_id)
        row = conn.execute(
            "SELECT games_played, questions_answered, correct_answers FROM stats WHERE user_id = ?",
            (user_id,),
        ).fetchone()

    if not row:
        return STATS_DEFAULT.copy()

    return {
        "games_played": int(row["games_played"] or 0),
        "questions_answered": int(row["questions_answered"] or 0),
        "correct_answers": int(row["correct_answers"] or 0),
    }


def save_stats(stats_data):
    user_id = get_current_user_id()
    if not user_id or not isinstance(stats_data, dict):
        return

    init_db()
    with get_connection() as conn:
        _ensure_related_rows(conn, user_id)
        conn.execute(
            """
            UPDATE stats
            SET games_played = ?, questions_answered = ?, correct_answers = ?
            WHERE user_id = ?
            """,
            (
                int(stats_data.get("games_played", 0) or 0),
                int(stats_data.get("questions_answered", 0) or 0),
                int(stats_data.get("correct_answers", 0) or 0),
                user_id,
            ),
        )


def load_settings():
    user_id = get_current_user_id()
    if not user_id:
        return SETTINGS_DEFAULT.copy()

    init_db()
    with get_connection() as conn:
        _ensure_related_rows(conn, user_id)
        row = conn.execute(
            "SELECT sound, timer FROM settings WHERE user_id = ?",
            (user_id,),
        ).fetchone()

    if not row:
        return SETTINGS_DEFAULT.copy()

    return {
        "sound": bool(row["sound"]),
        "timer": bool(row["timer"]),
    }


def save_settings(data):
    user_id = get_current_user_id()
    if not user_id or not isinstance(data, dict):
        return

    init_db()
    with get_connection() as conn:
        _ensure_related_rows(conn, user_id)
        conn.execute(
            "UPDATE settings SET sound = ?, timer = ? WHERE user_id = ?",
            (
                1 if data.get("sound", True) else 0,
                1 if data.get("timer", True) else 0,
                user_id,
            ),
        )


def load_leaderboard():
    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                name,
                MAX(COALESCE(best_score, score, 0)) AS score,
                MIN(id) AS sid
            FROM leaderboard
            GROUP BY name
            ORDER BY score DESC, sid ASC
            LIMIT 10
            """
        ).fetchall()
    return [{"name": row["name"], "score": int(row["score"])} for row in rows]


def save_leaderboard_all(board):
    init_db()
    if not isinstance(board, list):
        board = []

    with get_connection() as conn:
        conn.execute("DELETE FROM leaderboard")
        for entry in board[:10]:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("name", "")).strip()
            if not name:
                continue
            try:
                score = int(entry.get("score", 0) or 0)
            except (TypeError, ValueError):
                continue
            row = conn.execute(
                "SELECT id FROM users WHERE username = ?",
                (name,),
            ).fetchone()
            _upsert_leaderboard(conn, row["id"] if row else None, name, score)


def add_leaderboard_score(name, score):
    name = (name or "").strip()
    if not name:
        return
    try:
        score = int(score)
    except (TypeError, ValueError):
        return

    init_db()
    with get_connection() as conn:
        _upsert_leaderboard(conn, get_current_user_id(), name, score)
        _trim_leaderboard(conn)


def save_progress(language, level, score):
    user_id = get_current_user_id()
    if not user_id or not language:
        return

    init_db()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO progress (user_id, language, level, score, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, language, level)
            DO UPDATE SET score = excluded.score, updated_at = excluded.updated_at
            """,
            (user_id, language, int(level), int(score), _now()),
        )


def load_progress():
    user_id = get_current_user_id()
    if not user_id:
        return []

    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT language, level, score, updated_at FROM progress WHERE user_id = ? ORDER BY language, level",
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def unlock_achievements(badges):
    user_id = get_current_user_id()
    if not user_id or not badges:
        return

    init_db()
    now = _now()
    with get_connection() as conn:
        for badge in badges:
            conn.execute(
                """
                INSERT OR IGNORE INTO achievements (user_id, badge, unlocked_at)
                VALUES (?, ?, ?)
                """,
                (user_id, badge, now),
            )


def load_achievements():
    user_id = get_current_user_id()
    if not user_id:
        return []

    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT badge FROM achievements WHERE user_id = ? ORDER BY unlocked_at",
            (user_id,),
        ).fetchall()
    return [row["badge"] for row in rows]


def reset_current_user():
    user_id = get_current_user_id()
    if not user_id:
        return

    init_db()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT username FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        username = row["username"] if row else ""
        conn.execute(
            """
            UPDATE users
            SET coins = 0, xp = 0, level = 1, avatar = ?, last_reward = ''
            WHERE id = ?
            """,
            (PLAYER_DEFAULT["avatar"], user_id),
        )
        conn.execute(
            "UPDATE stats SET games_played = 0, questions_answered = 0, correct_answers = 0 WHERE user_id = ?",
            (user_id,),
        )
        conn.execute(
            "UPDATE settings SET sound = 1, timer = 1 WHERE user_id = ?",
            (user_id,),
        )
        conn.execute("DELETE FROM progress WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM achievements WHERE user_id = ?", (user_id,))
        if username:
            conn.execute("DELETE FROM leaderboard WHERE name = ?", (username,))


def delete_current_user():
    user_id = get_current_user_id()
    if not user_id:
        return False

    init_db()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT username FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        username = row["username"] if row else ""
        if username:
            conn.execute("DELETE FROM leaderboard WHERE name = ?", (username,))
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))

    logout_user()
    return True


init_db()
migrate_json_if_needed()
