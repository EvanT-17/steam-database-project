# Steam Database Project

A local classroom project that models a simple game store using Flask and
MySQL. Browse a catalog, manage game data, simulate purchases, and explore the
relationships between users, games, orders, libraries, and reviews.

> **For local development and learning only.** Purchases are simulated; no real
> payments are processed. This project is not a production service.

## Features

- Register and sign in with a website account.
- Browse and search games; add developers and games to the catalog.
- Add games to a persistent shopping cart (a pending order), remove items, and
  check out to add them to your library. Purchases are simulated.
- Remove games from your library and view completed order history.
- Create or update reviews, whether or not you own the game.
- Import a small fictional game catalog from a CSV file.

All signed-in users can add developers and games; there is no administrator role
or catalog deletion in the app. A game can only be added to the cart once and
cannot be added while it is in your library. Removing a game from your library
does not delete its order history; you can buy it again to restore it. Cart
prices are recorded when games are added, and all cart items are checked out
together.

## Requirements

- Python 3.9 or later and pip
- MySQL 8.0.16 or later, running locally or otherwise accessible
- A MySQL account with permission to create the database and tables and read
  and modify their data

The Python dependencies are listed in [requirements.txt](requirements.txt).

## Getting started

The commands below use macOS or Linux. Run them from a terminal.

### 1. Clone the repository

```bash
git clone https://github.com/EvanT-17/steam-database-project.git
cd steam-database-project
```

### 2. Create the database

Start MySQL, then run the schema script:

```bash
mysql -h 127.0.0.1 -u root -p < steam_schema.sql
```

Enter your MySQL password when prompted. Replace the host or user if needed.
The script creates and uses `steam_db` and creates nine tables. It is intended
for a new database: it does not drop or overwrite existing tables and will fail
if those tables already exist. See [steam_schema.sql](steam_schema.sql) for the
schema.

### 3. Install dependencies

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

### 4. Start the app

```bash
.venv/bin/python app.py
```

Enter your MySQL password at the prompt, then open
<http://127.0.0.1:5000>. Create a website account and sign in. You can add a
developer and game through the app or import the sample catalog below. Press
Ctrl+C in the terminal to stop the server.

The website account is separate from the MySQL account.

## Database configuration

The app and sample importer use the following environment variables:

| Variable | Default | Description |
| --- | --- | --- |
| `MYSQL_HOST` | `127.0.0.1` | MySQL server host |
| `MYSQL_PORT` | `3306` | MySQL server port |
| `MYSQL_USER` | `root` | MySQL user |
| `MYSQL_DATABASE` | `steam_db` | Database name |

Set any overrides before starting the app or importer, for example:

```bash
export MYSQL_USER=my_mysql_user
export MYSQL_HOST=127.0.0.1
```

Both programs prompt for the MySQL password. Do not put passwords in source
files or command-line arguments. If you choose a different database name,
create its tables separately: the provided schema script explicitly creates
and uses `steam_db`.

## Import sample games

After setting up the database and installing dependencies, run:

```bash
.venv/bin/python import_sample_data.py
```

The importer reads fictional developers, games, and pipe-separated categories
from [sample_games.csv](sample_games.csv). It uses the same connection settings
as the app and inserts the catalog in one transaction. It preserves existing
records, reuses matching developers, game titles, and categories, and does not
update existing game details. Duplicate matching names or a game title belonging
to a different developer cause the import to stop and roll back. Avoid running
the importer while another process is modifying the catalog. It does not create
users, orders, library entries, or reviews.

## Project structure

| Path | Purpose |
| --- | --- |
| [app.py](app.py) | Flask application and database operations |
| [steam_schema.sql](steam_schema.sql) | MySQL database and table definitions |
| [import_sample_data.py](import_sample_data.py) | CSV catalog importer |
| [sample_games.csv](sample_games.csv) | Fictional sample catalog |
| [templates/](templates/) | HTML templates |
| [static/](static/) | Stylesheet |

## Limitations

The app listens on localhost, has no administrator roles or login rate limiting,
and signs users out when restarted. Do not expose it to the internet or use it
for real payments.
