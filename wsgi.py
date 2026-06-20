import sys
import os

# プロジェクトのパスを追加（PythonAnywhereのユーザー名に合わせて変更する）
# 例: /home/yourusername/PicoProg
path = os.path.dirname(os.path.abspath(__file__))
if path not in sys.path:
    sys.path.insert(0, path)

from app import app as application
