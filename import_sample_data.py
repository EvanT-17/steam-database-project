import csv
import getpass
import os
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pymysql
from pymysql.cursors import DictCursor

CSV_PATH = Path(__file__).with_name("sample_games.csv")
EXPECTED_COLUMNS = ["title", "developer", "country", "price", "release_date", "categories"]


def load_rows():
    with CSV_PATH.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != EXPECTED_COLUMNS:
            raise ValueError(f"CSV headers must be: {', '.join(EXPECTED_COLUMNS)}")
        rows = []
        seen_titles = set()
        for line, row in enumerate(reader, start=2):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"Line {line}: incorrect number of columns")
            row = {key: value.strip() for key, value in row.items()}
            if not row["title"] or len(row["title"]) > 255:
                raise ValueError(f"Line {line}: invalid game title")
            if not row["developer"] or len(row["developer"]) > 200:
                raise ValueError(f"Line {line}: invalid developer name")
            if not row["country"] or len(row["country"]) > 100:
                raise ValueError(f"Line {line}: invalid country")
            title_key = row["title"].casefold()
            if title_key in seen_titles:
                raise ValueError(f"Line {line}: duplicate game title in CSV")
            seen_titles.add(title_key)
            try:
                price = Decimal(row["price"])
                if not price.is_finite() or not 0 <= price <= Decimal("99999999.99") or price.as_tuple().exponent < -2:
                    raise ValueError("invalid price")
                release_date = date.fromisoformat(row["release_date"])
            except (ValueError, InvalidOperation) as error:
                raise ValueError(f"Line {line}: invalid price or release date") from error
            categories = [name.strip() for name in row["categories"].split("|")]
            if any(not name or len(name) > 100 for name in categories):
                raise ValueError(f"Line {line}: invalid category")
            if len({name.casefold() for name in categories}) != len(categories):
                raise ValueError(f"Line {line}: duplicate category")
            rows.append((row["title"], row["developer"], row["country"], price, release_date, categories))
        if not rows:
            raise ValueError("CSV contains no games")
        return rows


def unique_existing(cursor, table, column, value):
    # Identifiers are fixed by the caller; values are always parameterized.
    cursor.execute(f"SELECT * FROM `{table}` WHERE `{column}` = %s LIMIT 2", (value,))
    matches = cursor.fetchall()
    if len(matches) > 1:
        raise ValueError(f"Multiple {table} records match {value!r}; resolve them before importing.")
    return matches[0] if matches else None


def import_rows(connection, rows):
    created = {"developers": 0, "categories": 0, "games": 0, "game_categories": 0}
    try:
        with connection.cursor() as cursor:
            for title, developer, country, price, release_date, categories in rows:
                existing_developer = unique_existing(cursor, "developers", "name", developer)
                if existing_developer:
                    developer_id = existing_developer["developer_id"]
                else:
                    cursor.execute("INSERT INTO developers (name, country) VALUES (%s, %s)", (developer, country))
                    developer_id = cursor.lastrowid
                    created["developers"] += 1

                game = unique_existing(cursor, "games", "title", title)
                if game:
                    if game["developer_id"] != developer_id:
                        raise ValueError(f"Game {title!r} belongs to another developer; import cancelled.")
                    game_id = game["game_id"]
                else:
                    cursor.execute(
                        "INSERT INTO games (developer_id, title, price, release_date) VALUES (%s, %s, %s, %s)",
                        (developer_id, title, price, release_date),
                    )
                    game_id = cursor.lastrowid
                    created["games"] += 1

                for category_name in categories:
                    category = unique_existing(cursor, "categories", "category_name", category_name)
                    if category:
                        category_id = category["category_id"]
                    else:
                        cursor.execute("INSERT INTO categories (category_name) VALUES (%s)", (category_name,))
                        category_id = cursor.lastrowid
                        created["categories"] += 1
                    cursor.execute(
                        "SELECT 1 FROM game_categories WHERE game_id = %s AND category_id = %s",
                        (game_id, category_id),
                    )
                    if not cursor.fetchone():
                        cursor.execute(
                            "INSERT INTO game_categories (game_id, category_id) VALUES (%s, %s)",
                            (game_id, category_id),
                        )
                        created["game_categories"] += 1
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return created


def main():
    rows = load_rows()
    user = os.environ.get("MYSQL_USER", "root")
    config = {
        "host": os.environ.get("MYSQL_HOST", "127.0.0.1"),
        "port": int(os.environ.get("MYSQL_PORT", "3306")),
        "user": user,
        "password": getpass.getpass(f"MySQL password for {user}: "),
        "database": os.environ.get("MYSQL_DATABASE", "steam_db"),
        "cursorclass": DictCursor,
        "connect_timeout": 5,
    }
    with pymysql.connect(**config) as connection:
        created = import_rows(connection, rows)
    print("Import committed. New records: " + ", ".join(f"{key}={value}" for key, value in created.items()))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, pymysql.MySQLError) as error:
        raise SystemExit(f"Import failed; no changes committed: {error}") from error
