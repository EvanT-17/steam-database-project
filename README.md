# Steam Database Project — Four-Page Version

A small, **local classroom project** using Flask and MySQL. The interface has
four sections after login: **Game Store**, **Library**, **Order** and **Admin**.
The Game Store keeps the original inline game cards and reviews; there is **no
separate Game Details page**. Purchases are simulated (no payment is processed).

## Features

| Section | What you can do |
| --- | --- |
| Login / Register | Create an account, log in, log out. Login is required to see the store. |
| Game Store | Browse/search games, see prices/developers/dates, read/add/update reviews, add games to cart. |
| Library | See purchased games and remove a game from your library. |
| Order | Two tabs: **Shopping Cart** (remove items / checkout) and **Order History**. |
| Admin | Add developers and games. Any signed-in user can access or submit these actions. |

For this local classroom demo, **Admin is a catalog-management page, not a
separate user role**. Every signed-in user can add developers and games.
The backend still requires login and validates form tokens. There are no
database schema changes or migrations. The original schema uses **developers**,
not a separate publisher table.

A cart is stored as a pending order. Checkout marks the order completed and
inserts its games into the user's library in the same transaction. Removing a
game from Library does **not** erase the order history; if removed, you may
purchase it again. Each user may review a game even without owning it. Saving
another review for the same game updates that user's previous review. The store
cannot be accessed without logging in.

## Requirements

- Python 3.9+ and `pip`
- MySQL 8.0.16+ (server running)
- MySQL account permitted to create tables and read/write data

Python dependencies are in `requirements.txt` (`Flask` and `PyMySQL`).

## Set up a **new database**

1. Install and start MySQL. Open **MySQL Workbench** and connect to your server.
2. Open **File > Open SQL Script**, choose `steam_schema.sql`, and run the whole
   script using the lightning-bolt Execute button. Alternatively, from a shell:

   ```bash
   mysql -h 127.0.0.1 -u root -p < steam_schema.sql
   ```

   The script creates the database `steam_db` and its nine tables. It is for a
   fresh database; it will fail rather than overwrite existing tables.
3. Install dependencies from the folder containing `app.py`:

   **Windows (PowerShell)**

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   .\.venv\Scripts\python.exe app.py
   ```

   **macOS / Linux**

   ```bash
   python3 -m venv .venv
   .venv/bin/python -m pip install -r requirements.txt
   .venv/bin/python app.py
   ```

4. Enter the **MySQL** password when prompted in the terminal. Open
   **http://127.0.0.1:5000**. Create a website account and log in.
   The website account is separate from the MySQL login.
5. To populate the catalog, run `import_sample_data.py` (see below), or use
   **Admin > Add Developer > Add Game**. Importing sample data is easiest for
   the video demonstration.

Stop the Flask server with Ctrl+C. Your MySQL data persists across browser and
app restarts. You may need to log in again after an app restart; the account is
not deleted.

## Using your **existing database** (no migration required)

If you already used the original `steam_schema.sql` and have saved accounts,
orders, reviews or games, **do not rerun the schema**. Simply replace the
project files with this version, launch `app.py` and log back in. Your data and
the original nine-table ER diagram remain unchanged. All signed-in accounts can access the Admin page.

## Import sample data

The supplied `sample_games.csv` contains 8 fictional games and their
developers/categories. Once tables are set up and dependencies are installed:

**Windows:**

```powershell
.\.venv\Scripts\python.exe import_sample_data.py
```

**macOS / Linux:**

```bash
.venv/bin/python import_sample_data.py
```

The importer prompts for the MySQL password, inserts games and categories
transactionally, reuses matching existing entries and does **not** insert
users, reviews, orders or library entries. It does not modify existing games.

## Database configuration

| Environment variable | Default | Purpose |
| --- | --- | --- |
| `MYSQL_HOST` | `127.0.0.1` | MySQL server address |
| `MYSQL_PORT` | `3306` | MySQL server port |
| `MYSQL_USER` | `root` | MySQL username |
| `MYSQL_DATABASE` | `steam_db` | Database name |
| `FLASK_SECRET_KEY` | random for each run | Optional fixed session signing key |

The app and importer ask for the MySQL password at launch. For a simple local
classroom demo you can leave all environment variables at their defaults. Set
`FLASK_SECRET_KEY` to a private stable value in your environment only if you
want existing browser login sessions to remain valid across app restarts;
otherwise log in again after restarting. Never commit real passwords or secret
keys to your repository.

## Key project files

| File | Purpose |
| --- | --- |
| `app.py` | Routes, login, DB queries, cart and transaction logic |
| `steam_schema.sql` | Nine-table schema for *new* databases |
| `templates/base.html` | Header, four-item nav and messages |
| `templates/auth.html` | Sign in / register screen |
| `templates/store.html` | Original inline game cards, search, reviews |
| `templates/library.html` | Purchased games |
| `templates/orders.html` | Cart and order history tabs |
| `templates/admin.html` | Developer/game create forms |
| `static/style.css` | Dark theme, nav and page styling |
| `import_sample_data.py`, `sample_games.csv` | Sample data importer/catalog |
| `tests/test_cart.py` | Flask/database workflow tests with SQLite test doubles |

## Suggested two-minute CRUD demonstration

1. Log in with any website account; use **Admin** to **create** a developer and a game
   (`INSERT`).
2. Open **Game Store** to **read** the new game and search it (`SELECT`).
3. Enter a review and submit it again with new text to **update** it
   (`INSERT ... ON DUPLICATE KEY UPDATE`).
4. Add the game to cart, visit **Order > Shopping Cart**, then check out
   (`INSERT` and `UPDATE` within a transaction).
5. Show **Order > Order History** and **Library** (`JOIN` and `SELECT`), then
   remove a library entry to demonstrate **delete** (`DELETE`).

The presentation assessment asks for a demonstration video of **at most two
minutes**, included within the **five-minute** presentation. The project also
needs an ER diagram, key SQL explanations and clear reproduction instructions.

## Tests

After installing the Python dependencies, from this directory run:

```bash
python -m unittest discover -s tests -v
```

The tests use SQLite in memory and a replacement cursor for most web flows;
no running MySQL instance is needed for the tests. A real MySQL run using the
README steps is still recommended before presentation.

## Limitations

For a *local class project only*: no real payments, no catalog edit/delete
screen, no publisher table, no game details page, no login rate limiting, and no
role-based catalog permissions. Because any signed-in user can add catalog
entries, this version is **not suitable for public deployment**. The app only listens on
`127.0.0.1` by default.
