import database


def load():
    data = database.load_leaderboard()
    return data if isinstance(data, list) else []


def save_all(board):
    database.save_leaderboard_all(board if isinstance(board, list) else [])


def save(name, score):
    if not name:
        return
    database.add_leaderboard_score(name, score)
