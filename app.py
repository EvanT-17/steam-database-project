import getpass
import os
import secrets
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation

import pymysql
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from pymysql import IntegrityError
from pymysql.cursors import DictCursor
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = secrets.token_bytes(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Strict")
db_config = {
    "host": os.environ.get("MYSQL_HOST", "127.0.0.1"),
    "port": int(os.environ.get("MYSQL_PORT", "3306")),
    "user": os.environ.get("MYSQL_USER", "root"),
    "database": os.environ.get("MYSQL_DATABASE", "steam_db"),
    "connect_timeout": 5,
    "cursorclass": DictCursor,
}


@contextmanager
def database():
    connection = pymysql.connect(**db_config)
    cursor = connection.cursor()
    try:
        yield connection, cursor
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def positive_id(value):
    try:
        number = int(value)
    except (TypeError, ValueError):
        abort(400, "Invalid ID.")
    if number < 1:
        abort(400, "Invalid ID.")
    return number


def text_field(name, max_length):
    value = request.form.get(name, "").strip()
    if not value or len(value) > max_length:
        abort(400, f"{name} must be between 1 and {max_length} characters.")
    return value


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        abort(401, "Please log in first.")
    return user_id


@app.before_request
def protect_forms():
    if request.method == "POST":
        expected = session.get("csrf_token", "")
        supplied = request.form.get("csrf_token", "")
        if not expected or not secrets.compare_digest(expected, supplied):
            abort(400, "Invalid form token. Reload the page and try again.")


@app.context_processor
def form_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return {"csrf_token": session["csrf_token"]}


@app.errorhandler(pymysql.MySQLError)
def database_error(error):
    app.logger.exception("Database operation failed: %s", error)
    return render_template("error.html", message="Database operation failed. Check the server terminal for details."), 500


@app.get("/")
def index():
    query = request.args.get("q", "").strip()
    user_id = session.get("user_id")
    with database() as (_, cursor):
        cursor.execute(
            """SELECT g.game_id, g.title, g.price, g.release_date, d.name AS developer,
                      EXISTS(SELECT 1 FROM `library` l WHERE l.game_id = g.game_id AND l.user_id = %s) AS owned
               FROM games g JOIN developers d ON d.developer_id = g.developer_id
               WHERE g.title LIKE %s ORDER BY g.title, g.game_id""",
            (user_id, f"%{query}%"),
        )
        games = cursor.fetchall()
        cursor.execute("SELECT developer_id, name FROM developers ORDER BY name")
        developers = cursor.fetchall()
        cursor.execute(
            """SELECT r.game_id, r.content, r.recommended, r.created_at, u.username
               FROM reviews r JOIN users u ON u.user_id = r.user_id
               ORDER BY r.created_at DESC, r.review_id DESC"""
        )
        reviews = cursor.fetchall()
        library = []
        orders = []
        if user_id:
            cursor.execute(
                """SELECT g.game_id, g.title, l.acquired_at
                   FROM `library` l JOIN games g ON g.game_id = l.game_id
                   WHERE l.user_id = %s ORDER BY l.acquired_at DESC""",
                (user_id,),
            )
            library = cursor.fetchall()
            cursor.execute(
                """SELECT o.order_id, o.created_at, o.total_amount, o.status,
                          g.title, oi.purchase_price, oi.quantity
                   FROM orders o JOIN order_items oi ON oi.order_id = o.order_id
                   JOIN games g ON g.game_id = oi.game_id
                   WHERE o.user_id = %s ORDER BY o.order_id DESC, oi.order_item_id""",
                (user_id,),
            )
            orders = cursor.fetchall()
    return render_template(
        "index.html", games=games, developers=developers, reviews=reviews,
        library=library, orders=orders, query=query,
    )


@app.post("/register")
def register():
    username = text_field("username", 100)
    email = text_field("email", 254)
    password = text_field("password", 128)
    if len(password) < 8:
        abort(400, "Password must contain at least 8 characters.")
    try:
        with database() as (_, cursor):
            cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                (username, email, generate_password_hash(password)),
            )
    except IntegrityError:
        flash("Username or email is already in use.", "error")
        return redirect(url_for("index"))
    flash("Account created. You can now log in.")
    return redirect(url_for("index"))


@app.post("/login")
def login():
    username = text_field("username", 100)
    password = text_field("password", 128)
    with database() as (_, cursor):
        cursor.execute("SELECT user_id, username, password_hash FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
    if not user or not check_password_hash(user["password_hash"], password):
        flash("Invalid username or password.", "error")
    else:
        session.clear()
        session["user_id"] = user["user_id"]
        session["username"] = user["username"]
        flash("Logged in.")
    return redirect(url_for("index"))


@app.post("/logout")
def logout():
    current_user()
    session.clear()
    flash("Logged out.")
    return redirect(url_for("index"))


@app.post("/developers")
def add_developer():
    current_user()
    name = text_field("name", 200)
    with database() as (_, cursor):
        cursor.execute("INSERT INTO developers (name) VALUES (%s)", (name,))
    flash("Developer added.")
    return redirect(url_for("index"))


@app.post("/games")
def add_game():
    current_user()
    title = text_field("title", 255)
    developer_id = positive_id(request.form.get("developer_id"))
    try:
        price = Decimal(request.form.get("price", ""))
        if not price.is_finite() or price < 0 or price > Decimal("99999999.99") or price.as_tuple().exponent < -2:
            raise InvalidOperation
    except InvalidOperation:
        abort(400, "Enter a valid non-negative price with at most two decimal places.")
    with database() as (_, cursor):
        cursor.execute("SELECT developer_id FROM developers WHERE developer_id = %s", (developer_id,))
        if not cursor.fetchone():
            abort(400, "Developer does not exist.")
        cursor.execute("INSERT INTO games (developer_id, title, price) VALUES (%s, %s, %s)",
                       (developer_id, title, price))
    flash("Game added.")
    return redirect(url_for("index"))


@app.post("/buy/<int:game_id>")
def buy(game_id):
    user_id = current_user()
    with database() as (_, cursor):
        cursor.execute("SELECT game_id, price FROM games WHERE game_id = %s FOR UPDATE", (game_id,))
        game = cursor.fetchone()
        if not game:
            abort(404, "Game not found.")
        cursor.execute("SELECT user_id FROM `library` WHERE user_id = %s AND game_id = %s", (user_id, game_id))
        if cursor.fetchone():
            flash("This game is already in your library.", "error")
            return redirect(url_for("index"))
        cursor.execute("INSERT INTO orders (user_id, total_amount, status) VALUES (%s, %s, %s)",
                       (user_id, game["price"], "completed"))
        order_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO order_items (order_id, game_id, purchase_price, quantity) VALUES (%s, %s, %s, 1)",
            (order_id, game_id, game["price"]),
        )
        cursor.execute("INSERT INTO `library` (user_id, game_id, acquisition_source) VALUES (%s, %s, %s)",
                       (user_id, game_id, "purchase"))
    flash("Purchase recorded. This is a demo; no payment was processed.")
    return redirect(url_for("index"))


@app.post("/reviews/<int:game_id>")
def review(game_id):
    user_id = current_user()
    content = text_field("content", 5000)
    recommendation = request.form.get("recommended")
    if recommendation not in ("0", "1"):
        abort(400, "Choose whether you recommend this game.")
    with database() as (_, cursor):
        cursor.execute("SELECT game_id FROM games WHERE game_id = %s", (game_id,))
        if not cursor.fetchone():
            abort(404, "Game not found.")
        cursor.execute(
            """INSERT INTO reviews (user_id, game_id, recommended, content)
               VALUES (%s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE recommended = %s, content = %s""",
            (user_id, game_id, int(recommendation), content, int(recommendation), content),
        )
    flash("Review saved.")
    return redirect(url_for("index"))


if __name__ == "__main__":
    db_config["password"] = getpass.getpass(f"MySQL password for {db_config['user']}: ")
    try:
        with database() as (_, cursor):
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except pymysql.MySQLError as error:
        raise SystemExit(f"Cannot connect to MySQL: {error}") from error
    print("Open http://127.0.0.1:5000 (press Ctrl+C to stop)")
    app.run(host="127.0.0.1", port=5000, debug=False)
