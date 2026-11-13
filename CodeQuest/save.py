import database

DEFAULT = database.PLAYER_DEFAULT.copy()


def load_data():
    data = database.load_player()
    if not isinstance(data, dict):
        data = {}

    merged = DEFAULT.copy()
    merged.update(data)

    if not merged.get("avatar"):
        merged["avatar"] = DEFAULT["avatar"]

    return merged


def save_data(data):
    if not isinstance(data, dict):
        data = DEFAULT.copy()
    database.save_player(data)
