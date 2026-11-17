-- MySQL 8.0.16 or later is required for enforced CHECK constraints.
-- Run against a new database; existing tables are never dropped or overwritten.
CREATE DATABASE IF NOT EXISTS steam_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_ai_ci;

USE steam_db;

CREATE TABLE users (
    user_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    username VARCHAR(100) NOT NULL,
    email VARCHAR(254) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    PRIMARY KEY (user_id),
    CONSTRAINT uq_users_username UNIQUE (username),
    CONSTRAINT uq_users_email UNIQUE (email)
) ENGINE = InnoDB;

CREATE TABLE developers (
    developer_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(200) NOT NULL,
    country VARCHAR(100),
    website VARCHAR(2048),
    PRIMARY KEY (developer_id)
) ENGINE = InnoDB;

CREATE TABLE games (
    game_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    developer_id BIGINT UNSIGNED NOT NULL,
    title VARCHAR(255) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    release_date DATE,
    PRIMARY KEY (game_id),
    CONSTRAINT fk_games_developer FOREIGN KEY (developer_id)
        REFERENCES developers (developer_id),
    CONSTRAINT chk_games_price CHECK (price >= 0)
) ENGINE = InnoDB;

CREATE TABLE categories (
    category_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    category_name VARCHAR(100) NOT NULL,
    PRIMARY KEY (category_id)
) ENGINE = InnoDB;

CREATE TABLE game_categories (
    game_id BIGINT UNSIGNED NOT NULL,
    category_id BIGINT UNSIGNED NOT NULL,
    PRIMARY KEY (game_id, category_id),
    CONSTRAINT fk_game_categories_game FOREIGN KEY (game_id)
        REFERENCES games (game_id),
    CONSTRAINT fk_game_categories_category FOREIGN KEY (category_id)
        REFERENCES categories (category_id)
) ENGINE = InnoDB;

CREATE TABLE orders (
    order_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    total_amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(32) NOT NULL,
    PRIMARY KEY (order_id),
    CONSTRAINT fk_orders_user FOREIGN KEY (user_id)
        REFERENCES users (user_id),
    CONSTRAINT chk_orders_total CHECK (total_amount >= 0)
) ENGINE = InnoDB;

CREATE TABLE order_items (
    order_item_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    order_id BIGINT UNSIGNED NOT NULL,
    game_id BIGINT UNSIGNED NOT NULL,
    purchase_price DECIMAL(10, 2) NOT NULL,
    quantity INT UNSIGNED NOT NULL,
    PRIMARY KEY (order_item_id),
    CONSTRAINT fk_order_items_order FOREIGN KEY (order_id)
        REFERENCES orders (order_id),
    CONSTRAINT fk_order_items_game FOREIGN KEY (game_id)
        REFERENCES games (game_id),
    CONSTRAINT chk_order_items_price CHECK (purchase_price >= 0),
    CONSTRAINT chk_order_items_quantity CHECK (quantity > 0)
) ENGINE = InnoDB;

CREATE TABLE `library` (
    user_id BIGINT UNSIGNED NOT NULL,
    game_id BIGINT UNSIGNED NOT NULL,
    acquired_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    acquisition_source VARCHAR(100) NOT NULL,
    PRIMARY KEY (user_id, game_id),
    CONSTRAINT fk_library_user FOREIGN KEY (user_id)
        REFERENCES users (user_id),
    CONSTRAINT fk_library_game FOREIGN KEY (game_id)
        REFERENCES games (game_id)
) ENGINE = InnoDB;

CREATE TABLE reviews (
    review_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    game_id BIGINT UNSIGNED NOT NULL,
    recommended BOOLEAN NOT NULL,
    content TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (review_id),
    CONSTRAINT uq_reviews_user_game UNIQUE (user_id, game_id),
    CONSTRAINT fk_reviews_user FOREIGN KEY (user_id)
        REFERENCES users (user_id),
    CONSTRAINT fk_reviews_game FOREIGN KEY (game_id)
        REFERENCES games (game_id),
    CONSTRAINT chk_reviews_recommended CHECK (recommended IN (0, 1))
) ENGINE = InnoDB;
