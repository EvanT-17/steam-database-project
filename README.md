# Local Steam database demo

This classroom app connects to the existing `steam_db` MySQL database. It can
register and sign in users, add developers and games, browse and search games,
simulate purchases, view a library and orders, and create or update reviews.
Purchases do not charge money. Reviews are allowed whether or not a game is owned.
All signed-in users can add games and developers; there is no administrator role.

## Setup on macOS

1. Start MySQL and create the nine tables using `steam_schema.sql`. If your
   earlier import stopped at `library`, complete that import first.
2. In Terminal, go to this folder and create an isolated Python environment:

   ```bash
   cd "/Users/tengyiming/Desktop/3278GP"
   python3 -m venv .venv
   .venv/bin/python -m pip install -r requirements.txt
   ```

3. Start the website:

   ```bash
   .venv/bin/python app.py
   ```

   Enter your MySQL password when prompted. The default MySQL connection uses
   user `root`, host `127.0.0.1`, port `3306`, and database `steam_db`. To use
   another connection, set `MYSQL_USER`, `MYSQL_HOST`, `MYSQL_PORT`, or
   `MYSQL_DATABASE` in the terminal before starting the app. Do not put your
   password in source files or command-line arguments.
4. Open <http://127.0.0.1:5000>. Create a website account, sign in, add a
   developer and a game, then try the store. Press Ctrl+C to stop the server.

The website account is separate from the MySQL account. For an empty database,
the add-developer and add-game forms let you create initial catalog data.

## Import sample games

`sample_games.csv` contains fictional developers, games, and pipe-separated
categories. After installing the dependencies, run:

```bash
.venv/bin/python import_sample_data.py
```

Enter the MySQL password at the prompt. The importer uses the same `MYSQL_*`
connection variables as the app and inserts the catalog in one transaction.
It preserves existing records and reuses matching developers, game titles, and
categories. Existing game details are not updated. Duplicate matching names or
a game title belonging to a different developer stop and roll back the import.
Run the import without another catalog writer modifying the database at the
same time. No users, orders, libraries, or reviews are created.

This is a local development demo, not a production service. It listens only on
localhost, has no administrator roles or login rate limiting, and signs users
out when restarted. Do not expose it to the internet or use real payments.
