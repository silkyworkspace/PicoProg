# PicoProg

プログラミング学習の進捗を投稿・共有できるSNS風Webアプリケーションです。

## 機能

- ユーザー登録・ログイン・ログアウト
- 学習進捗の投稿（カテゴリタグ付き）
- 投稿の編集・削除
- 投稿へのコメント・削除
- いいね登録・解除（カウント表示付き）
- お気に入り登録・解除（カウント表示付き）
- 通知（いいね・コメント・お気に入り時に通知、未読バッジ表示、カードクリックで個別既読化、既読から30日後に自動削除）
- キーワード検索・カテゴリ絞り込み
- タイムライン・お気に入り・通知ページのページネーション（1ページ10件）
- プロフィール編集（アイコン画像アップロード対応）
- カスタムエラーページ（404 / 500）
- 管理者機能（ユーザー一覧・削除、全投稿一覧・キーワード検索・削除）

## 技術スタック

- **バックエンド**: Python / Flask
- **データベース**: SQLite（sqlite3）
- **認証**: bcrypt（パスワードハッシュ化）
- **セキュリティ**: Flask-WTF（CSRF保護）、サーバーサイドバリデーション
- **本番環境**: PythonAnywhere

> **補足:** 開発当初はMySQLを使用していましたが、PythonAnywhere無料プランが2026年1月以降の新規アカウントでMySQL非対応となったため、Python組み込みの sqlite3 に移行しました。

## バリデーション

### バックエンド（サーバーサイド）

フロントエンドを迂回した不正リクエストからDBを守るため、サーバー側で必ずチェックを実施。

| 対象 | 検証内容 |
|---|---|
| ユーザー名 | 3〜20文字 |
| メールアドレス | 正規表現による形式チェック（登録・ログイン） |
| パスワード | 8文字以上・英字含む・数字含む |
| 投稿内容 | 1〜1000文字（新規投稿・編集） |
| プロフィール | 200文字以内 |

### フロントエンド（UX向上）

送信前にブラウザ側でチェックし、エラー時はフィールドの枠を赤くしてメッセージを直下に表示。入力を再開すると即座にエラーがクリアされる。投稿フォームには文字数カウンター（`0 / 1000`）を常時表示。

## セットアップ

### 前提条件

- Python 3.x

### 手順

1. リポジトリをクローン

```bash
git clone https://github.com/silkyworkspace/PicoProg.git
cd PicoProg
```

2. 仮想環境を作成・有効化

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. 依存パッケージをインストール

```bash
pip install -r requirements.txt
```

4. `.env` ファイルを作成

```
SECRET_KEY=your_secret_key
```

5. データベースを初期化

```bash
python database/init_db.py
```

6. アプリを起動

```bash
flask run
```

ブラウザで `http://localhost:5000` にアクセスしてください。

7. （任意）管理者ユーザーを設定

```bash
sqlite3 database/picoprog.db "UPDATE users SET is_admin = 1 WHERE email = 'your@email.com';"
```

管理者ユーザーでログインするとサイドバーに「管理者パネル」リンクが表示されます。

## テスト

```bash
source venv/bin/activate
python -m pytest tests/ -v
```

| ファイル | 件数 | 内容 |
|---|---|---|
| `tests/test_validators.py` | 16件 | メール・パスワード・ユーザー名のバリデーション |
| `tests/test_auth.py` | 8件 | 登録・ログイン・ログアウト・未ログイン保護 |
| `tests/test_posts.py` | 10件 | 投稿・コメントのCRUDと権限チェック |
| `tests/test_likes.py` | 10件 | いいねのtoggle動作と通知 |
| `tests/test_favorites.py` | 5件 | お気に入りのtoggle動作と通知 |
| `tests/test_notifications.py` | 5件 | 通知の取得・既読化・自動削除 |
| `tests/test_profile.py` | 5件 | プロフィール編集・アイコン更新 |
| `tests/test_settings.py` | 6件 | アカウント設定（ユーザー名・パスワード変更） |
| `tests/test_admin.py` | 12件 | 管理者機能のアクセス制限・検索・削除操作 |

## カテゴリ

| カテゴリ | 種別 |
|---|---|
| 学習中 | ステータス |
| 制作中 | ステータス |
| 完成・達成 | ステータス |
| Python基礎 | 技術 |
| Web開発(Flask) | 技術 |
| データベース(SQL) | 技術 |
| フロントエンド(HTML/CSS/JS) | 技術 |
| その他 | 技術 |

## ドキュメント

| ドキュメント | ファイル |
|---|---|
| 要件定義書 | [docs/01_requirements.md](docs/01_requirements.md) |
| 基本設計書 | [docs/02_basic_design.md](docs/02_basic_design.md) |
| 詳細設計書 | [docs/03_detail_design.md](docs/03_detail_design.md) |
| テーブル定義書 | [docs/04_table_definition.md](docs/04_table_definition.md) |
| 画面遷移図 | [docs/05_screen_flow.md](docs/05_screen_flow.md) |
| ER図 | [docs/06_erd.md](docs/06_erd.md) |

## 使用アイコン・ライセンス

このプロジェクトでは、以下のアイコンを使用しています。

- Lucide
  - License: ISC License
  - https://lucide.dev/license

- Google Material Symbols / Material Icons
  - License: Apache License 2.0
  - https://github.com/google/material-design-icons