# テーブル定義書

## テーブル一覧

| No. | テーブル名（物理） | テーブル名（論理） | 説明 |
|---|---|---|---|
| 1 | users | ユーザー | 登録ユーザーの情報を管理する |
| 2 | posts | 投稿 | ユーザーの学習記録投稿を管理する |
| 3 | categories | カテゴリ | 投稿に付けるカテゴリのマスタ |
| 4 | post_categories | 投稿カテゴリ | 投稿とカテゴリの中間テーブル |
| 5 | comments | コメント | 投稿へのコメントを管理する |
| 6 | likes | いいね | いいねの登録を管理する |
| 7 | favorites | お気に入り | お気に入りの登録を管理する |
| 8 | notifications | 通知 | いいね・コメント・お気に入り時の通知を管理する |

---

## 1. users（ユーザー）

| カラム名 | 論理名 | データ型 | NULL | 制約 | デフォルト値 | 説明 |
|---|---|---|---|---|---|---|
| id | ユーザーID | INTEGER | NOT NULL | PK, AUTOINCREMENT | — | 自動採番 |
| username | ユーザー名 | TEXT | NOT NULL | — | — | 3〜20文字 |
| email | メールアドレス | TEXT | NOT NULL | UNIQUE | — | 正規表現で形式チェック |
| password | パスワード | TEXT | NOT NULL | — | — | bcryptハッシュ化済み |
| profile | プロフィール | TEXT | NULL | — | NULL | 自己紹介文（200文字以内） |
| icon_path | アイコン画像パス | TEXT | NULL | — | NULL | アップロード画像のファイルパス |
| created_at | 登録日時 | DATETIME | NOT NULL | — | datetime('now','localtime') | レコード作成日時 |
| updated_at | 更新日時 | DATETIME | NOT NULL | — | datetime('now','localtime') | レコード更新日時 |
| is_admin | 管理者フラグ | INTEGER | NOT NULL | — | 0 | 1: 管理者、0: 一般ユーザー |

**インデックス**

| インデックス名 | カラム | 説明 |
|---|---|---|
| idx_users_email | email | メールアドレスによる検索高速化 |

---

## 2. posts（投稿）

| カラム名 | 論理名 | データ型 | NULL | 制約 | デフォルト値 | 説明 |
|---|---|---|---|---|---|---|
| id | 投稿ID | INTEGER | NOT NULL | PK, AUTOINCREMENT | — | 自動採番 |
| user_id | ユーザーID | INTEGER | NOT NULL | FK | — | users.id を参照（CASCADE削除） |
| content | 投稿内容 | TEXT | NOT NULL | — | — | 1〜1000文字 |
| created_at | 投稿日時 | DATETIME | NOT NULL | — | datetime('now','localtime') | レコード作成日時 |
| updated_at | 更新日時 | DATETIME | NOT NULL | — | datetime('now','localtime') | レコード更新日時 |

**外部キー**

| カラム名 | 参照先テーブル | 参照先カラム | 削除時 |
|---|---|---|---|
| user_id | users | id | CASCADE |

**インデックス**

| インデックス名 | カラム | 説明 |
|---|---|---|
| idx_posts_user_id | user_id | ユーザーの投稿一覧取得の高速化 |
| idx_posts_created_at | created_at | 新着順ソートの高速化 |

---

## 3. categories（カテゴリ）

| カラム名 | 論理名 | データ型 | NULL | 制約 | デフォルト値 | 説明 |
|---|---|---|---|---|---|---|
| id | カテゴリID | INTEGER | NOT NULL | PK, AUTOINCREMENT | — | 自動採番 |
| name | カテゴリ名 | TEXT | NOT NULL | UNIQUE | — | カテゴリの表示名 |
| type | 種別 | TEXT | NOT NULL | — | — | `status`（学習状況）または `tech`（技術領域） |
| sort_order | 表示順 | INTEGER | NOT NULL | — | 0 | 画面表示時の並び順 |
| created_at | 登録日時 | DATETIME | NOT NULL | — | datetime('now','localtime') | レコード作成日時 |

**初期データ**

| name | type | sort_order |
|---|---|---|
| 学習中 | status | 1 |
| 制作中 | status | 2 |
| 完成・達成 | status | 3 |
| Python基礎 | tech | 4 |
| Web開発(Flask) | tech | 5 |
| データベース(SQL) | tech | 6 |
| フロントエンド(HTML/CSS/JS) | tech | 7 |
| その他 | tech | 8 |

---

## 4. post_categories（投稿カテゴリ）

| カラム名 | 論理名 | データ型 | NULL | 制約 | デフォルト値 | 説明 |
|---|---|---|---|---|---|---|
| id | ID | INTEGER | NOT NULL | PK, AUTOINCREMENT | — | 自動採番 |
| post_id | 投稿ID | INTEGER | NOT NULL | FK | — | posts.id を参照（CASCADE削除） |
| category_id | カテゴリID | INTEGER | NOT NULL | FK | — | categories.id を参照（CASCADE削除） |
| created_at | 登録日時 | DATETIME | NOT NULL | — | datetime('now','localtime') | レコード作成日時 |

**外部キー**

| カラム名 | 参照先テーブル | 参照先カラム | 削除時 |
|---|---|---|---|
| post_id | posts | id | CASCADE |
| category_id | categories | id | CASCADE |

**ユニーク制約**

| 対象カラム | 説明 |
|---|---|
| (post_id, category_id) | 同じ投稿に同じカテゴリを重複登録しない |

**インデックス**

| インデックス名 | カラム | 説明 |
|---|---|---|
| idx_post_categories_post_id | post_id | 投稿に紐づくカテゴリ取得の高速化 |
| idx_post_categories_cat_id | category_id | カテゴリに紐づく投稿取得の高速化 |

---

## 5. comments（コメント）

| カラム名 | 論理名 | データ型 | NULL | 制約 | デフォルト値 | 説明 |
|---|---|---|---|---|---|---|
| id | コメントID | INTEGER | NOT NULL | PK, AUTOINCREMENT | — | 自動採番 |
| post_id | 投稿ID | INTEGER | NOT NULL | FK | — | posts.id を参照（CASCADE削除） |
| user_id | ユーザーID | INTEGER | NOT NULL | FK | — | users.id を参照（CASCADE削除） |
| content | コメント内容 | TEXT | NOT NULL | — | — | 未入力不可 |
| created_at | 投稿日時 | DATETIME | NOT NULL | — | datetime('now','localtime') | レコード作成日時 |

**外部キー**

| カラム名 | 参照先テーブル | 参照先カラム | 削除時 |
|---|---|---|---|
| post_id | posts | id | CASCADE |
| user_id | users | id | CASCADE |

**インデックス**

| インデックス名 | カラム | 説明 |
|---|---|---|
| idx_comments_post_id | post_id | 投稿に紐づくコメント取得の高速化 |

---

## 6. likes（いいね）

| カラム名 | 論理名 | データ型 | NULL | 制約 | デフォルト値 | 説明 |
|---|---|---|---|---|---|---|
| id | ID | INTEGER | NOT NULL | PK, AUTOINCREMENT | — | 自動採番 |
| user_id | ユーザーID | INTEGER | NOT NULL | FK | — | users.id を参照（CASCADE削除） |
| post_id | 投稿ID | INTEGER | NOT NULL | FK | — | posts.id を参照（CASCADE削除） |
| created_at | 登録日時 | DATETIME | NOT NULL | — | datetime('now','localtime') | レコード作成日時 |

**外部キー**

| カラム名 | 参照先テーブル | 参照先カラム | 削除時 |
|---|---|---|---|
| user_id | users | id | CASCADE |
| post_id | posts | id | CASCADE |

**ユニーク制約**

| 対象カラム | 説明 |
|---|---|
| (user_id, post_id) | 同じユーザーが同じ投稿に重複していいねしない |

---

## 7. favorites（お気に入り）

| カラム名 | 論理名 | データ型 | NULL | 制約 | デフォルト値 | 説明 |
|---|---|---|---|---|---|---|
| id | ID | INTEGER | NOT NULL | PK, AUTOINCREMENT | — | 自動採番 |
| user_id | ユーザーID | INTEGER | NOT NULL | FK | — | users.id を参照（CASCADE削除） |
| post_id | 投稿ID | INTEGER | NOT NULL | FK | — | posts.id を参照（CASCADE削除） |
| created_at | 登録日時 | DATETIME | NOT NULL | — | datetime('now','localtime') | レコード作成日時 |

**外部キー**

| カラム名 | 参照先テーブル | 参照先カラム | 削除時 |
|---|---|---|---|
| user_id | users | id | CASCADE |
| post_id | posts | id | CASCADE |

**ユニーク制約**

| 対象カラム | 説明 |
|---|---|
| (user_id, post_id) | 同じユーザーが同じ投稿を重複してお気に入りしない |

**インデックス**

| インデックス名 | カラム | 説明 |
|---|---|---|
| idx_favorites_user_id | user_id | ユーザーのお気に入り一覧取得の高速化 |
| idx_favorites_post_id | post_id | 投稿のお気に入り件数取得の高速化 |

---

## 8. notifications（通知）

| カラム名 | 論理名 | データ型 | NULL | 制約 | デフォルト値 | 説明 |
|---|---|---|---|---|---|---|
| id | 通知ID | INTEGER | NOT NULL | PK, AUTOINCREMENT | — | 自動採番 |
| user_id | 受信ユーザーID | INTEGER | NOT NULL | FK | — | users.id を参照（CASCADE削除）。通知を受け取るユーザー |
| actor_id | 送信ユーザーID | INTEGER | NOT NULL | FK | — | users.id を参照（CASCADE削除）。操作を行ったユーザー |
| type | 通知種別 | TEXT | NOT NULL | — | — | `like`（いいね）/ `comment`（コメント）/ `favorite`（お気に入り） |
| post_id | 投稿ID | INTEGER | NOT NULL | FK | — | posts.id を参照（CASCADE削除）。通知の起点となった投稿 |
| is_read | 既読フラグ | INTEGER | NOT NULL | — | 0 | 0: 未読、1: 既読 |
| read_at | 既読日時 | DATETIME | NULL | — | NULL | 既読になった日時。未読の場合は NULL |
| created_at | 通知日時 | DATETIME | NOT NULL | — | datetime('now','localtime') | レコード作成日時 |

**外部キー**

| カラム名 | 参照先テーブル | 参照先カラム | 削除時 |
|---|---|---|---|
| user_id | users | id | CASCADE |
| actor_id | users | id | CASCADE |
| post_id | posts | id | CASCADE |

**インデックス**

| インデックス名 | カラム | 説明 |
|---|---|---|
| idx_notifications_user_id | user_id | ユーザーの通知一覧取得の高速化 |

> **自動削除について**
> `read_at` から30日が経過した通知は `database/cleanup_notifications.py` によって削除される。
