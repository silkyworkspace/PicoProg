# PicoProg

プログラミング学習の進捗を投稿・共有できるSNS風Webアプリケーションです。

## 機能

- ユーザー登録・ログイン・ログアウト
- 学習進捗の投稿（カテゴリタグ付き）
- 投稿の編集・削除
- 投稿へのコメント
- いいね登録・解除（カウント表示付き）
- お気に入り登録・解除
- キーワード検索・カテゴリ絞り込み
- プロフィール編集（アイコン画像アップロード対応）

## 技術スタック

- **バックエンド**: Python / Flask
- **データベース**: MySQL
- **認証**: bcrypt（パスワードハッシュ化）
- **セキュリティ**: Flask-WTF（CSRF保護）

## セットアップ

### 前提条件

- Python 3.x
- MySQL

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
DB_PASSWORD=your_mysql_password
SECRET_KEY=your_secret_key
```

5. MySQLでデータベースを作成

```sql
CREATE DATABASE picoprog CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

6. `database/schema.sql` を参考にテーブルを作成

7. アプリを起動

```bash
python app.py
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