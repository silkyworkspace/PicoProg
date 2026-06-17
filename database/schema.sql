-- データベースを使用
USE picoprog;

-- usersテーブル
-- CREATE TABLE users (
--     id INT AUTO_INCREMENT PRIMARY KEY,
--     username VARCHAR(50) NOT NULL,
--     email VARCHAR(100) NOT NULL UNIQUE,
--     password VARCHAR(255) NOT NULL,
--     profile TEXT,
--     icon_path VARCHAR(255),
--     created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
--     updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
-- );

-- posts(投稿)テーブル
-- CREATE TABLE posts (
--     id INT AUTO_INCREMENT PRIMARY KEY,
--     user_id INT NOT NULL,
--     content TEXT NOT NULL,
--     created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
--     updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
--     FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
-- );

-- categories(カテゴリマスタ)テーブル
-- CREATE TABLE categories (
--     id INT AUTO_INCREMENT PRIMARY KEY,
--     name VARCHAR(50) NOT NULL UNIQUE,
--     type VARCHAR(20) NOT NULL,
--     sort_order INT NOT NULL DEFAULT 0,
--     created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
-- );

-- 初期カテゴリデータ
-- INSERT INTO categories (name, type, sort_order) VALUES
-- ('学習中', 'status', 1),
-- ('制作中', 'status', 2),
-- ('完成・達成', 'status', 3),
-- ('Python基礎', 'tech', 4),
-- ('Web開発(Flask)', 'tech', 5),
-- ('データベース(SQL)', 'tech', 6),
-- ('フロントエンド(HTML/CSS/JS)', 'tech', 7),
-- ('その他', 'tech', 8);

-- post_categoriesテーブル(中間テーブル)
-- CREATE TABLE post_categories (
--     id INT AUTO_INCREMENT PRIMARY KEY,
--     post_id INT NOT NULL,
--     category_id INT NOT NULL,
--     created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
--     FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE CASCADE,
--     FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE CASCADE,
--     UNIQUE KEY unique_post_category (post_id, category_id)
-- );

-- commentsテーブル
-- CREATE TABLE comments (
--     id INT AUTO_INCREMENT PRIMARY KEY,
--     post_id INT NOT NULL,
--     user_id INT NOT NULL,
--     content TEXT NOT NULL,
--     created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
--     FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
--     FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
-- );

-- likesテーブル
-- CREATE TABLE likes (
--     id INT AUTO_INCREMENT PRIMARY KEY,
--     user_id INT NOT NULL,
--     post_id INT NOT NULL,
--     created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
--     FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
--     FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
--     UNIQUE KEY unique_user_post_like(user_id, post_id)
-- );

-- favoritesテーブル
-- CREATE TABLE favorites (
--     id INT AUTO_INCREMENT PRIMARY KEY,
--     user_id INT NOT NULL,
--     post_id INT NOT NULL,
--     created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
--     FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
--     FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
--     UNIQUE KEY unique_user_post(user_id, post_id)
-- );

-- インデックス作成
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_posts_user_id ON posts(user_id);
CREATE INDEX idx_posts_created_at ON posts(created_at);
CREATE INDEX idx_post_categories_post_id ON post_categories(post_id);
CREATE INDEX idx_post_categories_category_id ON post_categories(category_id);
CREATE INDEX idx_comments_post_id ON comments(post_id);
CREATE INDEX idx_favorites_user_id ON favorites(user_id);
CREATE INDEX idx_favorites_post_id ON favorites(post_id);