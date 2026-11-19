import sqlite3
import unittest
from contextlib import contextmanager
from decimal import Decimal
from unittest.mock import patch

import app as steam_app


class SQLiteCursor:
    def __init__(self, connection, fail_on_library_game=None):
        self.cursor = connection.cursor()
        self.fail_on_library_game = fail_on_library_game

    def execute(self, query, params=()):
        if query.startswith("INSERT INTO `library`") and params[1] == self.fail_on_library_game:
            raise RuntimeError("Simulated library insertion failure")
        query = query.replace("%s", "?").replace(" FOR UPDATE", "")
        self.cursor.execute(query, tuple(str(value) if isinstance(value, Decimal) else value for value in params))

    def convert(self, row):
        if row is None:
            return None
        result = dict(row)
        for key in ("price", "purchase_price", "total_amount"):
            if key in result:
                result[key] = Decimal(str(result[key]))
        return result

    def fetchone(self):
        return self.convert(self.cursor.fetchone())

    def fetchall(self):
        return [self.convert(row) for row in self.cursor.fetchall()]

    @property
    def lastrowid(self):
        return self.cursor.lastrowid

    @property
    def rowcount(self):
        return self.cursor.rowcount


class CartWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript("""
            PRAGMA foreign_keys = ON;
            CREATE TABLE users (user_id INTEGER PRIMARY KEY, username TEXT);
            CREATE TABLE developers (developer_id INTEGER PRIMARY KEY, name TEXT);
            CREATE TABLE games (game_id INTEGER PRIMARY KEY, developer_id INTEGER, title TEXT,
                                price NUMERIC, release_date TEXT);
            CREATE TABLE orders (order_id INTEGER PRIMARY KEY, user_id INTEGER, total_amount NUMERIC,
                                 status TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE order_items (order_item_id INTEGER PRIMARY KEY, order_id INTEGER REFERENCES orders,
                                      game_id INTEGER, purchase_price NUMERIC, quantity INTEGER);
            CREATE TABLE library (user_id INTEGER, game_id INTEGER, acquisition_source TEXT,
                                  acquired_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (user_id, game_id));
            CREATE TABLE reviews (review_id INTEGER PRIMARY KEY, user_id INTEGER, game_id INTEGER,
                                  content TEXT, recommended INTEGER, created_at TEXT);
            INSERT INTO users VALUES (1, 'alice'), (2, 'bob');
            INSERT INTO developers VALUES (1, 'studio');
            INSERT INTO games VALUES (1, 1, 'First', 10.00, NULL), (2, 1, 'Second', 3.25, NULL);
        """)
        self.fail_on_library_game = None

        @contextmanager
        def database():
            cursor = SQLiteCursor(self.connection, self.fail_on_library_game)
            try:
                yield self.connection, cursor
                self.connection.commit()
            except Exception:
                self.connection.rollback()
                raise

        self.database_patch = patch.object(steam_app, "database", database)
        self.database_patch.start()
        self.addCleanup(self.database_patch.stop)
        self.addCleanup(self.connection.close)
        steam_app.app.config["TESTING"] = True
        self.client = steam_app.app.test_client()
        self.sign_in(1)

    def sign_in(self, user_id):
        with self.client.session_transaction() as session:
            session["user_id"] = user_id
            session["username"] = "alice" if user_id == 1 else "bob"
            session["csrf_token"] = "token"

    def post(self, url):
        return self.client.post(url, data={"csrf_token": "token"})

    def rows(self, query):
        return [tuple(row) for row in self.connection.execute(query).fetchall()]

    def test_cart_checkout_remove_and_repurchase(self):
        self.post("/cart/1/add")
        self.post("/cart/2/add")
        self.post("/cart/1/add")
        self.assertEqual(self.rows("SELECT user_id, total_amount, status FROM orders"), [(1, 13.25, "pending")])
        self.assertEqual(self.rows("SELECT game_id FROM order_items ORDER BY game_id"), [(1,), (2,)])
        self.assertEqual(self.rows("SELECT * FROM library"), [])
        page = self.client.get("/").get_data(as_text=True)
        self.assertIn("Shopping cart", page)
        self.assertIn("13.25", page)

        self.post("/cart/1/remove")
        self.assertEqual(self.rows("SELECT total_amount FROM orders"), [(3.25,)])
        self.post("/cart/1/add")
        self.post("/cart/checkout")
        self.assertEqual(self.rows("SELECT total_amount, status FROM orders"), [(13.25, "completed")])
        self.assertEqual(self.rows("SELECT user_id, game_id FROM library ORDER BY game_id"), [(1, 1), (1, 2)])
        self.post("/cart/1/add")
        self.assertEqual(self.rows("SELECT count(*) FROM orders"), [(1,)])

        self.post("/library/1/remove")
        self.assertEqual(self.rows("SELECT game_id FROM library"), [(2,)])
        self.assertEqual(self.rows("SELECT count(*) FROM order_items"), [(2,)])
        self.post("/cart/1/add")
        self.post("/cart/checkout")
        self.assertEqual(self.rows("SELECT status FROM orders ORDER BY order_id"), [("completed",), ("completed",)])
        self.assertEqual(self.rows("SELECT user_id, game_id FROM library ORDER BY game_id"), [(1, 1), (1, 2)])
        self.assertEqual(self.client.post("/games/1/delete", data={"csrf_token": "token"}).status_code, 404)

    def test_removal_is_scoped_to_user_and_empty_cart_is_deleted(self):
        self.post("/cart/1/add")
        self.sign_in(2)
        self.assertEqual(self.post("/cart/1/remove").status_code, 404)
        self.assertEqual(self.post("/library/1/remove").status_code, 404)
        self.post("/cart/checkout")
        self.assertEqual(self.rows("SELECT user_id, status FROM orders"), [(1, "pending")])
        self.sign_in(1)
        self.post("/cart/1/remove")
        self.assertEqual(self.rows("SELECT * FROM orders"), [])
        self.assertEqual(self.rows("SELECT count(*) FROM games"), [(2,)])

    def test_failed_checkout_rolls_back_everything(self):
        self.post("/cart/1/add")
        self.post("/cart/2/add")
        self.fail_on_library_game = 2
        with self.assertRaisesRegex(RuntimeError, "Simulated library insertion failure"):
            self.post("/cart/checkout")
        self.assertEqual(self.rows("SELECT * FROM library"), [])
        self.assertEqual(self.rows("SELECT status FROM orders"), [("pending",)])
        self.assertEqual(self.rows("SELECT count(*) FROM order_items"), [(2,)])

    def test_authentication_and_csrf_required(self):
        self.assertEqual(self.client.post("/cart/1/add").status_code, 400)
        with self.client.session_transaction() as session:
            session.pop("user_id")
        self.assertEqual(self.post("/cart/1/add").status_code, 401)
        self.assertEqual(self.post("/cart/checkout").status_code, 401)
        self.assertEqual(self.post("/cart/1/remove").status_code, 401)
        self.assertEqual(self.post("/library/1/remove").status_code, 401)


if __name__ == "__main__":
    unittest.main()
