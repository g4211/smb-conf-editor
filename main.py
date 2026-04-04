#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Samba設定エディター (smb.conf Editor)
Ubuntu向けのSamba設定ファイルをGUIで編集するアプリケーション

使い方:
    python3 main.py
"""

import sys
import os

# アプリケーションのルートディレクトリをPythonパスに追加
app_dir = os.path.dirname(os.path.abspath(__file__))
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

from smb_editor.app import SmbConfEditorApp


def main():
    """アプリケーションのエントリーポイント"""
    # アプリケーションを作成して実行
    app = SmbConfEditorApp()
    app.run()


if __name__ == "__main__":
    main()
