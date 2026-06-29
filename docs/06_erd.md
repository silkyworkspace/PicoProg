# ER図

```mermaid
erDiagram
    users {
        INTEGER id PK
        TEXT username
        TEXT email UK
        TEXT password
        TEXT profile
        TEXT icon_path
        DATETIME created_at
        DATETIME updated_at
        INTEGER is_admin
    }
    posts {
        INTEGER id PK
        INTEGER user_id FK
        TEXT content
        DATETIME created_at
        DATETIME updated_at
    }
    categories {
        INTEGER id PK
        TEXT name UK
        TEXT type
        INTEGER sort_order
        DATETIME created_at
    }
    post_categories {
        INTEGER id PK
        INTEGER post_id FK
        INTEGER category_id FK
        DATETIME created_at
    }
    comments {
        INTEGER id PK
        INTEGER post_id FK
        INTEGER user_id FK
        TEXT content
        DATETIME created_at
    }
    likes {
        INTEGER id PK
        INTEGER user_id FK
        INTEGER post_id FK
        DATETIME created_at
    }
    favorites {
        INTEGER id PK
        INTEGER user_id FK
        INTEGER post_id FK
        DATETIME created_at
    }
    notifications {
        INTEGER id PK
        INTEGER user_id FK
        INTEGER actor_id FK
        TEXT type
        INTEGER post_id FK
        INTEGER is_read
        DATETIME read_at
        DATETIME created_at
    }

    users ||--o{ posts         : "投稿する"
    users ||--o{ comments      : "コメントする"
    posts ||--o{ comments      : "持つ"
    users ||--o{ likes         : "いいねする"
    posts ||--o{ likes         : "いいねされる"
    users ||--o{ favorites     : "お気に入りにする"
    posts ||--o{ favorites     : "お気に入りされる"
    posts ||--o{ post_categories : "分類される"
    categories ||--o{ post_categories : "使われる"
    users ||--o{ notifications : "受け取る"
    users ||--o{ notifications : "起こす"
    posts ||--o{ notifications : "起点になる"
```

## テーブル間の関係まとめ

| リレーション | 種別 | 説明 |
|---|---|---|
| users → posts | 1対多 | 1ユーザーが複数投稿を持つ |
| users → comments | 1対多 | 1ユーザーが複数コメントを持つ |
| posts → comments | 1対多 | 1投稿に複数コメントが付く |
| users ↔ posts（likes） | 多対多 | likes テーブルを中間テーブルとして使用 |
| users ↔ posts（favorites） | 多対多 | favorites テーブルを中間テーブルとして使用 |
| posts ↔ categories | 多対多 | post_categories テーブルを中間テーブルとして使用 |
| users（user_id） → notifications | 1対多 | 通知の受信者 |
| users（actor_id） → notifications | 1対多 | 通知を発生させたユーザー |
| posts → notifications | 1対多 | 通知の起点となった投稿 |

> **notifications の actor_id について**
> `user_id`（通知受信者）と `actor_id`（いいね・コメント・お気に入りをした人）は
> 両方 users テーブルを参照する外部キーです。自分の投稿への操作は通知を生成しません。
