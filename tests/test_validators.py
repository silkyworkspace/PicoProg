import sys #  Pythonの実行環境に関する情報や操作ができるモジュール(sys.path を操作するために読み込む)
import os #  OS（ファイルシステムや環境変数など）を操作できるモジュール(ファイルパスを操作するために読み込む)

# app.py があるディレクトリ（1つ上）を Python の検索パスに追加する
# これがないと「from app import ...」が失敗する
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# app.py からテストしたい関数を直接インポートする
from app import _validate_email, _validate_password, _validate_username

import unittest  # Python 標準のテスト用ライブラリ


# ===== メールアドレスのバリデーションテスト =====
# unittest.TestCase を継承することで、このクラスがテストクラスになる
class TestValidateEmail(unittest.TestCase):

    def test_valid_email(self):
        # 正常なメールアドレス → True が返るはず
        self.assertTrue(_validate_email('user@example.com'))

    def test_valid_email_with_dot(self):
        # ドット入りのメールアドレスも正常
        self.assertTrue(_validate_email('user.name@example.co.jp'))

    def test_valid_email_with_plus(self):
        # + 記号入りのメールアドレスも正常
        self.assertTrue(_validate_email('user+tag@example.com'))

    def test_missing_at(self):
        # @ がない → False が返るはず
        self.assertFalse(_validate_email('userexample.com'))

    def test_missing_domain(self):
        # @ の後のドメインがない → False が返るはず
        self.assertFalse(_validate_email('user@'))

    def test_empty_string(self):
        # 空文字 → False が返るはず
        self.assertFalse(_validate_email(''))


# ===== パスワードのバリデーションテスト =====
class TestValidatePassword(unittest.TestCase):

    def test_valid_password(self):
        # 正常なパスワード → (True, None) が返るはず
        # _validate_password は (is_valid: 成否, msg: エラーメッセージ) の2つをセットで返す
        is_valid, msg = _validate_password('Password1')
        self.assertTrue(is_valid)     # 成否が True であること
        self.assertIsNone(msg)        # エラーメッセージが None（なし）であること

    def test_too_short(self):
        # 8文字未満 → (False, エラーメッセージ) が返るはず
        is_valid, msg = _validate_password('Pass1')
        self.assertFalse(is_valid)            # 成否が False であること
        self.assertIn('8文字以上', msg)       # エラーメッセージに「8文字以上」が含まれること

    def test_no_letter(self):
        # 英字が含まれていない → False が返るはず
        is_valid, msg = _validate_password('12345678')
        self.assertFalse(is_valid)
        self.assertIn('英字', msg)            # エラーメッセージに「英字」が含まれること

    def test_no_digit(self):
        # 数字が含まれていない → False が返るはず
        is_valid, msg = _validate_password('Password')
        self.assertFalse(is_valid)
        self.assertIn('数字', msg)            # エラーメッセージに「数字」が含まれること

    def test_exactly_8_chars(self):
        # ちょうど8文字 → 合格するはず（境界値テスト）
        is_valid, msg = _validate_password('Pass1234')
        self.assertTrue(is_valid)
        self.assertIsNone(msg)


# ===== ユーザー名のバリデーションテスト =====
class TestValidateUsername(unittest.TestCase):

    def test_valid_username(self):
        # 正常なユーザー名 → (True, None) が返るはず
        is_valid, msg = _validate_username('picoprog')
        self.assertTrue(is_valid)
        self.assertIsNone(msg)

    def test_min_length(self):
        # 最小文字数（3文字）→ 合格するはず（境界値テスト）
        # エラーメッセージは確認しないので _ で受け取って捨てる
        is_valid, _ = _validate_username('abc')
        self.assertTrue(is_valid)

    def test_max_length(self):
        # 最大文字数（20文字）→ 合格するはず（境界値テスト）
        is_valid, _ = _validate_username('a' * 20)  # 'a' を20個並べた文字列
        self.assertTrue(is_valid)

    def test_too_short(self):
        # 2文字（最小の3文字未満）→ 不合格のはず
        is_valid, msg = _validate_username('ab')
        self.assertFalse(is_valid)
        self.assertIn('3〜20文字', msg)

    def test_too_long(self):
        # 21文字（最大の20文字超）→ 不合格のはず
        is_valid, msg = _validate_username('a' * 21)  # 'a' を21個並べた文字列
        self.assertFalse(is_valid)
        self.assertIn('3〜20文字', msg)


# このファイルを直接 `python test_validators.py` で実行したときだけテストを走らせる
# pytest で実行する場合はこの行は無視される
if __name__ == '__main__':
    unittest.main()
