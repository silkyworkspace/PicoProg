import os
from datetime import timedelta
from dotenv import load_dotenv

# .envファイルを読み込む
load_dotenv()

class Config:
    # データベース接続設定（Pythonコード内でMySQLに接続するために必要）
    DB_HOST = 'localhost'
    DB_USER = 'root'
    DB_PASSWORD = os.getenv('DB_PASSWORD') # 環境変数から取得
    DB_NAME = 'picoprog'

    # セッション設定
    # SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(24)) # セッション暗号化用のランダムキー
    SECRET_KEY = os.getenv('SECRET_KEY') # SECRET_KEYを固定値に変更

    # セッション有効期限（ログインから2時間）
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)

    # アップロードフォルダ設定
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024 # 最大5MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}