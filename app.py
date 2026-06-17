from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
import bcrypt
from config import Config
import os
from datetime import datetime
from functools import wraps
from werkzeug.utils import secure_filename
from flask_wtf.csrf import CSRFProtect, generate_csrf  # ← generate_csrf を追加

# 画像アップロードの設定を追加
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# アプリケーションの初期化（Flaskアプリを作成し、設定を読み込む）
app = Flask(__name__)
app.config.from_object(Config)

# デバッグ：SECRET_KEYを確認
print("=" * 50)
print(f"SECRET_KEY: {app.config['SECRET_KEY']}")
print(f"SECRET_KEY type: {type(app.config['SECRET_KEY'])}")
print("=" * 50)

app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE  # Flaskのファイルサイズ制限

# CSRF保護を有効化
csrf = CSRFProtect(app)

# Jinjaテンプレートでcsrf_token()を使えるようにする
@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf)

# デバッグ：CSRFが有効か確認
print("=" * 50)
print(f"CSRF Protection enabled: {csrf}")
print(f"WTF_CSRF_ENABLED: {app.config.get('WTF_CSRF_ENABLED', True)}")
print("=" * 50)

# データベース接続するための関数
def get_db_connection():
    conn = mysql.connector.connect(
        host=Config.DB_HOST,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME
    )
    return conn

# 画像ファイル検証関数
def allowed_file(filename):
    """拡張子が許可されているかチェック"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_image(file):
    """画像ファイルを検証"""
    # ファイルが選択されていない
    if not file or file.filename == '':
        return True, None  # エラーなし（ファイル選択は任意）
    
    # 拡張子チェック
    if not allowed_file(file.filename):
        return False, '画像ファイル（PNG, JPG, GIF）のみアップロード可能です'
    
    # MIMEタイプチェック（本当に画像か）
    if not file.content_type.startswith('image/'):
        return False, '画像ファイルではありません'
    
    return True, None  # 検証OK

# ログイン必須デコレーター
def login_required(f):#引数として関数を受け取る
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('ログインが必要です', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs) #元の関数（f）を実行している行
    return decorated_function #新しい関数（decorated_function）を返す

# テスト用ルート
@app.route('/')
@login_required
def index():

    # 仮の投稿データ
    # posts = [
    #     {
    #         'id': 1,
    #         'username': 'program-lover',
    #         'content': '今日はFlaskに初挑戦！\nWebアプリが数行で動いたのに感動！',
    #         'created_at': datetime(2025, 9, 25, 10, 55),
    #         'categories': ['学習中', 'Web開発(Flask)'],
    #         'category_ids': [1, 5],
    #         'user_id': 2,
    #         'is_favorited': False,
    #         'icon_path': 'abcdefg.jpg'
    #     },
    #     {
    #         'id': 2,
    #         'username': 'python-master',
    #         'content': '今日はpythonのfor文の練習をしました。\n\n難しかったけど3問は自力で解けた！',
    #         'created_at': datetime(2025, 9, 20, 16, 0),
    #         'categories': ['学習中', '完成・達成', 'Python基礎'],
    #         'category_ids': [1, 2, 4],
    #         'user_id': 3,
    #         'is_favorited': True,
    #         'icon_path': None
    #     }
    # ]

    try:
        # データベース接続
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 絞り込みパラメーターを取得
        keyword = request.args.get('keyword', '').strip()
        category_ids = request.args.getlist('category') #複数選択可能
        print(f"keyword: {keyword}")
        print(f"category_ids: {category_ids}")

        # 基本のSQL
        sql = '''
        SELECT DISTINCT
            p.id,
            p.user_id,
            p.content,
            p.created_at,
            u.username,
            u.icon_path
        FROM posts p
        JOIN users u ON p.user_id = u.id
        '''
        # WHERE句とパラメーターを動的に構築
        conditions = []
        params = []

        # キーワード検索
        if keyword:
            conditions.append('p.content LIKE %s')
            params.append(f'%{keyword}%') #fがないとただの文字列になってしまう
            print(f'conditions: {conditions}')
            print(f'params: {params}')

        # カテゴリ絞り込み（複数選択対応）
        if category_ids:
            sql += 'JOIN post_categories pc ON p.id = pc.post_id'
            placeholders = ','.join(['%s'] * len(category_ids))
            conditions.append(f'pc.category_id IN ({placeholders})')
            params.extend(category_ids)
            print(f'conditions: {conditions}')
            print(f'params: {params}')
        
        # WHERE句を追加
        if conditions:
            sql += ' WHERE ' + ' AND '.join(conditions)
            

        # 並び順
        sql += ' ORDER BY p.created_at DESC'
        print(f'sql: {sql}')

        # SQLを実行
        cursor.execute(sql, tuple(params))
        posts = cursor.fetchall()
        print(f'posts: {posts}')

        # 投稿とユーザー情報を取得
        # cursor.execute('''
        #                SELECT
        #                     p.id,
        #                     p.content,
        #                     p.created_at,
        #                     p.user_id,
        #                     u.username,
        #                     u.icon_path
        #                 FROM posts p
        #                 JOIN users u ON p.user_id = u.id
        #                 ORDER BY p.created_at DESC
        #                ''')
        # posts = cursor.fetchall()

        # 各投稿のカテゴリを取得
        for post in posts:
            cursor.execute('''
                SELECT c.id, c.name
                FROM categories c
                JOIN post_categories pc ON c.id = pc.category_id
                WHERE pc.post_id = %s
                ORDER BY c.sort_order
            ''', (post['id'],)
            )
            categories = cursor.fetchall()
            post['categories'] = [cat['name'] for cat in categories] #リスト内包表記
            post['category_ids'] = [cat['id'] for cat in categories] #リスト内包表記

             # お気に入り状態を取得（ログイン中の場合のみ）
            if 'user_id' in session:
                cursor.execute('''
                    SELECT id FROM favorites
                    WHERE user_id = %s AND post_id = %s
                ''', (session['user_id'], post['id']))
                result = cursor.fetchone()
                post['is_favorited'] = result is not None

                cursor.execute(
                    'SELECT id FROM likes WHERE user_id = %s AND post_id = %s',
                    (session['user_id'], post['id'])
                )
                post['is_liked'] = cursor.fetchone() is not None
            else:
                post['is_favorited'] = False
                post['is_liked'] = False

            cursor.execute(
                'SELECT COUNT(*) AS cnt FROM likes WHERE post_id = %s',
                (post['id'],)
            )
            post['like_count'] = cursor.fetchone()['cnt']

        return render_template('index.html', posts=posts)
    
    except mysql.connector.Error as err:
        flash(f'投稿の取得に失敗しました: {err}', 'error')
        return render_template('index.html', posts=[])
    
    finally:
        cursor.close()
        conn.close()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # バリデーション
        if not email or not password:
            flash('メールアドレスとパスワードを入力してください', 'error')
            # return render_template('login.html')
            return redirect(url_for('login'))
        
        try:
            # データベース接続
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)#クエリ結果を辞書型（dict）で受け取る

            # ユーザー情報を取得
            cursor.execute(
                'SELECT id, username, password FROM users WHERE email = %s', (email,)
            )
            user = cursor.fetchone()
            print(user)

            # ユーザーが存在しない、またはパスワードが間違っている
            if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
                flash('メールアドレスまたはパスワードが間違っています', 'error')
                # return render_template('login.html')
                return redirect(url_for('login'))
            
            # セッションにユーザー情報を保存
            session['user_id'] = user['id']
            session['username'] = user['username']

            flash(f"{session['username']}さん、ログインしました", 'success')
            print(session)
            return redirect(url_for('index'))
        
        except mysql.connector.Error as err:
            flash(f'ログインに失敗しました: {err}', 'error')
            # return render_template('login.html')
            return redirect(url_for('login'))
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')

        # バリデーション
        if not username or not email or not password:
            flash('全ての項目を入力してください', 'error')
            return redirect(url_for('register'))
        
        if password != password_confirm:
            flash('パスワードが一致しません', 'error')
            return redirect(url_for('register'))
        
        # パスワードのハッシュ化
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        try:
            # データベース接続
            conn = get_db_connection()
            cursor = conn.cursor()

            # メールアドレスの重複チェック(SQLの実行)
            # users テーブルからemail が %s(つまりemail,) の行を探してその行の id カラムの値だけ取り出す
            cursor.execute('SELECT id FROM users WHERE email = %s', (email,))
            # マッチするデータがあれば → 最初の1行だけタプルで返ってくる
            if cursor.fetchone():
                flash('このメールアドレスはすでに登録されています', 'error')
                return redirect(url_for('register'))
            
            # ユーザー登録
            cursor.execute(
                'INSERT INTO users (username, email, password) VALUES (%s, %s, %s)', (username, email, hashed_password)
            )
            # SQL実行(特にデータ変更系)の確定
            conn.commit()

            # 登録したユーザーのIDを取得
            user_id = cursor.lastrowid

            # セッションにユーザー情報を保持(自動ログイン)
            session['user_id'] = user_id
            session['username'] = username

            flash('登録が完了しました', 'success')
            return redirect(url_for('index'))
        
        except mysql.connector.Error as err:
            flash(f'登録に失敗しました: {err}', 'error')
            return redirect(url_for('register'))
        finally:
            cursor.close()
            conn.close()

    return render_template('register.html')

@app.route('/logout')
def logout():
        # セッションからユーザー情報を削除
        session.pop('user_id', None)
        session.pop('username', None)

        print(session)
        flash('ログアウトしました', 'success')
        return redirect(url_for('login'))

@app.route('/post/new', methods=['GET', 'POST'])
@login_required
def new_post():
    if request.method == 'POST':
        content = request.form.get('content')
        categories = request.form.getlist('categories') # 複数のカテゴリを取得

        # バリデーション
        if not content:
            flash('投稿内容を入力してください', 'error')
            return redirect('new_post')
        
        if not categories:
            flash('カテゴリを1つ以上選択してください', 'error')
            return redirect('new_post')
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # 投稿をpostsテーブルに挿入
            cursor.execute(
                'INSERT INTO posts (user_id, content) VALUES (%s, %s)', 
                (session['user_id'], content)
            )
            post_id = cursor.lastrowid  # 挿入した投稿のID

            # カテゴリをpost_categoriesテーブルに挿入
            for category_id in categories:
                cursor.execute(
                    'INSERT INTO post_categories (post_id, category_id) VALUES (%s, %s)',
                    (post_id, category_id)
                )
            conn.commit()

            flash('投稿しました', 'success')
            return redirect(url_for('index'))
        
        except mysql.connector.Error as err:
            flash(f'投稿に失敗しました: {err}', 'error')
            return redirect('new_post')
        
        finally:
            cursor.close()
            conn.close()

    return render_template('new_post.html')

@app.route('/favorites', methods=['GET', 'POST'])
@login_required
def favorites():
    # 仮のお気に入りした投稿データ
    # posts = [
    #     {
    #         'id': 1,
    #         'username': 'program-lover',
    #         'content': '今日はFlaskに初挑戦！\nWebアプリが数行で動いたのに感動！',
    #         'created_at': datetime(2025, 9, 25, 10, 55),
    #         'categories': ['学習中', 'Web開発(Flask)'],
    #         'category_ids': [1, 5],
    #         'icon_path': 'abcdefg.jpg'
    #     },
    #     {
    #         'id': 2,
    #         'username': 'python-master',
    #         'content': '今日はpythonのfor文の練習をしました。\n\n難しかったけど3問は自力で解けた！',
    #         'created_at': datetime(2025, 9, 20, 16, 0),
    #         'categories': ['学習中', '完成・達成', 'Python基礎'],
    #         'category_ids': [1, 2, 4],
    #         'icon_path': None
    #     }
    # ]

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # お気に入り登録した投稿を取得
        cursor.execute('''
            SELECT 
                    p.id, 
                    p.content,
                    p.created_at,
                    p.user_id,
                    u.username,
                    u.icon_path
            FROM posts p
            JOIN users u  ON p.user_id = u.id
            JOIN favorites f ON p.id = f.post_id
            WHERE f.user_id = %s
            ORDER BY f.created_at DESC
        ''', (session['user_id'], ))

        posts = cursor.fetchall()

        # 各投稿のカテゴリを取得
        for post in posts:
            cursor.execute('''
                SELECT c.id, c.name
                FROM categories c
                JOIN post_categories pc ON c.id = pc.category_id
                WHERE pc.post_id = %s
                ORDER BY c.sort_order
            ''', (post['id'], ))
            categories = cursor.fetchall()
            post['categories'] = [cat['name'] for cat in categories] #リスト内包表記
            post['category_ids'] = [cat['id'] for cat in categories] #リスト内包表記

            post['is_favorited'] = True

            cursor.execute(
                'SELECT id FROM likes WHERE user_id = %s AND post_id = %s',
                (session['user_id'], post['id'])
            )
            post['is_liked'] = cursor.fetchone() is not None

            cursor.execute(
                'SELECT COUNT(*) AS cnt FROM likes WHERE post_id = %s',
                (post['id'],)
            )
            post['like_count'] = cursor.fetchone()['cnt']

        return render_template('favorites.html', posts=posts)
    
    except mysql.connector.Error as err:
        flash(f'投稿の取得に失敗しました: {err}', 'error')
        return render_template('index.html', posts=[])
    
    finally:
        cursor.close()
        conn.close()

# お気に入り登録/解除のルート
@app.route('/post/<int:post_id>/favorite', methods=['POST'])
@login_required
def toggle_favorite(post_id):
    try:
        # データベース接続
        conn = get_db_connection()
        cursor = conn.cursor()

        # 登録が存在するか確認
        cursor.execute('''
                        SELECT id FROM posts WHERE id = %s
                       ''', (post_id,))
        if not cursor.fetchone():
            flash('投稿が見つかりません', 'error')
            return redirect(url_for('index'))
        
        # 既にお気に入り登録されているか確認
        cursor.execute('''
                SELECT id FROM favorites WHERE user_id = %s AND post_id = %s
                    ''', (session['user_id'], post_id))
        favorite = cursor.fetchone()
        print(favorite)

        if favorite:
            # お気に入り解除
            cursor.execute('''
                        DELETE FROM favorites WHERE user_id = %s AND post_id = %s
                        ''', (session['user_id'], post_id))
            flash('お気に入りから削除しました', 'success')
        else:
            cursor.execute('''
            INSERT INTO favorites (user_id, post_id) VALUES (%s, %s)
            ''', (session['user_id'], post_id))
            flash('お気に入りに追加しました。', 'success')
        
        conn.commit()

        # request.referrer は直前にいたページURLを取得する
        return redirect(request.referrer or url_for('index'))
    
    except mysql.connector.Error as err:
        flash(f'処理に失敗しました: {err}', 'error')
        return redirect(url_for('index'))
    
    finally:
        cursor.close()
        conn.close()


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def user_settings():

    # 仮のユーザーデータ
    # user = {
    #     'username': 'program-lover',
    #     'profile': '',
    #     'icon_path': None
    # }

    try:
        # データベース接続
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute('''
                    SELECT
                        id,
                        username,
                        profile,
                        icon_path
                    FROM users
                    WHERE id = %s;
                ''', (session['user_id'],))
        
        user = cursor.fetchone()
        print(user)

        # バリデーション
        if not user:
            flash('ユーザー情報が見つかりません', 'error')

        # POST処理（更新）
        if request.method == 'POST':
            username = request.form.get('username')
            profile = request.form.get('profile')
            icon = request.files.get('icon') # ← 画像ファイル取得

            print(f"username: {username}")
            print(f"profile: {profile}")
            print(f"icon: {icon}")
            print(f"icon.filename: {icon.filename if icon else 'None'}")

            # バリデーション
            if not username:
                flash('ユーザー名を入力してください', 'error')
                render_template('user_setting.html', user=user)
            
            # 画像ファイルの検証 ← ここを追加
            is_valid, error_message = validate_image(icon) # タプルのアンパッっく代入
            if not is_valid:
                flash(error_message, 'error')
                return render_template('user_settings.html', user=user)

            # 画像のアップロード処理
            icon_filename = user['icon_path'] # 既存のファイル名を保持

            if icon and icon_filename != '':
                # ファイル名をユニークにする（ユーザーID + タイムスタンプ）
                # import os
                # from werkzeug.utils import secure_filename

                # 拡張子を取得
                ext = os.path.splitext(secure_filename(icon.filename))[1]

                # 新しいファイル名を生成
                icon_filename = f"user_{session['user_id']}_{int(datetime.now().timestamp())}{ext}"

                # 保存先のパス
                upload_folder = os.path.join(app.root_path, 'static', 'uploads')

                # uploadsフォルダがなければ作成
                os.makedirs(upload_folder, exist_ok=True)

                # 画像を保存
                icon.save(os.path.join(upload_folder, icon_filename))
            
            # ユーザー情報を更新
            cursor.execute('''
                        UPDATE
                           users
                        SET
                           username = %s,
                           profile = %s,
                           icon_path = %s
                        WHERE
                           id = %s
                        ''', (username, profile, icon_filename, session['user_id']))
            
            conn.commit()

            # セッションのユーザー名を更新
            session['username'] = username

            flash('設定を更新しました', 'success')
            return redirect(url_for('index'))
        
        # GET処理（表示）
        return render_template('user_settings.html', user=user)

    except mysql.connector.Error as err:
        flash(f'処理に失敗しました: {err}', 'error')
        return redirect(url_for('index'))
    
    finally:
        cursor.close()
        conn.close()

@app.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):

    # 仮の投稿データ
    # post = {
    #     'id': post_id,
    #     'content': '既存の投稿内容です',
    #     'category_ids': [1, 5]  # チェック済みカテゴリ
    # }

    try:
        # データベース接続
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 投稿データを取得
        cursor.execute('''
                        SELECT p.id, p.content, p.user_id
                        FROM posts p
                        WHERE p.id = %s
                        ''', (post_id,))
        post = cursor.fetchone()

        # 投稿が存在しない
        if not post:
            flash('投稿が見つかりません', 'error')
            return redirect(url_for('index'))
        
        # 自分の投稿でない場合は編集不可
        if post['user_id'] != session['user_id']:
            flash('他のユーザーの投稿は編集できません', 'error')
            return redirect(url_for('index'))
        
        # カテゴリを取得
        cursor.execute('''
                        SELECT category_id
                        FROM post_categories
                        WHERE post_id = %s
                       ''', (post_id,))
        
        categories = cursor.fetchall()
        print(f'categories: {categories}')
        post['category_ids'] = [cat['category_id'] for cat in categories]

        # POST処理（更新）
        if request.method == 'POST':
            content = request.form.get('content')
            new_categories = request.form.getlist('categories')

            # バリデーション
            if not content:
                flash('投稿内容を入力してください', 'error')
                return render_template('edit_post.html', post=post)
            
            if not new_categories:
                flash('カテゴリを1つ以上選択してください', 'error')
                return render_template('edit_post.html', post=post)
            
            # 投稿を更新
            cursor.execute('''
                            UPDATE posts SET content = %s WHERE id = %s
                            ''', (content, post_id))
            
            # 既存のカテゴリを削除
            cursor.execute('''
                DELETE FROM post_categories WHERE post_id = %s
                ''', (post_id,))
            
            # 新しいカテゴリを挿入
            for category_id in new_categories:
                cursor.execute('''
                                INSERT INTO post_categories (post_id, category_id) VALUES (%s, %s)
                               ''' ,(post_id, category_id))
            conn.commit()

            flash('投稿を更新しました', 'success')
            return redirect(url_for('index')) #データベースの更新に関わるので、PRGリダイレクト
     
        # GET処理（表示）
        return render_template('edit_post.html', post=post)
    
    except mysql.connector.Error as err:
        flash(f'処理に失敗しました: {err}', 'error')
        return redirect(url_for('index'))
    
    finally:
        cursor.close()
        conn.close()

@app.route('/post/<int:post_id>/comment', methods=['GET', 'POST'])
@login_required
def comment(post_id):

    # 仮の投稿データ
    # post = {
    #     'id': post_id,
    #     'username': 'program-lover',
    #     'content': '今日はFlaskに初挑戦！\nWebアプリが数行で動いたのに感動！',
    #     'created_at': datetime.now(),
    #     'categories': ['学習中', 'Web開発(Flask)'],
    #     'category_ids': [1, 5]  # チェック済みカテゴリ
    # }
    # 仮のコメントデータを作成
    # comments = [
    #     {
    #         'username': 'python-master',
    #         'content': 'Flaskいいですよね！私も最初感動しました',
    #         'created_at': datetime.now(),
    #     }
    # ]

    try:
        # データベース接続
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 投稿データを取得
        cursor.execute('''
                        SELECT
                            p.id,
                            p.content,
                            p.created_at,
                            u.username,
                            u.icon_path
                        FROM posts p
                        JOIN users u ON p.user_id = u.id
                        WHERE p.id = %s
                        ''', (post_id,))
        post = cursor.fetchone()
        print(post)

        # 投稿が存在しない
        if not post:
            flash('投稿が見つかりません', 'error')
            return redirect(url_for('index'))
        
        # 各投稿のカテゴリを取得
        cursor.execute('''
            SELECT c.id, c.name
            FROM categories c
            JOIN post_categories pc ON c.id = pc.category_id
            WHERE pc.post_id = %s
            ORDER BY c.sort_order
        ''', (post['id'],)
        )
        categories = cursor.fetchall()
        post['categories'] = [cat['name'] for cat in categories]

        # いいね情報を取得
        cursor.execute(
            'SELECT id FROM likes WHERE user_id = %s AND post_id = %s',
            (session['user_id'], post['id'])
        )
        post['is_liked'] = cursor.fetchone() is not None
        cursor.execute(
            'SELECT COUNT(*) AS cnt FROM likes WHERE post_id = %s',
            (post['id'],)
        )
        post['like_count'] = cursor.fetchone()['cnt']

        # コメント一覧の取得
        cursor.execute('''
                SELECT
                       c.id,
                       c.content,
                       c.created_at,
                       u.username,
                       u.icon_path
                FROM comments c
                JOIN users u ON c.user_id = u.id
                WHERE c.post_id = %s
                       ORDER BY c.created_at ASC
                ''', (post_id, ))
        comments = cursor.fetchall()

        # POST処理（コメント投稿）
        if request.method == 'POST':
            content = request.form.get('content')

            # バリデーション
            if not content:
                flash('コメント内容を入力してください', 'error')
                # コメント一覧の取得
                cursor.execute('''
                        SELECT
                            c.id,
                            c.content,
                            c.created_at,
                            u.username,
                            u.icon_path
                        FROM comments c
                        JOIN users u ON c.user_id = u.id
                        WHERE c.post_id = %s
                            ORDER BY c.created_at ASC
                        ''', (post_id, ))
                comments = cursor.fetchall()
                return render_template('comment.html', post=post, comments=comments)
            
            # コメントを保存
            cursor.execute('''
                            INSERT INTO comments (post_id, user_id, content) VALUES (%s, %s, %s)
                        ''', (post_id, session['user_id'], content))
            # SQL実行(特にデータ変更系)の確定
            conn.commit()

            flash('コメントしました', 'success')
            return redirect(url_for('comment', post_id=post_id)) #PRG
        
        # コメント一覧の取得
        cursor.execute('''
                SELECT
                    c.id,
                    c.content,
                    c.created_at,
                    u.username,
                    u.icon_path
                FROM comments c
                JOIN users u ON c.user_id = u.id
                WHERE c.post_id = %s
                    ORDER BY c.created_at ASC
                ''', (post_id, ))
        comments = cursor.fetchall()
        return render_template('comment.html', post=post, comments=comments)

    except mysql.connector.Error as err:
        flash(f'処理に失敗しました: {err}', 'error')
        return redirect(url_for('index'))
    
    finally:
        cursor.close()
        conn.close()

# いいね登録/解除のルート
@app.route('/post/<int:post_id>/like', methods=['POST'])
@login_required
def toggle_like(post_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT id FROM posts WHERE id = %s', (post_id,))
        if not cursor.fetchone():
            flash('投稿が見つかりません', 'error')
            return redirect(url_for('index'))

        cursor.execute(
            'SELECT id FROM likes WHERE user_id = %s AND post_id = %s',
            (session['user_id'], post_id)
        )
        like = cursor.fetchone()

        if like:
            cursor.execute(
                'DELETE FROM likes WHERE user_id = %s AND post_id = %s',
                (session['user_id'], post_id)
            )
        else:
            cursor.execute(
                'INSERT INTO likes (user_id, post_id) VALUES (%s, %s)',
                (session['user_id'], post_id)
            )

        conn.commit()
        return redirect(request.referrer or url_for('index'))

    except mysql.connector.Error as err:
        flash(f'処理に失敗しました: {err}', 'error')
        return redirect(url_for('index'))

    finally:
        cursor.close()
        conn.close()


# delete_post 投稿を削除する処理
@app.route('/post/<int:post_id>/delete', methods=['POST']) #メソッドをPOSTのみに...GETでの削除は危険（URLアクセスだけで削除されてしまう）
@login_required
def delete_post(post_id):
    try:
        # データベース接続
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 投稿を取得（権限チェック用）
        cursor.execute('''
            SELECT user_id FROM posts WHERE id = %s
            ''', (post_id,)
        )
        post = cursor.fetchone()

        # 投稿が存在しない
        if not post:
            flash('投稿が見つかりません', 'error')
            return redirect(url_for('index'))
        
        # 自分の投稿でない場合は削除不可
        if post['user_id'] != session['user_id']:
            flash('他のユーザーの投稿は削除できません', 'error')
            return redirect(url_for('index'))
        
        # 投稿を削除（ON DELETE CASCADEでカテゴリ・コメント・お気に入りも自動削除）
        cursor.execute('''
                    DELETE FROM posts WHERE id = %s
                    ''', (post_id,)
        )

        conn.commit()

        flash('投稿を削除しました', 'success')
        return redirect(url_for('index'))
    
    except mysql.connector.Error as err:

        flash(f'削除に失敗しました: {err}', 'error')
        return redirect(url_for('index'))
    
    finally:
        cursor.close()
        conn.close()

# このファイルを直接実行した時にFlaskサーバーを起動
# debug=True = エラーが見やすくなる開発モード
if __name__ == '__main__':
    app.run(debug=True)