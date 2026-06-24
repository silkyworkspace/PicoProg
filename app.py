from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, abort
import sqlite3
import bcrypt
import re
from config import Config
import os
from datetime import datetime
from functools import wraps
from werkzeug.utils import secure_filename
from flask_wtf.csrf import CSRFProtect, generate_csrf

# SQLiteのDATETIME型をPythonのdatetimeに自動変換
def _convert_datetime(val):
    return datetime.strptime(val.decode(), '%Y-%m-%d %H:%M:%S')

sqlite3.register_converter("DATETIME", _convert_datetime)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

USERNAME_MIN = 3
USERNAME_MAX = 20
POST_MAX = 1000
PER_PAGE = 10

def _validate_email(email):
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return bool(re.match(pattern, email))

def _validate_password(password):
    if len(password) < 8:
        return False, 'パスワードは8文字以上で入力してください'
    if not re.search(r'[a-zA-Z]', password):
        return False, 'パスワードには英字を含めてください'
    if not re.search(r'[0-9]', password):
        return False, 'パスワードには数字を含めてください'
    return True, None

def _validate_username(username):
    if len(username) < USERNAME_MIN or len(username) > USERNAME_MAX:
        return False, f'ユーザー名は{USERNAME_MIN}〜{USERNAME_MAX}文字で入力してください'
    return True, None

app = Flask(__name__)
app.config.from_object(Config)
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

csrf = CSRFProtect(app)

@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf)

@app.context_processor
def inject_globals():
    return dict(current_year=datetime.now().year)

@app.context_processor
def inject_unread_count():
    if 'user_id' not in session:
        return dict(unread_notification_count=0)
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT COUNT(*) AS cnt FROM notifications WHERE user_id = ? AND is_read = 0',
            (session['user_id'],)
        )
        count = cursor.fetchone()['cnt']
    except Exception:
        count = 0
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
    return dict(unread_notification_count=count)


def get_db_connection():
    conn = sqlite3.connect(Config.DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_image(file):
    if not file or file.filename == '':
        return True, None
    if not allowed_file(file.filename):
        return False, '画像ファイル（PNG, JPG, GIF）のみアップロード可能です'
    if not file.content_type.startswith('image/'):
        return False, '画像ファイルではありません'
    return True, None

@app.before_request
def load_user_icon():
    if 'user_id' in session and 'user_icon' not in session:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT icon_path FROM users WHERE id = ?', (session['user_id'],))
            user = cursor.fetchone()
            session['user_icon'] = user['icon_path'] if user else None
        except Exception:
            session['user_icon'] = None
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if not session.get('is_admin'):
            flash('管理者のみアクセスできます', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
@login_required
def index():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        keyword = request.args.get('keyword', '').strip()
        category_ids = request.args.getlist('category')
        page = request.args.get('page', 1, type=int)
        if page < 1:
            page = 1

        sql = '''
        SELECT DISTINCT
            p.id,
            p.user_id,
            p.content,
            p.created_at,
            u.username,
            u.icon_path,
            (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.id) AS comment_count,
            (SELECT COUNT(*) FROM favorites fv WHERE fv.post_id = p.id) AS favorite_count
        FROM posts p
        JOIN users u ON p.user_id = u.id
        '''
        conditions = []
        params = []

        if keyword:
            conditions.append('p.content LIKE ?')
            params.append(f'%{keyword}%')

        if category_ids:
            sql += 'JOIN post_categories pc ON p.id = pc.post_id'
            placeholders = ','.join(['?'] * len(category_ids))
            conditions.append(f'pc.category_id IN ({placeholders})')
            params.extend(category_ids)

        if conditions:
            sql += ' WHERE ' + ' AND '.join(conditions)

        sql += ' ORDER BY p.created_at DESC'

        count_sql = f'SELECT COUNT(*) AS total FROM ({sql}) AS sub'
        cursor.execute(count_sql, tuple(params))
        total = cursor.fetchone()['total']

        total_pages = max(1, -(-total // PER_PAGE))
        offset = (page - 1) * PER_PAGE

        sql += ' LIMIT ? OFFSET ?'
        cursor.execute(sql, tuple(params) + (PER_PAGE, offset))
        posts = [dict(row) for row in cursor.fetchall()]

        for post in posts:
            cursor.execute('''
                SELECT c.id, c.name
                FROM categories c
                JOIN post_categories pc ON c.id = pc.category_id
                WHERE pc.post_id = ?
                ORDER BY c.sort_order
            ''', (post['id'],))
            categories = cursor.fetchall()
            post['categories'] = [cat['name'] for cat in categories]
            post['category_ids'] = [cat['id'] for cat in categories]

            if 'user_id' in session:
                cursor.execute(
                    'SELECT id FROM favorites WHERE user_id = ? AND post_id = ?',
                    (session['user_id'], post['id'])
                )
                post['is_favorited'] = cursor.fetchone() is not None

                cursor.execute(
                    'SELECT id FROM likes WHERE user_id = ? AND post_id = ?',
                    (session['user_id'], post['id'])
                )
                post['is_liked'] = cursor.fetchone() is not None
            else:
                post['is_favorited'] = False
                post['is_liked'] = False

            cursor.execute(
                'SELECT COUNT(*) AS cnt FROM likes WHERE post_id = ?',
                (post['id'],)
            )
            post['like_count'] = cursor.fetchone()['cnt']

        return render_template('index.html', posts=posts, page=page, total_pages=total_pages)

    except sqlite3.Error as err:
        flash(f'投稿の取得に失敗しました: {err}', 'error')
        return render_template('index.html', posts=[], page=1, total_pages=1)

    finally:
        cursor.close()
        conn.close()


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            flash('メールアドレスとパスワードを入力してください', 'error')
            return redirect(url_for('login'))

        if not _validate_email(email):
            flash('メールアドレスの形式が正しくありません', 'error')
            return redirect(url_for('login'))

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                'SELECT id, username, password, icon_path, is_admin FROM users WHERE email = ?', (email,)
            )
            user = cursor.fetchone()

            if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
                flash('メールアドレスまたはパスワードが間違っています', 'error')
                return redirect(url_for('login'))

            session.permanent = True
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['user_icon'] = user['icon_path']
            session['is_admin'] = bool(user['is_admin'])

            flash(f"{session['username']}さん、ログインしました", 'success')
            return redirect(url_for('index'))

        except sqlite3.Error as err:
            flash(f'ログインに失敗しました: {err}', 'error')
            return redirect(url_for('login'))
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')

        if not username or not email or not password or not password_confirm:
            flash('全ての項目を入力してください', 'error')
            return redirect(url_for('register'))

        ok, msg = _validate_username(username)
        if not ok:
            flash(msg, 'error')
            return redirect(url_for('register'))

        if not _validate_email(email):
            flash('メールアドレスの形式が正しくありません', 'error')
            return redirect(url_for('register'))

        ok, msg = _validate_password(password)
        if not ok:
            flash(msg, 'error')
            return redirect(url_for('register'))

        if password != password_confirm:
            flash('パスワードが一致しません', 'error')
            return redirect(url_for('register'))

        # decode() でテキスト文字列としてDBに保存する
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
            if cursor.fetchone():
                flash('このメールアドレスはすでに登録されています', 'error')
                return redirect(url_for('register'))

            cursor.execute(
                'INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                (username, email, hashed_password)
            )
            conn.commit()

            user_id = cursor.lastrowid

            session.permanent = True
            session['user_id'] = user_id
            session['username'] = username
            session['user_icon'] = None

            flash('登録が完了しました', 'success')
            return redirect(url_for('index'))

        except sqlite3.Error as err:
            flash(f'登録に失敗しました: {err}', 'error')
            return redirect(url_for('register'))
        finally:
            cursor.close()
            conn.close()

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('ログアウトしました', 'success')
    return redirect(url_for('login'))


@app.route('/post/new', methods=['GET', 'POST'])
@login_required
def new_post():
    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        categories = request.form.getlist('categories')

        if not content:
            flash('投稿内容を入力してください', 'error')
            return redirect(url_for('new_post'))

        if len(content) > POST_MAX:
            flash(f'投稿内容は{POST_MAX}文字以内で入力してください（現在{len(content)}文字）', 'error')
            return redirect(url_for('new_post'))

        if not categories:
            flash('カテゴリを1つ以上選択してください', 'error')
            return redirect(url_for('new_post'))

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                'INSERT INTO posts (user_id, content) VALUES (?, ?)',
                (session['user_id'], content)
            )
            post_id = cursor.lastrowid

            for category_id in categories:
                cursor.execute(
                    'INSERT INTO post_categories (post_id, category_id) VALUES (?, ?)',
                    (post_id, category_id)
                )
            conn.commit()

            flash('投稿しました', 'success')
            return redirect(url_for('index'))

        except sqlite3.Error as err:
            flash(f'投稿に失敗しました: {err}', 'error')
            return redirect(url_for('new_post'))

        finally:
            cursor.close()
            conn.close()

    return render_template('new_post.html')


@app.route('/favorites', methods=['GET', 'POST'])
@login_required
def favorites():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        page = request.args.get('page', 1, type=int)
        if page < 1:
            page = 1

        cursor.execute('''
            SELECT COUNT(*) AS total
            FROM favorites
            WHERE user_id = ?
        ''', (session['user_id'],))
        total = cursor.fetchone()['total']
        total_pages = max(1, -(-total // PER_PAGE))

        offset = (page - 1) * PER_PAGE

        cursor.execute('''
            SELECT
                p.id,
                p.content,
                p.created_at,
                p.user_id,
                u.username,
                u.icon_path,
                (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.id) AS comment_count,
                (SELECT COUNT(*) FROM favorites fv WHERE fv.post_id = p.id) AS favorite_count
            FROM posts p
            JOIN users u  ON p.user_id = u.id
            JOIN favorites f ON p.id = f.post_id
            WHERE f.user_id = ?
            ORDER BY f.created_at DESC
            LIMIT ? OFFSET ?
        ''', (session['user_id'], PER_PAGE, offset))

        posts = [dict(row) for row in cursor.fetchall()]

        for post in posts:
            cursor.execute('''
                SELECT c.id, c.name
                FROM categories c
                JOIN post_categories pc ON c.id = pc.category_id
                WHERE pc.post_id = ?
                ORDER BY c.sort_order
            ''', (post['id'],))
            categories = cursor.fetchall()
            post['categories'] = [cat['name'] for cat in categories]
            post['category_ids'] = [cat['id'] for cat in categories]

            post['is_favorited'] = True

            cursor.execute(
                'SELECT id FROM likes WHERE user_id = ? AND post_id = ?',
                (session['user_id'], post['id'])
            )
            post['is_liked'] = cursor.fetchone() is not None

            cursor.execute(
                'SELECT COUNT(*) AS cnt FROM likes WHERE post_id = ?',
                (post['id'],)
            )
            post['like_count'] = cursor.fetchone()['cnt']

        return render_template('favorites.html', posts=posts, page=page, total_pages=total_pages)

    except sqlite3.Error as err:
        flash(f'投稿の取得に失敗しました: {err}', 'error')
        return render_template('favorites.html', posts=[], page=1, total_pages=1)

    finally:
        cursor.close()
        conn.close()


@app.route('/post/<int:post_id>/favorite', methods=['POST'])
@login_required
def toggle_favorite(post_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT id, user_id FROM posts WHERE id = ?', (post_id,))
        post = cursor.fetchone()
        if not post:
            flash('投稿が見つかりません', 'error')
            return redirect(url_for('index'))

        cursor.execute(
            'SELECT id FROM favorites WHERE user_id = ? AND post_id = ?',
            (session['user_id'], post_id)
        )
        favorite = cursor.fetchone()

        if favorite:
            cursor.execute(
                'DELETE FROM favorites WHERE user_id = ? AND post_id = ?',
                (session['user_id'], post_id)
            )
            is_favorited = False
        else:
            cursor.execute(
                'INSERT INTO favorites (user_id, post_id) VALUES (?, ?)',
                (session['user_id'], post_id)
            )
            is_favorited = True
            if post['user_id'] != session['user_id']:
                cursor.execute(
                    'INSERT INTO notifications (user_id, actor_id, type, post_id) VALUES (?, ?, ?, ?)',
                    (post['user_id'], session['user_id'], 'favorite', post_id)
                )

        conn.commit()

        cursor.execute('SELECT COUNT(*) AS cnt FROM favorites WHERE post_id = ?', (post_id,))
        favorite_count = cursor.fetchone()['cnt']
        return jsonify({'favorited': is_favorited, 'favorite_count': favorite_count})

    except sqlite3.Error as err:
        return jsonify({'error': str(err)}), 500

    finally:
        cursor.close()
        conn.close()


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def user_settings():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, username, profile, icon_path
            FROM users
            WHERE id = ?
        ''', (session['user_id'],))

        user = dict(cursor.fetchone())

        if not user:
            flash('ユーザー情報が見つかりません', 'error')

        if request.method == 'POST':
            username = request.form.get('username')
            profile = request.form.get('profile')
            icon = request.files.get('icon')

            if not username:
                flash('ユーザー名を入力してください', 'error')
                return render_template('user_settings.html', user=user)

            if profile and len(profile) > 200:
                flash('プロフィールは200文字以内で入力してください', 'error')
                return render_template('user_settings.html', user=user)

            is_valid, error_message = validate_image(icon)
            if not is_valid:
                flash(error_message, 'error')
                return render_template('user_settings.html', user=user)

            icon_filename = user['icon_path']

            if icon and icon.filename != '':
                ext = os.path.splitext(secure_filename(icon.filename))[1]
                icon_filename = f"user_{session['user_id']}_{int(datetime.now().timestamp())}{ext}"

                upload_folder = os.path.join(app.root_path, 'static', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                icon.save(os.path.join(upload_folder, icon_filename))

            cursor.execute('''
                UPDATE users
                SET username = ?, profile = ?, icon_path = ?
                WHERE id = ?
            ''', (username, profile, icon_filename, session['user_id']))

            conn.commit()

            session['username'] = username
            session['user_icon'] = icon_filename

            flash('設定を更新しました', 'success')
            return redirect(url_for('index'))

        return render_template('user_settings.html', user=user)

    except sqlite3.Error as err:
        flash(f'処理に失敗しました: {err}', 'error')
        return redirect(url_for('index'))

    finally:
        cursor.close()
        conn.close()


@app.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT p.id, p.content, p.user_id
            FROM posts p
            WHERE p.id = ?
        ''', (post_id,))
        row = cursor.fetchone()

        if not row:
            flash('投稿が見つかりません', 'error')
            return redirect(url_for('index'))

        post = dict(row)

        if post['user_id'] != session['user_id']:
            flash('他のユーザーの投稿は編集できません', 'error')
            return redirect(url_for('index'))

        cursor.execute(
            'SELECT category_id FROM post_categories WHERE post_id = ?',
            (post_id,)
        )
        post['category_ids'] = [cat['category_id'] for cat in cursor.fetchall()]

        if request.method == 'POST':
            content = request.form.get('content', '').strip()
            new_categories = request.form.getlist('categories')

            if not content:
                flash('投稿内容を入力してください', 'error')
                return render_template('edit_post.html', post=post)

            if len(content) > POST_MAX:
                flash(f'投稿内容は{POST_MAX}文字以内で入力してください（現在{len(content)}文字）', 'error')
                return render_template('edit_post.html', post=post)

            if not new_categories:
                flash('カテゴリを1つ以上選択してください', 'error')
                return render_template('edit_post.html', post=post)

            cursor.execute('UPDATE posts SET content = ? WHERE id = ?', (content, post_id))
            cursor.execute('DELETE FROM post_categories WHERE post_id = ?', (post_id,))

            for category_id in new_categories:
                cursor.execute(
                    'INSERT INTO post_categories (post_id, category_id) VALUES (?, ?)',
                    (post_id, category_id)
                )
            conn.commit()

            flash('投稿を更新しました', 'success')
            return redirect(url_for('index'))

        return render_template('edit_post.html', post=post)

    except sqlite3.Error as err:
        flash(f'処理に失敗しました: {err}', 'error')
        return redirect(url_for('index'))

    finally:
        cursor.close()
        conn.close()


@app.route('/post/<int:post_id>/comment', methods=['GET', 'POST'])
@login_required
def comment(post_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT p.id, p.user_id, p.content, p.created_at, u.username, u.icon_path
            FROM posts p
            JOIN users u ON p.user_id = u.id
            WHERE p.id = ?
        ''', (post_id,))
        row = cursor.fetchone()

        if not row:
            flash('投稿が見つかりません', 'error')
            return redirect(url_for('index'))

        post = dict(row)

        cursor.execute('''
            SELECT c.id, c.name
            FROM categories c
            JOIN post_categories pc ON c.id = pc.category_id
            WHERE pc.post_id = ?
            ORDER BY c.sort_order
        ''', (post['id'],))
        categories = cursor.fetchall()
        post['categories'] = [cat['name'] for cat in categories]

        cursor.execute(
            'SELECT id FROM likes WHERE user_id = ? AND post_id = ?',
            (session['user_id'], post['id'])
        )
        post['is_liked'] = cursor.fetchone() is not None

        cursor.execute(
            'SELECT COUNT(*) AS cnt FROM likes WHERE post_id = ?',
            (post['id'],)
        )
        post['like_count'] = cursor.fetchone()['cnt']

        cursor.execute(
            'SELECT id FROM favorites WHERE user_id = ? AND post_id = ?',
            (session['user_id'], post['id'])
        )
        post['is_favorited'] = cursor.fetchone() is not None

        cursor.execute(
            'SELECT COUNT(*) AS cnt FROM favorites WHERE post_id = ?',
            (post['id'],)
        )
        post['favorite_count'] = cursor.fetchone()['cnt']

        if request.method == 'POST':
            content = request.form.get('content', '').strip()

            if not content:
                flash('コメント内容を入力してください', 'error')
                cursor.execute('''
                    SELECT c.id, c.content, c.created_at, c.user_id, u.username, u.icon_path
                    FROM comments c
                    JOIN users u ON c.user_id = u.id
                    WHERE c.post_id = ?
                    ORDER BY c.created_at ASC
                ''', (post_id,))
                comments = cursor.fetchall()
                return render_template('comment.html', post=post, comments=comments)

            cursor.execute(
                'INSERT INTO comments (post_id, user_id, content) VALUES (?, ?, ?)',
                (post_id, session['user_id'], content)
            )
            if post['user_id'] != session['user_id']:
                cursor.execute(
                    'INSERT INTO notifications (user_id, actor_id, type, post_id) VALUES (?, ?, ?, ?)',
                    (post['user_id'], session['user_id'], 'comment', post_id)
                )
            conn.commit()

            flash('コメントしました', 'success')
            return redirect(url_for('comment', post_id=post_id))

        cursor.execute('''
            SELECT c.id, c.content, c.created_at, c.user_id, u.username, u.icon_path
            FROM comments c
            JOIN users u ON c.user_id = u.id
            WHERE c.post_id = ?
            ORDER BY c.created_at ASC
        ''', (post_id,))
        comments = cursor.fetchall()
        return render_template('comment.html', post=post, comments=comments)

    except sqlite3.Error as err:
        flash(f'処理に失敗しました: {err}', 'error')
        return redirect(url_for('index'))

    finally:
        cursor.close()
        conn.close()


@app.route('/post/<int:post_id>/like', methods=['POST'])
@login_required
def toggle_like(post_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT id, user_id FROM posts WHERE id = ?', (post_id,))
        post = cursor.fetchone()
        if not post:
            flash('投稿が見つかりません', 'error')
            return redirect(url_for('index'))

        cursor.execute(
            'SELECT id FROM likes WHERE user_id = ? AND post_id = ?',
            (session['user_id'], post_id)
        )
        like = cursor.fetchone()

        if like:
            cursor.execute(
                'DELETE FROM likes WHERE user_id = ? AND post_id = ?',
                (session['user_id'], post_id)
            )
            is_liked = False
        else:
            cursor.execute(
                'INSERT INTO likes (user_id, post_id) VALUES (?, ?)',
                (session['user_id'], post_id)
            )
            is_liked = True
            if post['user_id'] != session['user_id']:
                cursor.execute(
                    'INSERT INTO notifications (user_id, actor_id, type, post_id) VALUES (?, ?, ?, ?)',
                    (post['user_id'], session['user_id'], 'like', post_id)
                )

        conn.commit()

        cursor.execute('SELECT COUNT(*) AS cnt FROM likes WHERE post_id = ?', (post_id,))
        like_count = cursor.fetchone()['cnt']
        return jsonify({'liked': is_liked, 'like_count': like_count})

    except sqlite3.Error as err:
        return jsonify({'error': str(err)}), 500

    finally:
        cursor.close()
        conn.close()


@app.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT user_id FROM posts WHERE id = ?', (post_id,))
        post = cursor.fetchone()

        if not post:
            flash('投稿が見つかりません', 'error')
            return redirect(url_for('index'))

        if post['user_id'] != session['user_id']:
            flash('他のユーザーの投稿は削除できません', 'error')
            return redirect(url_for('index'))

        cursor.execute('DELETE FROM posts WHERE id = ?', (post_id,))
        conn.commit()

        flash('投稿を削除しました', 'success')
        return redirect(url_for('index'))

    except sqlite3.Error as err:
        flash(f'削除に失敗しました: {err}', 'error')
        return redirect(url_for('index'))

    finally:
        cursor.close()
        conn.close()


@app.route('/comment/<int:comment_id>/delete', methods=['POST'])
def delete_comment(comment_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, post_id FROM comments WHERE id = ?', (comment_id,))
        comment = cursor.fetchone()
        if not comment:
            flash('コメントが見つかりません', 'error')
            return redirect(url_for('index'))
        if comment['user_id'] != session['user_id']:
            flash('他のユーザーのコメントは削除できません', 'error')
            return redirect(url_for('comment', post_id=comment['post_id']))
        cursor.execute('DELETE FROM comments WHERE id = ?', (comment_id,))
        conn.commit()
        flash('コメントを削除しました', 'success')
        return redirect(url_for('comment', post_id=comment['post_id']))
    except Exception as err:
        flash(f'削除に失敗しました: {err}', 'error')
        return redirect(url_for('index'))
    finally:
        conn.close()


@app.route('/user/<username>')
@login_required
def user_profile(username):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, username, profile, icon_path FROM users WHERE username = ?',
            (username,)
        )
        row = cursor.fetchone()
        if not row:
            abort(404)
        profile_user = dict(row)

        page = request.args.get('page', 1, type=int)
        per_page = 10
        offset = (page - 1) * per_page

        cursor.execute(
            'SELECT COUNT(*) AS cnt FROM posts WHERE user_id = ?',
            (profile_user['id'],)
        )
        total = cursor.fetchone()['cnt']
        total_pages = max(1, (total + per_page - 1) // per_page)

        cursor.execute('''
            SELECT
                p.id,
                p.content,
                p.created_at,
                p.user_id,
                u.username,
                u.icon_path,
                (SELECT COUNT(*) FROM likes     WHERE post_id = p.id) AS like_count,
                (SELECT COUNT(*) FROM favorites  WHERE post_id = p.id) AS favorite_count,
                (SELECT COUNT(*) FROM comments   WHERE post_id = p.id) AS comment_count,
                EXISTS(SELECT 1 FROM likes     WHERE post_id = p.id AND user_id = ?) AS is_liked,
                EXISTS(SELECT 1 FROM favorites  WHERE post_id = p.id AND user_id = ?) AS is_favorited
            FROM posts p
            JOIN users u ON p.user_id = u.id
            WHERE p.user_id = ?
            ORDER BY p.created_at DESC
            LIMIT ? OFFSET ?
        ''', (session['user_id'], session['user_id'], profile_user['id'], per_page, offset))
        posts = [dict(row) for row in cursor.fetchall()]

        category_map = {}
        if posts:
            post_ids = [p['id'] for p in posts]
            placeholders = ','.join(['?'] * len(post_ids))
            cursor.execute(f'''
                SELECT pc.post_id, c.name
                FROM post_categories pc
                JOIN categories c ON pc.category_id = c.id
                WHERE pc.post_id IN ({placeholders})
            ''', post_ids)
            for row in cursor.fetchall():
                category_map.setdefault(row['post_id'], []).append(row['name'])
        for p in posts:
            p['categories'] = category_map.get(p['id'], [])

        return render_template(
            'profile.html',
            profile_user=profile_user,
            posts=posts,
            page=page,
            total_pages=total_pages,
            post_count=total,
        )
    except Exception as err:
        flash(f'プロフィールの読み込みに失敗しました: {err}', 'error')
        return redirect(url_for('index'))
    finally:
        cursor.close()
        conn.close()


@app.route('/notifications')
@login_required
def notifications():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        page = request.args.get('page', 1, type=int)
        if page < 1:
            page = 1
        offset = (page - 1) * PER_PAGE

        cursor.execute(
            "SELECT COUNT(*) FROM notifications n JOIN users u ON n.actor_id = u.id JOIN posts p ON n.post_id = p.id WHERE n.user_id = ?",
            (session['user_id'],)
        )
        total = cursor.fetchone()[0]
        total_pages = max(1, -(-total // PER_PAGE))

        cursor.execute('''
            SELECT n.id, n.type, n.is_read, n.created_at,
                   u.username AS actor_name, u.icon_path AS actor_icon,
                   p.id AS post_id, p.content AS post_content
            FROM notifications n
            JOIN users u ON n.actor_id = u.id
            JOIN posts p ON n.post_id = p.id
            WHERE n.user_id = ?
            ORDER BY n.created_at DESC
            LIMIT ? OFFSET ?
        ''', (session['user_id'], PER_PAGE, offset))
        notifs = [dict(row) for row in cursor.fetchall()]

        cursor.execute(
            "DELETE FROM notifications WHERE user_id = ? AND is_read = 1 AND read_at <= datetime('now', '-30 days', 'localtime')",
            (session['user_id'],)
        )
        conn.commit()

        return render_template('notifications.html', notifications=notifs, page=page, total_pages=total_pages)

    except sqlite3.Error as err:
        flash(f'通知の取得に失敗しました: {err}', 'error')
        return redirect(url_for('index'))
    finally:
        cursor.close()
        conn.close()


@app.route('/notifications/<int:notif_id>/read')
@login_required
def notification_read(notif_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT post_id FROM notifications WHERE id = ? AND user_id = ?",
            (notif_id, session['user_id'])
        )
        row = cursor.fetchone()
        if not row:
            abort(404)
        cursor.execute(
            "UPDATE notifications SET is_read = 1, read_at = datetime('now', 'localtime') WHERE id = ? AND user_id = ?",
            (notif_id, session['user_id'])
        )
        conn.commit()
        return redirect(url_for('comment', post_id=row['post_id']))
    except sqlite3.Error as err:
        flash(f'既読処理に失敗しました: {err}', 'error')
        return redirect(url_for('notifications'))
    finally:
        cursor.close()
        conn.close()


@app.route('/admin')
@admin_required
def admin():
    q = request.args.get('q', '').strip()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, username, email, is_admin, created_at FROM users ORDER BY id'
        )
        users = cursor.fetchall()
        if q:
            cursor.execute(
                '''SELECT posts.id, posts.content, posts.created_at, users.username
                   FROM posts
                   JOIN users ON posts.user_id = users.id
                   WHERE posts.content LIKE ? OR users.username LIKE ?
                   ORDER BY posts.id DESC''',
                (f'%{q}%', f'%{q}%')
            )
        else:
            cursor.execute(
                '''SELECT posts.id, posts.content, posts.created_at, users.username
                   FROM posts
                   JOIN users ON posts.user_id = users.id
                   ORDER BY posts.id DESC
                   LIMIT 50'''
            )
        posts = cursor.fetchall()
        return render_template('admin.html', users=users, posts=posts, q=q)
    except sqlite3.Error as err:
        flash(f'データの取得に失敗しました: {err}', 'error')
        return redirect(url_for('index'))
    finally:
        cursor.close()
        conn.close()


@app.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    if user_id == session['user_id']:
        flash('自分自身を削除することはできません', 'error')
        return redirect(url_for('admin'))
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE id = ?', (user_id,))
        if not cursor.fetchone():
            flash('ユーザーが見つかりません', 'error')
            return redirect(url_for('admin'))
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        flash('ユーザーを削除しました', 'success')
        return redirect(url_for('admin'))
    except sqlite3.Error as err:
        flash(f'削除に失敗しました: {err}', 'error')
        return redirect(url_for('admin'))
    finally:
        cursor.close()
        conn.close()


@app.route('/admin/post/<int:post_id>/delete', methods=['POST'])
@admin_required
def admin_delete_post(post_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM posts WHERE id = ?', (post_id,))
        if not cursor.fetchone():
            flash('投稿が見つかりません', 'error')
            return redirect(url_for('admin'))
        cursor.execute('DELETE FROM posts WHERE id = ?', (post_id,))
        conn.commit()
        flash('投稿を削除しました', 'success')
        return redirect(url_for('admin'))
    except sqlite3.Error as err:
        flash(f'削除に失敗しました: {err}', 'error')
        return redirect(url_for('admin'))
    finally:
        cursor.close()
        conn.close()


@app.errorhandler(404)
def not_found(_e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(_e):
    return render_template('500.html'), 500


if __name__ == '__main__':
    app.run(debug=True)
