import database

if __name__ == "__main__":
    database.init_db()
    database.migrate_json_if_needed()
    print("Database ready:", database.DB_PATH)
