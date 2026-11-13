import tkinter as tk
import game, save, achievements, leaderboard, stats, shop, sound, rank, splash, settings, random, database, theme
from datetime import date
from constants import *

root = tk.Tk()
root.title("CodeQuest")
root.attributes("-fullscreen", True)
root.configure(bg=BG)
root.bind("<Escape>", lambda e: root.attributes("-fullscreen", False))

lifeline_used = False
question_locked = False
selected_language = ""
level = 1
score = 0
current_question = 0
questions = []
player = {}

NO_SELECTION = "__none__"
selected_option = tk.StringVar(value=NO_SELECTION)

timer = 30
timer_job = None
player_name = ""

_anim_jobs = []
feedback_label = None
timer_label = None


def _cancel_anims():
    for job in _anim_jobs:
        try:
            root.after_cancel(job)
        except Exception:
            pass
    _anim_jobs.clear()


def _shutdown_tree(widget):
    try:
        if isinstance(widget, theme.ParticleCanvas):
            widget.shutdown()
        for child in list(widget.children.values()):
            _shutdown_tree(child)
    except tk.TclError:
        return


def clear():
    _cancel_anims()
    try:
        root.unbind("<Return>")
    except Exception:
        pass
    if timer_job:
        try:
            root.after_cancel(timer_job)
        except Exception:
            pass
    for widget in list(root.winfo_children()):
        _shutdown_tree(widget)
        try:
            widget.destroy()
        except tk.TclError:
            pass
    root.configure(bg=BG)


def schedule(ms, fn, *args):
    job = root.after(ms, fn, *args)
    _anim_jobs.append(job)
    return job


def stage():
    canvas = theme.ParticleCanvas(root, _anim_jobs)
    canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
    overlay = tk.Frame(root, bg=BG)
    overlay.place(relx=0, rely=0, relwidth=1, relheight=1)

    def reveal():
        try:
            overlay.destroy()
        except tk.TclError:
            pass
        try:
            canvas.lower()
        except tk.TclError:
            pass

    schedule(180, reveal)
    schedule(10, canvas.lower)
    return canvas


def hover_effect(button, normal, hover):
    button.configure(highlightthickness=2, highlightbackground=normal, bd=0, relief="flat")

    def on_enter(_e):
        button.config(bg=hover, highlightbackground=hover, activebackground=hover)

    def on_leave(_e):
        button.config(bg=normal, highlightbackground=normal, activebackground=normal)

    button.bind("<Enter>", on_enter)
    button.bind("<Leave>", on_leave)


def create_card(parent):
    wrap, inner = theme.glass_card(parent)
    wrap.inner = inner
    return wrap


def menu_button(parent, text, color, command):
    return theme.styled_button(parent, text, command, bg=color, hover=_lighten(color), width=22, height=2)


def _lighten(color):
    mapping = {
        GREEN: GLOW_GREEN,
        BLUE: GLOW_BLUE,
        PRIMARY: GLOW_BLUE,
        ORANGE: "#FBBF24",
        PURPLE: GLOW_PURPLE,
        GRAY: "#94A3B8",
        RED: "#F87171",
        GOLD: "#FDE047",
    }
    return mapping.get(color, GLOW_BLUE)


def confirm_exit():
    if theme.themed_confirm(root, "Exit CodeQuest", "Close CodeQuest now?", "Exit", "Stay"):
        root.destroy()


def page_header(parent, title, subtitle=None):
    bar = tk.Frame(parent, bg=SECONDARY, highlightbackground=GLASS_LINE, highlightthickness=2)
    bar.pack(fill="x", padx=28, pady=(18, 10))
    inner = tk.Frame(bar, bg=SECONDARY)
    inner.pack(fill="x", padx=18, pady=12)
    theme.section_title(inner, title, PRIMARY, 22, SECONDARY).pack(side="left")
    if subtitle:
        theme.muted_label(inner, subtitle, 12, SECONDARY).pack(side="left", padx=16)
    theme.styled_button(
        inner, "Exit", confirm_exit, bg=RED, hover="#F87171", width=8, height=1, font=(FONT, 10, "bold")
    ).pack(side="right")
    return inner


def icon_field(parent, icon, placeholder, show=None):
    row = tk.Frame(parent, bg=SECONDARY, highlightbackground=GLASS_LINE, highlightthickness=2, bd=0)
    row.pack(fill="x", pady=8)
    tk.Label(row, text=icon, font=(FONT, 14), bg=SECONDARY, fg=PRIMARY, width=3).pack(side="left", padx=(8, 0), pady=10)
    entry = tk.Entry(
        row,
        font=(FONT, 14),
        bg=SECONDARY,
        fg=MUTED,
        insertbackground=WHITE,
        relief="flat",
        bd=0,
        highlightthickness=0,
        show="" if show else "",
    )
    entry.pack(side="left", fill="x", expand=True, padx=8, pady=10)
    entry.insert(0, placeholder)
    entry._placeholder = placeholder
    entry._secret = show or ""
    entry._filled = False

    def apply_empty():
        entry.delete(0, "end")
        entry.insert(0, placeholder)
        entry.configure(fg=MUTED, show="")
        entry._filled = False

    def apply_active(clear=False):
        if clear or not entry._filled:
            entry.delete(0, "end")
        entry.configure(fg=WHITE, show=entry._secret)
        entry._filled = True

    def on_focus_in(_e):
        row.configure(highlightbackground=PRIMARY, highlightthickness=2)
        if not entry._filled:
            apply_active(clear=True)

    def on_focus_out(_e):
        row.configure(highlightbackground=GLASS_LINE, highlightthickness=2)
        if not entry.get():
            apply_empty()

    entry.bind("<FocusIn>", on_focus_in)
    entry.bind("<FocusOut>", on_focus_out)
    entry._apply_empty = apply_empty
    entry._apply_active = apply_active
    return row, entry


def field_value(entry):
    if not getattr(entry, "_filled", True):
        return ""
    value = entry.get().strip()
    if value == getattr(entry, "_placeholder", None):
        return ""
    return value


def count_up(label, prefix, target, suffix="", delay=18):
    state = {"n": 0}

    def tick():
        try:
            if not label.winfo_exists():
                return
            if state["n"] >= target:
                label.config(text=f"{prefix}{target}{suffix}")
                return
            state["n"] += max(1, target // 12)
            if state["n"] > target:
                state["n"] = target
            label.config(text=f"{prefix}{state['n']}{suffix}")
            schedule(delay, tick)
        except tk.TclError:
            return

    tick()


def auth_screen():
    clear()
    stage()

    shell = tk.Frame(root, bg=BG)
    shell.place(relx=0.5, rely=0.5, anchor="center")

    brand = tk.Frame(shell, bg=BG)
    brand.pack(side="left", padx=(0, 48))

    logo = tk.Label(brand, text="</>", font=(FONT_MONO, 72, "bold"), fg=PRIMARY, bg=BG)
    logo.pack(anchor="w")
    theme.pulse_label(logo, [PRIMARY, PURPLE, GLOW_BLUE, GLOW_PURPLE], _anim_jobs, 380)

    tk.Label(brand, text="CODEQUEST", font=(FONT, 42, "bold"), fg=WHITE, bg=BG).pack(anchor="w", pady=(4, 6))
    tk.Label(
        brand,
        text="Master the Code  •  Conquer the Quest",
        font=(FONT, 14),
        fg=MUTED,
        bg=BG,
    ).pack(anchor="w")

    keys = tk.Frame(brand, bg=BG)
    keys.pack(anchor="w", pady=18)
    for key in ("CODE", "QUEST", "XP", "LVL"):
        theme.kbd_key(keys, key).pack(side="left", padx=(0, 8))

    theme.muted_label(brand, "A premium coding quiz adventure", 11, BG).pack(anchor="w")

    wrap, card = theme.glass_card(shell, padx=40, pady=32)
    wrap.pack(side="left")

    tk.Label(card, text="Sign in", font=(FONT, 22, "bold"), fg=WHITE, bg=CARD).pack(anchor="w")
    theme.muted_label(card, "Login or create your explorer account", 12, CARD).pack(anchor="w", pady=(0, 14))

    _, user_entry = icon_field(card, "👤", "Username")
    pass_row, pass_entry = icon_field(card, "🔒", "Password", show="*")

    visible = {"on": False}

    def toggle_password():
        visible["on"] = not visible["on"]
        pass_entry._secret = "" if visible["on"] else "*"
        if pass_entry._filled:
            pass_entry.configure(show=pass_entry._secret)
        eye.configure(text="Hide" if visible["on"] else "Show")

    eye = tk.Button(
        pass_row,
        text="Show",
        command=toggle_password,
        bg=SECONDARY,
        fg=MUTED,
        bd=0,
        relief="flat",
        cursor="hand2",
        activebackground=SECONDARY,
        activeforeground=WHITE,
        font=(FONT, 10, "bold"),
        highlightthickness=0,
        width=5,
    )
    eye.pack(side="right", padx=8)

    error_label = tk.Label(card, text="", font=(FONT, 11), fg=RED, bg=CARD, wraplength=320, justify="left")
    error_label.pack(anchor="w", pady=(2, 8))

    def show_auth_error(message):
        error_label.config(text=message)
        theme.pulse_label(error_label, [RED, ORANGE, RED], _anim_jobs, 220)

    def do_login():
        global player_name
        ok, message = database.login_user(field_value(user_entry), field_value(pass_entry))
        if not ok:
            show_auth_error(message)
            return
        player_name = save.load_data().get("player", "")
        home()

    def do_register():
        global player_name
        ok, message = database.register_user(field_value(user_entry), field_value(pass_entry))
        if not ok:
            show_auth_error(message)
            return
        player_name = save.load_data().get("player", "")
        home()

    theme.styled_button(card, "Login", do_login, bg=PRIMARY, hover=GLOW_BLUE, width=28, height=1).pack(pady=(8, 8))
    theme.styled_button(card, "Register", do_register, bg=PURPLE, hover=GLOW_PURPLE, width=28, height=1).pack()

    hint = tk.Frame(card, bg=CARD)
    hint.pack(pady=(16, 4))
    theme.muted_label(hint, "Press", 10, CARD).pack(side="left")
    theme.kbd_key(hint, "Enter").pack(side="left", padx=8)
    theme.muted_label(hint, "to login", 10, CARD).pack(side="left")

    theme.styled_button(card, "Exit", confirm_exit, bg=SECONDARY, hover="#1F2A40", fg=MUTED, width=28, height=1).pack(
        pady=(12, 0)
    )

    root.bind("<Return>", lambda e: do_login())


def switch_user():
    global player_name
    database.logout_user()
    player_name = ""
    auth_screen()


def name_screen():
    clear()
    global player_name
    try:
        saved_player = save.load_data().get("player", "")
    except Exception:
        saved_player = ""
    if saved_player:
        player_name = saved_player
        return language_screen()

    stage()
    wrap, card = theme.glass_card(root, padx=32, pady=28)
    wrap.place(relx=0.5, rely=0.5, anchor="center")
    theme.section_title(card, "Welcome, explorer", GREEN, 24, CARD).pack()
    theme.muted_label(card, "Enter your name to begin your coding adventure", 13, CARD).pack(pady=10)
    _, name_entry = icon_field(card, "⌨", "Name")

    def save_name():
        global player_name
        player_name = field_value(name_entry)
        if not player_name:
            theme.themed_alert(root, "Name required", "Please enter your name.")
            return
        data = save.load_data()
        data["player"] = player_name
        save.save_data(data)
        language_screen()

    theme.styled_button(card, "Continue  ➜", save_name, bg=PRIMARY, width=24, height=1).pack(pady=16)
    theme.styled_button(card, "Back", home, bg=SECONDARY, hover="#1F2A40", fg=MUTED, width=24, height=1).pack()


def show_question():
    clear()
    global feedback_label, timer_label, timer, timer_job

    q = questions[current_question]
    selected_option.set(NO_SELECTION)
    if timer_job:
        root.after_cancel(timer_job)
        timer_job = None
    timer = 30

    stage()
    page_header(root, "QUEST", f"{selected_language}  •  Level {level}")

    shell, card = theme.glass_card(root, padx=36, pady=28)
    shell.pack(pady=8)

    top = tk.Frame(card, bg=CARD)
    top.pack(fill="x")
    tk.Label(top, text=f"👋  {player_name}", font=(FONT, 12), fg=MUTED, bg=CARD).pack(side="left")

    progress_chip = tk.Frame(top, bg=SECONDARY, highlightbackground=PRIMARY, highlightthickness=2, bd=0)
    progress_chip.pack(side="right", padx=(10, 0))
    tk.Label(
        progress_chip,
        text=f"Q  {current_question + 1} / 5",
        font=(FONT, 11, "bold"),
        fg=PRIMARY,
        bg=SECONDARY,
        padx=12,
        pady=6,
    ).pack()

    timer_enabled = settings.load()["timer"]
    timer_chip = tk.Frame(top, bg=SECONDARY, highlightbackground=GOLD, highlightthickness=2, bd=0)
    timer_chip.pack(side="right", padx=(0, 8))
    timer_label = tk.Label(
        timer_chip,
        text="⏳  30s" if timer_enabled else "⏳  OFF",
        font=(FONT, 13, "bold"),
        fg=GOLD,
        bg=SECONDARY,
        padx=12,
        pady=6,
    )
    timer_label.pack()

    track, fill = theme.progress_track(card)
    track.pack(fill="x", pady=(18, 12))
    theme.animate_bar(fill, (current_question + 1) / 5, _anim_jobs)

    tk.Label(card, text=f"Question {current_question + 1} of 5", font=(FONT, 12), fg=PRIMARY, bg=CARD).pack(anchor="w")
    tk.Label(
        card,
        text=q["question"],
        font=(FONT, 22, "bold"),
        wraplength=820,
        justify="left",
        fg=WHITE,
        bg=CARD,
    ).pack(anchor="w", pady=(8, 18))

    options_host = tk.Frame(card, bg=CARD)
    options_host.pack(fill="x")
    option_cards = []
    letters = "ABCD"

    def restyle_options(*_args):
        current = selected_option.get()
        for opt, wrap, key, accent, inner, rb in option_cards:
            selected = current == opt
            tone = "#1E2C48" if selected else SECONDARY
            wrap.configure(
                highlightbackground=PRIMARY if selected else GLASS_LINE,
                highlightthickness=2,
                bg=tone,
            )
            inner.configure(bg=tone)
            rb.configure(bg=tone, activebackground=tone)
            accent.configure(bg=PRIMARY if selected else CARD2)
            key.configure(highlightbackground=PRIMARY if selected else GLASS_LINE)

    for index, option in enumerate(q["options"]):
        wrap = tk.Frame(options_host, bg=SECONDARY, highlightbackground=GLASS_LINE, highlightthickness=2, bd=0)
        wrap._option_card = True
        accent = tk.Frame(wrap, bg=CARD2, width=6)
        accent.pack(side="left", fill="y")
        accent.pack_propagate(False)
        inner = tk.Frame(wrap, bg=SECONDARY)
        inner.pack(side="left", fill="x", expand=True, padx=8, pady=8)
        key = theme.kbd_key(inner, letters[index] if index < len(letters) else str(index + 1), SECONDARY)
        key.pack(side="left", padx=(4, 10))
        rb = tk.Radiobutton(
            inner,
            text=option,
            variable=selected_option,
            value=option,
            tristatevalue="__tristate__",
            font=(FONT, 16),
            fg=WHITE,
            bg=SECONDARY,
            selectcolor=CARD,
            activebackground=SECONDARY,
            activeforeground=WHITE,
            anchor="w",
            padx=8,
            pady=8,
            highlightthickness=0,
            bd=0,
            command=restyle_options,
        )
        rb.pack(side="left", fill="x", expand=True)
        wrap.pack(fill="x", pady=6)
        option_cards.append((option, wrap, key, accent, inner, rb))

        def on_enter(_e, w=wrap, current=option, a=accent):
            if selected_option.get() != current:
                w.configure(highlightbackground=GLOW_BLUE, highlightthickness=2)
                a.configure(bg=GLOW_BLUE)

        def on_leave(_e):
            restyle_options()

        def select_row(_e=None, value=option, button=rb):
            selected_option.set(value)
            button.select()
            restyle_options()

        wrap.bind("<Enter>", on_enter)
        wrap.bind("<Leave>", on_leave)
        wrap.bind("<Button-1>", select_row)
        inner.bind("<Button-1>", select_row)
        accent.bind("<Button-1>", select_row)

    selected_option.set(NO_SELECTION)
    restyle_options()

    actions = tk.Frame(card, bg=CARD)
    actions.pack(fill="x", pady=(22, 6))
    theme.styled_button(actions, "Next  ➜", game.submit_answer, bg=GREEN, hover=GLOW_GREEN, width=16, height=1).pack(
        side="left"
    )
    theme.styled_button(actions, "50 / 50", game.fifty_fifty, bg=PURPLE, hover=GLOW_PURPLE, width=12, height=1).pack(
        side="left", padx=10
    )
    theme.styled_button(actions, "Skip", game.skip_question, bg=ORANGE, hover="#FBBF24", width=12, height=1).pack(
        side="left"
    )

    feedback_label = tk.Label(card, text="", font=(FONT, 14, "bold"), bg=CARD, fg=MUTED, wraplength=780, justify="left")
    feedback_label.pack(fill="x", pady=(12, 0))

    def watch_timer():
        try:
            if not timer_label.winfo_exists():
                return
            if timer_enabled and timer <= 8:
                timer_label.configure(fg=RED)
                timer_chip.configure(highlightbackground=RED)
            else:
                timer_label.configure(fg=GOLD)
                timer_chip.configure(highlightbackground=GOLD)
            schedule(400, watch_timer)
        except tk.TclError:
            return

    watch_timer()
    if timer_enabled:
        game.countdown()


def show_result():
    clear()

    percentage = score * 20
    wrong = 5 - score
    data = save.load_data()
    player_rank = rank.get_rank(data["xp"])

    if settings.load()["sound"]:
        sound.win.play()

    if score == 5:
        data["xp"] += 50
        save.save_data(data)

    if player_name:
        leaderboard.save(player_name, score)

    database.save_progress(selected_language, level, score)
    badges = achievements.check(data, score, level)
    coins = score * 5

    stage()
    page_header(root, "LEVEL COMPLETE", f"{selected_language}  •  Level {level}")
    wrap, card = theme.glass_card(root, padx=32, pady=24)
    wrap.pack(pady=10)

    tk.Label(card, text=f"Great job, {player_name}", font=(FONT, 22, "bold"), fg=WHITE, bg=CARD).pack()
    tk.Label(card, text="⭐" * max(score, 0), font=(FONT, 26), fg=GOLD, bg=CARD).pack(pady=6)

    score_lbl = tk.Label(card, text="Score  0/5", font=(FONT, 20, "bold"), fg=GOLD, bg=CARD)
    score_lbl.pack(pady=(8, 2))
    count_up(score_lbl, "Score  ", score, "/5")

    xp_lbl = tk.Label(card, text="⭐  +0 XP", font=(FONT, 15, "bold"), fg=PRIMARY, bg=CARD)
    xp_lbl.pack()
    count_up(xp_lbl, "⭐  +", score * 10 + (50 if score == 5 else 0), " XP")

    coin_lbl = tk.Label(card, text="🪙  +0 coins", font=(FONT, 16, "bold"), fg=GOLD, bg=CARD)
    coin_lbl.pack()
    count_up(coin_lbl, "🪙  +", coins, " coins")

    stats_row = tk.Frame(card, bg=CARD)
    stats_row.pack(pady=12)
    for text, color in (
        (f"✅  {score} correct", GREEN),
        (f"❌  {wrong} wrong", RED),
        (f"🎯  {percentage}%", WHITE),
        (f"🏆  {player_rank}", GREEN),
    ):
        chip = tk.Label(stats_row, text=text, font=(FONT, 12, "bold"), fg=color, bg=SECONDARY, padx=12, pady=8)
        chip.pack(side="left", padx=6)

    if score == 5:
        bonus = tk.Label(card, text="🔥  PERFECT SCORE BONUS  +50 XP", font=(FONT, 14, "bold"), fg=ORANGE, bg=CARD)
        bonus.pack(pady=8)
        theme.pulse_label(bonus, [ORANGE, GOLD, GREEN], _anim_jobs, 260)

    if badges:
        popup = tk.Frame(card, bg=SECONDARY, highlightbackground=GOLD, highlightthickness=2, bd=0)
        popup.pack(fill="x", pady=10)
        title = tk.Label(popup, text="🏅  Achievements unlocked", font=(FONT, 14, "bold"), fg=GOLD, bg=SECONDARY)
        title.pack(pady=(10, 4))
        theme.pulse_label(title, [GOLD, WHITE, GOLD], _anim_jobs, 280)
        for badge in badges[:3]:
            tk.Label(popup, text=badge, font=(FONT, 12), fg=WHITE, bg=SECONDARY).pack()
        tk.Label(popup, text="", bg=SECONDARY).pack(pady=4)

    actions = tk.Frame(card, bg=CARD)
    actions.pack(pady=14)
    if level < 3:
        theme.styled_button(actions, "Continue  ➜", game.next_level, bg=PRIMARY, width=16, height=1).pack(
            side="left", padx=6
        )
    else:
        theme.styled_button(
            actions, "Finish Quest", game.next_level, bg=GREEN, hover=GLOW_GREEN, width=16, height=1
        ).pack(side="left", padx=6)
    theme.styled_button(
        actions, "Restart Level", lambda: game.start_game(selected_language, level), bg=ORANGE, hover="#FBBF24", width=16, height=1
    ).pack(side="left", padx=6)
    theme.styled_button(actions, "Home", home, bg=SECONDARY, hover="#1F2A40", fg=MUTED, width=12, height=1).pack(
        side="left", padx=6
    )


def language_screen():
    clear()
    stage()
    page_header(
        root,
        "SELECT A PATH",
        random.choice(
            [
                f"Welcome {player_name}",
                f"Good luck {player_name}",
                f"Ready to code, {player_name}?",
                f"Let's win, {player_name}",
            ]
        ),
    )

    wrap, card = theme.glass_card(root, padx=28, pady=22)
    wrap.pack(pady=12)
    theme.section_title(card, "Choose your programming language", WHITE, 22, CARD).pack()
    theme.muted_label(card, "Each language has 3 levels  •  5 random questions per level", 12, CARD).pack(pady=(4, 18))

    grid = tk.Frame(card, bg=CARD)
    grid.pack()
    languages = [
        ("🐍  Python", "Python", PRIMARY),
        ("☕  Java", "Java", ORANGE),
        ("⚙  C", "C", MUTED),
        ("🚀  C++", "C++", GREEN),
        ("💎  C#", "C#", PURPLE),
    ]
    for i, (text, value, color) in enumerate(languages):
        btn = theme.styled_button(
            grid,
            text,
            lambda lang=value: game.start_game(lang),
            bg=color,
            hover=_lighten(color),
            width=18,
            height=2,
        )
        btn.grid(row=i // 3, column=i % 3, padx=10, pady=10)

    theme.styled_button(card, "⬅  Back", home, bg=SECONDARY, hover="#1F2A40", fg=MUTED, width=16, height=1).pack(pady=16)


def home():
    if not database.get_current_user_id():
        return auth_screen()

    clear()
    global player_name
    data = save.load_data()
    player_name = data.get("player", "")
    today = str(date.today())
    granted_daily = data.get("last_reward") != today
    if granted_daily:
        data["last_reward"] = today
        data["coins"] += 20
        save.save_data(data)

    game_stats = stats.load()
    accuracy = stats.accuracy()
    player_rank = rank.get_rank(data["xp"])
    user_level = database.xp_to_level(data["xp"])
    streak = "1" if data.get("last_reward") == today else "0"

    stage()

    header = tk.Frame(root, bg=SECONDARY, highlightbackground=GLASS_LINE, highlightthickness=2)
    header.pack(fill="x", padx=28, pady=(16, 10))
    head_in = tk.Frame(header, bg=SECONDARY)
    head_in.pack(fill="x", padx=16, pady=12)

    greet = tk.Label(
        head_in,
        text=f"Welcome back, {data.get('player', 'Player')}",
        font=(FONT, 20, "bold"),
        fg=WHITE,
        bg=SECONDARY,
    )
    greet.pack(side="left")

    theme.styled_button(
        head_in, "Exit", confirm_exit, bg=RED, hover="#F87171", width=8, height=1, font=(FONT, 10, "bold")
    ).pack(side="right")
    theme.header_chip(head_in, f"🪙  {data['coins']}", GOLD, CARD).pack(side="right", padx=8)
    theme.header_chip(head_in, f"⭐  {data['xp']} XP", PRIMARY, CARD).pack(side="right", padx=6)
    theme.header_chip(head_in, f"LVL {user_level}", BG, GOLD).pack(side="right", padx=6)
    tk.Label(head_in, text=data.get("avatar", "😎"), font=(FONT, 22), bg=SECONDARY).pack(side="right", padx=8)

    body = tk.Frame(root, bg=BG)
    body.pack(pady=8, fill="both", expand=True)
    body.grid_columnconfigure(0, weight=1)
    body.grid_columnconfigure(1, weight=1)

    left_wrap, left = theme.glass_card(body, padx=26, pady=22)
    left_wrap.grid(row=0, column=0, padx=18, sticky="n")

    glow = tk.Frame(left, bg=CARD, highlightbackground=PRIMARY, highlightthickness=2, bd=0)
    glow.pack(pady=(4, 6))
    avatar = tk.Label(glow, text=data.get("avatar", "😎"), font=(FONT, 46), bg=CARD, fg=WHITE, padx=18, pady=10)
    avatar.pack()
    theme.pulse_label(avatar, [WHITE, GOLD, PRIMARY, PURPLE], _anim_jobs, 640)
    tk.Label(left, text=data.get("player", "Player"), font=(FONT, 22, "bold"), fg=WHITE, bg=CARD).pack()
    tk.Label(left, text=player_rank, font=(FONT, 13, "bold"), fg=GREEN, bg=CARD).pack(pady=4)
    badge = tk.Label(
        left,
        text=f"LEVEL {user_level}",
        font=(FONT, 11, "bold"),
        fg=BG,
        bg=GOLD,
        padx=12,
        pady=4,
    )
    badge.pack(pady=(2, 4))

    xp_max = 1000 if data["xp"] < 1000 else max(data["xp"], 2000)
    track, xp_fill = theme.progress_track(left)
    track.pack(fill="x", pady=14)
    theme.animate_bar(xp_fill, min(1.0, data["xp"] / xp_max), _anim_jobs)
    theme.muted_label(left, f"{data['xp']} XP  •  next milestone {xp_max}", 10, CARD).pack()

    meta = tk.Frame(left, bg=CARD)
    meta.pack(fill="x", pady=10)
    theme.stat_chip(meta, str(game_stats["games_played"]), "Games", WHITE).pack(side="left", expand=True, fill="x", padx=4)
    theme.stat_chip(meta, f"{accuracy}%", "Accuracy", GREEN).pack(side="left", expand=True, fill="x", padx=4)
    theme.stat_chip(meta, streak, "Today streak", GOLD).pack(side="left", expand=True, fill="x", padx=4)

    if granted_daily:
        bonus = tk.Label(left, text="🪙  Daily reward +20 coins", font=(FONT, 11, "bold"), fg=GOLD, bg=CARD)
        bonus.pack(pady=8)
        theme.pulse_label(bonus, [GOLD, WHITE], _anim_jobs, 300)

    menu = tk.Frame(left, bg=CARD)
    menu.pack(pady=14)
    actions = [
        ("▶  Start Quest", name_screen, GREEN),
        ("📊  Statistics", stats_screen, PRIMARY),
        ("🏆  Leaderboard", leaderboard_screen, ORANGE),
        ("🛒  Shop", shop_screen, PURPLE),
        ("⚙  Settings", settings_screen, GRAY),
    ]
    for i, (text, cmd, color) in enumerate(actions):
        btn = theme.styled_button(menu, text, cmd, bg=color, hover=_lighten(color), width=22, height=2)
        btn.grid(row=i // 2, column=i % 2, padx=8, pady=8)

    right_wrap, right = theme.glass_card(body, padx=22, pady=20)
    right_wrap.grid(row=0, column=1, padx=12, sticky="n")
    theme.section_title(right, "🏆  Top Players", GOLD, 18, CARD).pack(anchor="w", pady=(0, 10))
    board = leaderboard.load()[:5]
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    podium_bg = {0: PODIUM_GOLD, 1: PODIUM_SILVER, 2: PODIUM_BRONZE}
    if board:
        for i, entry in enumerate(board):
            row = tk.Frame(right, bg=podium_bg.get(i, SECONDARY), highlightbackground=GLASS_LINE, highlightthickness=2)
            row.pack(fill="x", pady=5)
            tk.Label(row, text=medals[i], font=(FONT, 16), bg=row["bg"], fg=WHITE, width=3).pack(side="left", padx=6, pady=10)
            tk.Label(row, text="😎", font=(FONT, 14), bg=row["bg"]).pack(side="left")
            tk.Label(row, text=entry["name"], font=(FONT, 13, "bold"), bg=row["bg"], fg=WHITE).pack(side="left", padx=8)
            tk.Label(row, text=f"{entry['score']}/5", font=(FONT, 12, "bold"), bg=row["bg"], fg=GOLD).pack(
                side="right", padx=10
            )
    else:
        theme.muted_label(right, "No scores yet", 13, CARD).pack(pady=20)

    tips = ["Practice daily", "Debug patiently", "Build projects", "Read errors carefully"]
    theme.muted_label(right, f"💡  {random.choice(tips)}", 11, CARD).pack(pady=(12, 4), anchor="w")
    theme.muted_label(root, "CodeQuest", 10, BG, MUTED).pack(side="bottom", pady=8)


def game_complete():
    clear()
    data = save.load_data()
    if "avatar" not in data:
        data["avatar"] = "😎"
        save.save_data(data)
    player_rank = rank.get_rank(data["xp"])

    stage()
    page_header(root, "QUEST COMPLETE")
    wrap, card = theme.glass_card(root, padx=32, pady=24)
    wrap.pack(pady=16)
    tk.Label(card, text="🏆  QUEST COMPLETE", font=(FONT, 28, "bold"), fg=GOLD, bg=CARD).pack()
    theme.pulse_label(card.winfo_children()[0], [GOLD, PRIMARY, GREEN], _anim_jobs)
    tk.Label(card, text=f"Congratulations, {data['player']}", font=(FONT, 18), fg=WHITE, bg=CARD).pack(pady=8)
    tk.Label(card, text=f"Rank  {player_rank}", font=(FONT, 14, "bold"), fg=GREEN, bg=CARD).pack()
    tk.Label(card, text=f"⭐  {data['xp']} XP", font=(FONT, 16), fg=PRIMARY, bg=CARD).pack(pady=4)
    tk.Label(card, text=f"🪙  {data['coins']} coins", font=(FONT, 16), fg=GOLD, bg=CARD).pack()
    tk.Label(card, text="🏅  Certified CodeQuest Explorer", font=(FONT, 16, "bold"), fg=GOLD, bg=CARD).pack(pady=16)

    actions = tk.Frame(card, bg=CARD)
    actions.pack()
    theme.styled_button(actions, "🏠  Home", home, bg=PRIMARY, width=14, height=1).pack(side="left", padx=6)
    theme.styled_button(
        actions, "🔄  Play Again", lambda: game.start_game(selected_language), bg=GREEN, hover=GLOW_GREEN, width=14, height=1
    ).pack(side="left", padx=6)
    theme.styled_button(actions, "Exit", confirm_exit, bg=SECONDARY, hover="#1F2A40", fg=MUTED, width=10, height=1).pack(
        side="left", padx=6
    )


def shop_screen():
    clear()
    data = save.load_data()
    stage()
    page_header(root, "SHOP", f"🪙  {data['coins']} coins")
    wrap, card = theme.glass_card(root, padx=28, pady=20)
    wrap.pack(pady=12)
    theme.muted_label(card, "Spend coins on boosts and badges", 12, CARD).pack(pady=(0, 12))
    for item in shop.items:
        row = tk.Frame(card, bg=SECONDARY, highlightbackground=GLASS_LINE, highlightthickness=2, bd=0)
        row.pack(fill="x", pady=6)
        tk.Label(row, text=item["name"], font=(FONT, 14, "bold"), fg=WHITE, bg=SECONDARY).pack(
            side="left", padx=14, pady=10
        )
        theme.styled_button(
            row,
            f"{item['price']} 🪙",
            lambda i=item: buy_item(i),
            bg=PRIMARY,
            hover=GLOW_BLUE,
            width=12,
            height=1,
        ).pack(side="right", padx=10, pady=6)
    theme.styled_button(card, "⬅  Home", home, bg=SECONDARY, hover="#1F2A40", fg=MUTED, width=16, height=1).pack(pady=16)


def buy_item(item):
    data = save.load_data()
    if data["coins"] < item["price"]:
        theme.themed_alert(root, "Shop", "Not enough coins.")
        return
    data["coins"] -= item["price"]
    if "Golden Badge" in item["name"]:
        data["avatar"] = "👑"
    elif "XP Booster" in item["name"]:
        data["xp"] += 50
    save.save_data(data)
    theme.themed_alert(root, "Shop", f"You bought {item['name']}!")
    shop_screen()


def settings_screen():
    clear()
    data = settings.load()
    profile = save.load_data()
    sound_var = tk.BooleanVar(value=data["sound"])
    timer_var = tk.BooleanVar(value=data["timer"])

    stage()
    page_header(root, "SETTINGS")
    body = tk.Frame(root, bg=BG)
    body.pack(pady=8)

    acc_wrap, acc = theme.glass_card(body, padx=24, pady=18)
    acc_wrap.grid(row=0, column=0, padx=12, sticky="n")
    theme.section_title(acc, "Account", PRIMARY, 18, CARD).pack(anchor="w", pady=(0, 8))
    for label, value in (
        ("Username", profile.get("player", "")),
        ("Current Level", str(database.xp_to_level(profile.get("xp", 0)))),
        ("Coins", str(profile.get("coins", 0))),
        ("XP", str(profile.get("xp", 0))),
    ):
        theme.info_row(acc, label, value).pack(fill="x", pady=6)

    def logout():
        switch_user()

    def delete_account():
        if not theme.themed_confirm(
            root,
            "Delete Account",
            "Permanently delete this account and its SQLite data? This cannot be undone.",
            "Delete",
            "Cancel",
        ):
            return
        database.delete_current_user()
        global player_name
        player_name = ""
        theme.themed_alert(root, "Account", "Your account has been deleted.")
        auth_screen()

    theme.styled_button(acc, "Logout", logout, bg=PRIMARY, width=22, height=1).pack(pady=(14, 6))
    theme.styled_button(acc, "Switch User", switch_user, bg=GRAY, hover="#94A3B8", width=22, height=1).pack(pady=6)
    theme.styled_button(acc, "Delete Account", delete_account, bg=RED, hover="#F87171", width=22, height=1).pack(pady=6)

    app_wrap, app = theme.glass_card(body, padx=24, pady=18)
    app_wrap.grid(row=0, column=1, padx=12, sticky="n")
    theme.section_title(app, "Application", GREEN, 18, CARD).pack(anchor="w", pady=(0, 8))

    tk.Checkbutton(
        app,
        text="Enable Sound",
        variable=sound_var,
        font=(FONT, 13),
        bg=CARD,
        fg=WHITE,
        selectcolor=SECONDARY,
        activebackground=CARD,
        activeforeground=WHITE,
        highlightthickness=0,
    ).pack(anchor="w", pady=6)
    tk.Checkbutton(
        app,
        text="Enable Timer",
        variable=timer_var,
        font=(FONT, 13),
        bg=CARD,
        fg=WHITE,
        selectcolor=SECONDARY,
        activebackground=CARD,
        activeforeground=WHITE,
        highlightthickness=0,
    ).pack(anchor="w", pady=6)

    def save_settings():
        settings.save({"sound": sound_var.get(), "timer": timer_var.get()})
        theme.themed_alert(root, "Settings", "Settings saved!")

    def reset_game():
        if theme.themed_confirm(root, "Reset", "Delete all progress for this account?", "Reset", "Cancel"):
            database.reset_current_user()
            global player_name
            player_name = save.load_data().get("player", "")
            home()

    def about():
        theme.themed_alert(
            root,
            "About CodeQuest",
            "CodeQuest is a coding quiz adventure.\nMaster the code. Conquer the quest.",
        )

    theme.styled_button(app, "Save Preferences", save_settings, bg=GREEN, hover=GLOW_GREEN, width=22, height=1).pack(
        pady=(12, 6)
    )
    theme.styled_button(app, "Reset Progress", reset_game, bg=ORANGE, hover="#FBBF24", width=22, height=1).pack(pady=6)
    theme.styled_button(app, "About CodeQuest", about, bg=PRIMARY, width=22, height=1).pack(pady=6)
    theme.styled_button(app, "Exit Application", confirm_exit, bg=RED, hover="#F87171", width=22, height=1).pack(pady=6)
    theme.styled_button(app, "⬅  Home", home, bg=SECONDARY, hover="#1F2A40", fg=MUTED, width=22, height=1).pack(pady=10)


def stats_screen():
    clear()
    game_stats = stats.load()
    accuracy = stats.accuracy()
    stage()
    page_header(root, "STATISTICS")
    wrap, card = theme.glass_card(root, padx=32, pady=24)
    wrap.pack(pady=16)
    rows = [
        ("🎮  Games Played", game_stats["games_played"], PRIMARY),
        ("❓  Questions Answered", game_stats["questions_answered"], WHITE),
        ("✅  Correct Answers", game_stats["correct_answers"], GREEN),
        ("🎯  Accuracy", f"{accuracy}%", GOLD),
    ]
    for label, value, color in rows:
        row = tk.Frame(card, bg=SECONDARY, highlightbackground=GLASS_LINE, highlightthickness=2, bd=0)
        row.pack(fill="x", pady=6)
        tk.Label(row, text=label, font=(FONT, 14), fg=MUTED, bg=SECONDARY).pack(side="left", padx=14, pady=12)
        tk.Label(row, text=str(value), font=(FONT, 16, "bold"), fg=color, bg=SECONDARY).pack(side="right", padx=14)
    theme.styled_button(card, "⬅  Home", home, bg=SECONDARY, hover="#1F2A40", fg=MUTED, width=16, height=1).pack(pady=16)


def leaderboard_screen():
    clear()
    board = leaderboard.load()
    stage()
    page_header(root, "LEADERBOARD", "Best score  •  one entry per player")
    wrap, card = theme.glass_card(root, padx=28, pady=20)
    wrap.pack(pady=12)

    if not board:
        theme.muted_label(card, "No scores yet. Complete a quest to appear here.", 14, CARD).pack(pady=30)
    else:
        podium = tk.Frame(card, bg=CARD)
        podium.pack(pady=(0, 16))
        top = board[:3]
        styles = [
            (GOLD, "🥇", PODIUM_GOLD),
            (MUTED, "🥈", PODIUM_SILVER),
            ("#CD7F32", "🥉", PODIUM_BRONZE),
        ]
        if len(top) >= 3:
            display = [top[1], top[0], top[2]]
            display_styles = [styles[1], styles[0], styles[2]]
            ranks = [2, 1, 3]
        else:
            display = top
            display_styles = styles[: len(top)]
            ranks = list(range(1, len(top) + 1))
        for entry, style, rank_n in zip(display, display_styles, ranks):
            color, medal, bg = style
            col = tk.Frame(podium, bg=bg, highlightbackground=color, highlightthickness=2, bd=0)
            col.pack(side="left", padx=8, ipadx=20, ipady=14)
            tk.Label(col, text=medal, font=(FONT, 24), bg=bg, fg=color).pack()
            tk.Label(col, text="😎", font=(FONT, 22), bg=bg).pack(pady=2)
            tk.Label(col, text=f"#{rank_n}", font=(FONT, 10, "bold"), bg=bg, fg=MUTED).pack()
            tk.Label(col, text=entry["name"], font=(FONT, 14, "bold"), bg=bg, fg=WHITE).pack()
            tk.Label(col, text=f"{entry['score']}/5", font=(FONT, 13, "bold"), bg=bg, fg=color).pack()

        for i, entry in enumerate(board[3:], start=4):
            row = tk.Frame(card, bg=SECONDARY, highlightbackground=GLASS_LINE, highlightthickness=2, bd=0)
            row.pack(fill="x", pady=4)
            tk.Label(row, text=f"#{i}", font=(FONT, 12, "bold"), fg=MUTED, bg=SECONDARY, width=4).pack(
                side="left", padx=8, pady=10
            )
            tk.Label(row, text="😎", font=(FONT, 14), bg=SECONDARY).pack(side="left")
            tk.Label(row, text=entry["name"], font=(FONT, 13, "bold"), fg=WHITE, bg=SECONDARY).pack(side="left", padx=8)
            tk.Label(row, text=f"Best  {entry['score']}/5", font=(FONT, 12, "bold"), fg=GOLD, bg=SECONDARY).pack(
                side="right", padx=12
            )

    theme.styled_button(card, "⬅  Home", home, bg=SECONDARY, hover="#1F2A40", fg=MUTED, width=16, height=1).pack(pady=16)
