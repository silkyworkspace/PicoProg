# PicoProg

プログラミング学習の進捗を投稿・共有できるSNS風Webアプリケーションです。

## 機能

- ユーザー登録・ログイン・ログアウト
- 学習進捗の投稿（カテゴリタグ付き）
- 投稿の編集・削除
- 投稿へのコメント・削除
- いいね登録・解除（カウント表示付き）
- お気に入り登録・解除（カウント表示付き）
- キーワード検索・カテゴリ絞り込み
- タイムライン・お気に入りページのページネーション（1ページ10件）
- プロフィール編集（アイコン画像アップロード対応）
- カスタムエラーページ（404 / 500）

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

## 使用アイコン・ライセンス

このプロジェクトでは、以下のアイコンを使用しています。

- Lucide
  - License: ISC License
  - https://lucide.dev/license

- Google Material Symbols / Material Icons
  - License: Apache License 2.0
  - https://github.com/google/material-design-icons