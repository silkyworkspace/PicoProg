# 詳細設計書

## 1. アプリケーション構成

| 項目 | 内容 |
|---|---|
| フレームワーク | Flask |
| 言語 | Python 3.x |
| データベース | SQLite3 |
| 設定ファイル | `config.py`（SECRET_KEY・DB_PATH） |
| エントリポイント | `app.py` |

### ディレクトリ構成

```
picoprog/
├── app.py                  # アプリケーション本体（ルート・ビジネスロジック）
├── config.py               # 設定クラス
├── requirements.txt
├── database/
│   ├── init_db.py          # DB初期化スクリプト
│   ├── cleanup_notifications.py  # 通知自動削除スクリプト
│   └── picoprog.db         # SQLiteデータベース
├── static/
│   ├── css/style.css
│   ├── js/
│   └── uploads/            # アイコン画像のアップロード先
├── templates/              # Jinja2テンプレート
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── new_post.html
│   ├── edit_post.html
│   ├── comment.html
│   ├── favorites.html
│   ├── notifications.html
│   ├── profile.html
│   ├── user_settings.html
│   ├── admin.html
│   ├── 404.html
│   └── 500.html
└── tests/
    ├── test_validators.py
    ├── test_auth.py
    ├── test_posts.py
    ├── test_likes.py
    ├── test_favorites.py
    ├── test_notifications.py
    ├── test_profile.py
    ├── test_settings.py
    └── test_admin.py
```

---

## 2. 定数・グローバル設定

| 定数名 | 値 | 説明 |
|---|---|---|
| `ALLOWED_EXTENSIONS` | `{'png', 'jpg', 'jpeg', 'gif'}` | アップロード可能な画像拡張子 |
| `MAX_FILE_SIZE` | `5 * 1024 * 1024`（5MB） | アップロード上限サイズ |
| `USERNAME_MIN` | `3` | ユーザー名の最小文字数 |
| `USERNAME_MAX` | `20` | ユーザー名の最大文字数 |
| `POST_MAX` | `1000` | 投稿内容の最大文字数 |
| `PER_PAGE` | `10` | ページネーションの1ページあたり表示件数 |

---

## 3. 共通処理

### 3.1 データベース接続

```
get_db_connection()
```

- `sqlite3.connect()` で `picoprog.db` に接続
- `row_factory = sqlite3.Row` で辞書形式のアクセスを有効化
- `PRAGMA foreign_keys = ON` で外部キー制約を有効化
- DATETIME型を自動的にPythonの `datetime` オブジェクトに変換

### 3.2 デコレータ

| デコレータ | 説明 |
|---|---|
| `@login_required` | セッションに `user_id` がない場合、ログイン画面へリダイレクト |
| `@admin_required` | 未ログイン時はログイン画面へ、`is_admin` が False の場合はタイムラインへリダイレクト |

### 3.3 コンテキストプロセッサ

| 関数 | テンプレートへ渡す変数 | 説明 |
|---|---|---|
| `inject_csrf_token` | `csrf_token` | 全テンプレートでCSRFトークンを利用可能にする |
| `inject_globals` | `current_year` | フッターの著作権表記に使用 |
| `inject_unread_count` | `unread_notification_count` | ナビゲーションの未読バッジ件数（未ログイン時は0） |

### 3.4 before_request

`load_user_icon()` : セッションに `user_icon` がない場合、DBからアイコンパスを取得してセッションに保存する。

### 3.5 バリデーション関数

| 関数 | 引数 | 戻り値 | チェック内容 |
|---|---|---|---|
| `_validate_email(email)` | メールアドレス文字列 | bool | 正規表現 `^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$` |
| `_validate_password(password)` | パスワード文字列 | (bool, エラーメッセージ) | 8文字以上・英字含む・数字含む |
| `_validate_username(username)` | ユーザー名文字列 | (bool, エラーメッセージ) | 3〜20文字 |
| `validate_image(file)` | アップロードファイル | (bool, エラーメッセージ) | 拡張子・Content-Typeチェック |

### 3.6 セッション情報

ログイン成功時に以下をセッションに保存する。

| キー | 型 | 説明 |
|---|---|---|
| `user_id` | int | ログイン中ユーザーのID |
| `username` | str | ログイン中ユーザーのユーザー名 |
| `user_icon` | str or None | アイコン画像のファイルパス |
| `is_admin` | bool | 管理者フラグ |

---

## 4. エンドポイント一覧

| メソッド | URL | 関数名 | 認証 | 説明 |
|---|---|---|---|---|
| GET | `/` | `index` | ログイン必須 | タイムライン |
| GET/POST | `/login` | `login` | — | ログイン |
| GET/POST | `/register` | `register` | — | 新規登録 |
| GET | `/logout` | `logout` | — | ログアウト |
| GET/POST | `/post/new` | `new_post` | ログイン必須 | 新規投稿 |
| GET/POST | `/post/<id>/edit` | `edit_post` | ログイン必須 | 投稿編集 |
| POST | `/post/<id>/delete` | `delete_post` | ログイン必須 | 投稿削除 |
| GET/POST | `/post/<id>/comment` | `comment` | ログイン必須 | コメント表示・投稿 |
| POST | `/comment/<id>/delete` | `delete_comment` | ログイン必須 | コメント削除 |
| POST | `/post/<id>/like` | `toggle_like` | ログイン必須 | いいね toggle（JSON） |
| GET | `/favorites` | `favorites` | ログイン必須 | お気に入り一覧 |
| POST | `/post/<id>/favorite` | `toggle_favorite` | ログイン必須 | お気に入り toggle（JSON） |
| GET | `/notifications` | `notifications` | ログイン必須 | 通知一覧 |
| GET | `/notifications/<id>/read` | `notification_read` | ログイン必須 | 通知既読化 |
| GET | `/user/<username>` | `user_profile` | ログイン必須 | プロフィール |
| GET/POST | `/settings` | `user_settings` | ログイン必須 | ユーザー設定 |
| GET | `/admin` | `admin` | 管理者必須 | 管理者パネル |
| POST | `/admin/user/<id>/delete` | `admin_delete_user` | 管理者必須 | ユーザー削除 |
| POST | `/admin/post/<id>/delete` | `admin_delete_post` | 管理者必須 | 投稿削除（管理者） |

---

## 5. 各機能の処理詳細

### 5.1 ログイン（`/login`）

**GET**
- ログイン済みの場合はタイムラインへリダイレクト
- `login.html` を表示

**POST**
1. `email` / `password` の未入力チェック
2. メールアドレス形式チェック（`_validate_email`）
3. DBから `email` に一致するユーザーを取得
4. `bcrypt.checkpw` でパスワードを照合
5. 認証成功時：`user_id` / `username` / `user_icon` / `is_admin` をセッションに保存
6. タイムラインへリダイレクト

---

### 5.2 新規登録（`/register`）

**POST**
1. 全項目の未入力チェック
2. `_validate_username` でユーザー名をチェック
3. `_validate_email` でメールアドレス形式をチェック
4. `_validate_password` でパスワード強度をチェック
5. パスワードと確認用パスワードの一致チェック
6. DBでメールアドレスの重複チェック
7. `bcrypt.hashpw` でパスワードをハッシュ化してDBに保存
8. セッションを設定して自動ログイン → タイムラインへリダイレクト

---

### 5.3 タイムライン（`/`）

1. クエリパラメータから `keyword` / `category`（複数）/ `page` を取得
2. 動的にSQL条件を組み立てる
   - `keyword` がある場合：`content LIKE '%keyword%'`
   - `category` がある場合：`post_categories` をJOINして `category_id IN (...)`
3. 総件数を取得してページ数を計算（`PER_PAGE = 10`）
4. LIMIT/OFFSETで該当ページの投稿を取得
5. 各投稿に対してループでカテゴリ・いいね状態・お気に入り状態・いいね件数を付加
6. `index.html` へ渡してレンダリング

---

### 5.4 新規投稿（`/post/new`）

**POST**
1. `content` の未入力チェック・文字数チェック（1〜1000文字）
2. `categories` の未選択チェック（1つ以上必須）
3. `posts` テーブルにINSERT → `post_id` を取得
4. `post_categories` テーブルに選択カテゴリ分をINSERT
5. タイムラインへリダイレクト

---

### 5.5 投稿編集（`/post/<id>/edit`）

**GET**
1. `post_id` で投稿を取得。存在しない場合はタイムラインへ
2. 投稿の `user_id` とセッションの `user_id` を照合。不一致はエラー
3. 現在のカテゴリIDを取得して `edit_post.html` へ渡す

**POST**
1. 新規投稿と同じバリデーションを実施
2. `posts` テーブルをUPDATE
3. 対象投稿の `post_categories` を全DELETE後、新しいカテゴリをINSERT
4. タイムラインへリダイレクト

---

### 5.6 投稿削除（`/post/<id>/delete`）

1. 投稿の存在確認
2. `user_id` 照合（本人チェック）
3. `posts` テーブルからDELETE（CASCADE で関連レコードも自動削除）
4. タイムラインへリダイレクト

---

### 5.7 コメント（`/post/<id>/comment`）

**GET**
1. 投稿情報（カテゴリ・いいね状態・件数・お気に入り状態・件数）を取得
2. コメント一覧を `created_at ASC` で取得
3. `comment.html` へ渡してレンダリング

**POST**
1. `content` の未入力チェック
2. `comments` テーブルにINSERT
3. 投稿者が自分でない場合、`notifications` テーブルに `type='comment'` でINSERT
4. 同じコメント画面へリダイレクト

---

### 5.8 コメント削除（`/comment/<id>/delete`）

1. コメントの存在確認
2. `user_id` 照合（本人チェック）
3. `comments` テーブルからDELETE
4. 元のコメント画面へリダイレクト

---

### 5.9 いいね toggle（`/post/<id>/like`）

1. 投稿の存在確認
2. `likes` テーブルに既存レコードがあれば DELETE、なければ INSERT
3. INSERT時、投稿者が自分でない場合は `notifications` に `type='like'` でINSERT
4. いいね件数を再取得してJSONで返す
   ```json
   { "liked": true, "like_count": 5 }
   ```

---

### 5.10 お気に入り toggle（`/post/<id>/favorite`）

1. 投稿の存在確認
2. `favorites` テーブルに既存レコードがあれば DELETE、なければ INSERT
3. INSERT時、投稿者が自分でない場合は `notifications` に `type='favorite'` でINSERT
4. お気に入り件数を再取得してJSONで返す
   ```json
   { "favorited": true, "favorite_count": 3 }
   ```

---

### 5.11 お気に入り一覧（`/favorites`）

1. `favorites` テーブルとJOINして自分がお気に入りした投稿を取得
2. `favorites.created_at DESC` でソート、LIMIT/OFFSETでページネーション
3. 各投稿のカテゴリ・いいね状態・件数を付加
4. `favorites.html` へ渡してレンダリング

---

### 5.12 通知一覧（`/notifications`）

1. `notifications` / `users`（actor） / `posts` をJOINして自分への通知を取得
2. `created_at DESC` でソート、LIMIT/OFFSETでページネーション
3. 通知取得後に **既読から30日以上経過した通知を自動削除**
   ```sql
   DELETE FROM notifications
   WHERE user_id = ? AND is_read = 1
   AND read_at <= datetime('now', '-30 days', 'localtime')
   ```
4. `notifications.html` へ渡してレンダリング

---

### 5.13 通知既読化（`/notifications/<id>/read`）

1. `notif_id` と `user_id` で通知の存在確認（他人の通知は404）
2. `is_read = 1` / `read_at = 現在日時` でUPDATE
3. 対象投稿のコメント画面へリダイレクト

---

### 5.14 プロフィール（`/user/<username>`）

1. `username` でユーザーを検索。存在しない場合は404
2. そのユーザーの投稿を `created_at DESC` で取得（ページネーションあり）
3. カテゴリは全投稿分を一括取得（IN句）してマッピング（N+1対策）
4. `profile.html` へ渡してレンダリング

---

### 5.15 ユーザー設定（`/settings`）

**GET**
- `users` テーブルから現在のユーザー情報を取得して `user_settings.html` を表示

**POST**
1. `username` の未入力チェック
2. `profile` の文字数チェック（200文字以内）
3. アイコン画像のバリデーション（`validate_image`）
4. 画像ファイルがある場合：`user_<id>_<timestamp>.<ext>` の形式でファイル名を生成して `static/uploads/` に保存
5. `users` テーブルをUPDATE（username / profile / icon_path）
6. セッションの `username` / `user_icon` を更新
7. タイムラインへリダイレクト

---

### 5.16 管理者パネル（`/admin`）

1. 全ユーザー一覧を `id ASC` で取得
2. クエリパラメータ `q` がある場合：投稿内容またはユーザー名で検索
3. `q` がない場合：最新50件の投稿を取得
4. `admin.html` へ渡してレンダリング

---

### 5.17 管理者によるユーザー削除（`/admin/user/<id>/delete`）

1. 自分自身を削除しようとした場合はエラー
2. ユーザーの存在確認
3. `users` テーブルからDELETE（CASCADE で投稿・コメント・通知なども自動削除）
4. 管理者パネルへリダイレクト

---

### 5.18 管理者による投稿削除（`/admin/post/<id>/delete`）

1. 投稿の存在確認
2. `posts` テーブルからDELETE（CASCADE で関連レコードも自動削除）
3. 管理者パネルへリダイレクト

---

## 6. エラーハンドリング

| 状況 | 処理 |
|---|---|
| SQLiteエラー | `flash` でエラーメッセージを表示してリダイレクト |
| 存在しないリソースへのアクセス | `flash` でエラー表示 or `abort(404)` |
| 権限エラー（他人のリソース） | `flash` でエラー表示してリダイレクト |
| 404 Not Found | `404.html` を返す |
| 500 Internal Server Error | `500.html` を返す |
| いいね・お気に入りのSQLiteエラー | JSONで `{"error": "..."}` を返す（ステータス500） |
