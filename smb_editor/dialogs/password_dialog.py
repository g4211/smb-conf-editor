# -*- coding: utf-8 -*-
"""
パスワード入力ダイアログ
Sambaユーザーのパスワードを入力するためのダイアログ
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional


class PasswordDialog(tk.Toplevel):
    """Sambaパスワード入力ダイアログ"""

    def __init__(self, parent: tk.Widget, username: str):
        """ダイアログを初期化する"""
        super().__init__(parent)
        self.title(f"Sambaパスワード設定 - {username}")
        self.username = username
        self.result: Optional[str] = None  # OKの場合にパスワードが設定される

        # モーダルダイアログとして設定
        self.transient(parent)
        self.grab_set()

        # ウィンドウサイズと位置を設定
        self.geometry("400x220")
        self.resizable(False, False)

        # UIを構築
        self._build_ui()

        # ウィンドウを親の中央に配置
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        # Enterキーでの確定を設定
        self.bind("<Return>", lambda e: self._on_ok())
        self.bind("<Escape>", lambda e: self._on_cancel())

        # 最初のフィールドにフォーカス
        self._password_entry.focus_set()

    def _build_ui(self) -> None:
        """UIウィジェットを構築する"""
        # メインフレーム
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 説明ラベル
        desc_label = ttk.Label(
            main_frame,
            text=f"ユーザー '{self.username}' のSambaパスワードを設定してください",
            wraplength=350
        )
        desc_label.pack(anchor=tk.W, pady=(0, 15))

        # パスワード入力フィールド
        pw_frame = ttk.Frame(main_frame)
        pw_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(pw_frame, text="パスワード:", width=14).pack(side=tk.LEFT)
        self._password_entry = ttk.Entry(pw_frame, show="*")
        self._password_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # パスワード確認フィールド
        confirm_frame = ttk.Frame(main_frame)
        confirm_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(confirm_frame, text="パスワード(確認):", width=14).pack(side=tk.LEFT)
        self._confirm_entry = ttk.Entry(confirm_frame, show="*")
        self._confirm_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # エラーメッセージラベル
        self._error_label = ttk.Label(main_frame, text="", foreground="red")
        self._error_label.pack(anchor=tk.W, pady=(0, 8))

        # ボタンフレーム
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(btn_frame, text="キャンセル", command=self._on_cancel).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(btn_frame, text="OK", command=self._on_ok).pack(side=tk.RIGHT)

    def _on_ok(self) -> None:
        """OKボタンがクリックされた時の処理"""
        password = self._password_entry.get()
        confirm = self._confirm_entry.get()

        # バリデーション
        if not password:
            self._error_label.config(text="パスワードを入力してください")
            return
        if password != confirm:
            self._error_label.config(text="パスワードが一致しません")
            return
        if len(password) < 1:
            self._error_label.config(text="パスワードを入力してください")
            return

        # 結果を設定してダイアログを閉じる
        self.result = password
        self.destroy()

    def _on_cancel(self) -> None:
        """キャンセルボタンがクリックされた時の処理"""
        self.result = None
        self.destroy()


def ask_samba_password(parent: tk.Widget, username: str) -> Optional[str]:
    """
    Sambaパスワード入力ダイアログを表示する。
    戻り値: パスワード（キャンセル時はNone）
    """
    dialog = PasswordDialog(parent, username)
    # ダイアログが閉じるまで待機
    parent.wait_window(dialog)
    return dialog.result
