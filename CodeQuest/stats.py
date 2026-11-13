import database

DEFAULT = database.STATS_DEFAULT.copy()


def load():
    data = database.load_stats()
    if not isinstance(data, dict):
        return DEFAULT.copy()

    merged = DEFAULT.copy()
    merged.update(data)
    return merged


def save(stats):
    if not isinstance(stats, dict):
        stats = DEFAULT.copy()
    database.save_stats(stats)


def add_game():
    stats = load()
    stats["games_played"] += 1
    save(stats)


def add_question(correct):
    stats = load()
    stats["questions_answered"] += 1

    if correct:
        stats["correct_answers"] += 1

    save(stats)


def accuracy():
    stats = load()

    if stats["questions_answered"] == 0:
        return 0

    return round(
        stats["correct_answers"] * 100 / stats["questions_answered"],
        2
    )
