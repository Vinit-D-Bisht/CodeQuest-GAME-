import database

DEFAULT = database.SETTINGS_DEFAULT.copy()


def load():
    data = database.load_settings()
    if not isinstance(data, dict):
        data = {}

    merged = DEFAULT.copy()
    merged.update(data)
    return merged


def save(data):
    if not isinstance(data, dict):
        data = DEFAULT.copy()
    database.save_settings(data)
