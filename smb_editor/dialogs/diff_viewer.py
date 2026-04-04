# -*- coding: utf-8 -*-
"""
差分表示ダイアログ
2つのファイルの差分をunified diff形式でカラー表示するダイアログ。
"""

import tkinter as tk
from tkinter import ttk
import difflib


class DiffViewer(tk.Toplevel):
    """差分表示ダイアログ"""

    def __init__(self, parent: tk.Widget, title: str, diff_text: str,
                 width: int = 800, height: int = 600):
        """ダイアログを初期化する"""
        super().__init__(parent)
        self.title(title)

        # ウィンドウサイズを設定
        self.geometry(f"{width}x{height}")
        self.minsize(600, 400)

        # モーダルダイアログとして設定
        self.transient(parent)

        # UIを構築
        self._build_ui(diff_text)

        # ウィンドウを親の中央に配置
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(0, x)}+{max(0, y)}")

        # Escapeで閉じる
        self.bind("<Escape>", lambda e: self.destroy())

    def _build_ui(self, diff_text: str) -> None:
        """UIウィジェットを構築する"""
        # メインフレーム
        main_frame = ttk.Frame(self, padding=5)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 凡例フレーム
        legend_frame = ttk.Frame(main_frame)
        legend_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(legend_frame, text="凡例:").pack(side=tk.LEFT, padx=(0, 10))

        # 追加行の凡例
        add_legend = tk.Label(legend_frame, text=" + 追加行 ", bg="#1B5E20", fg="#C8E6C9",
                              font=("monospace", 9))
        add_legend.pack(side=tk.LEFT, padx=(0, 5))

        # 削除行の凡例
        del_legend = tk.Label(legend_frame, text=" - 削除行 ", bg="#B71C1C", fg="#FFCDD2",
                              font=("monospace", 9))
        del_legend.pack(side=tk.LEFT, padx=(0, 5))

        # ヘッダー行の凡例
        hdr_legend = tk.Label(legend_frame, text=" @@ 位置情報 ", bg="#0D47A1", fg="#BBDEFB",
                              font=("monospace", 9))
        hdr_legend.pack(side=tk.LEFT, padx=(0, 5))

        # テキスト表示エリア
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        # スクロールバー
        v_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar = ttk.Scrollbar(text_frame, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        # テキストウィジェット
        self._text = tk.Text(
            text_frame,
            wrap=tk.NONE,
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set,
            font=("monospace", 10),
        )
        self._text.pack(fill=tk.BOTH, expand=True)
        v_scrollbar.config(command=self._text.yview)
        h_scrollbar.config(command=self._text.xview)

        # カラー表示用のタグを設定
        # 追加行（緑系）
        self._text.tag_configure("add", background="#1B5E20", foreground="#C8E6C9")
        # 削除行（赤系）
        self._text.tag_configure("delete", background="#B71C1C", foreground="#FFCDD2")
        # ヘッダー行（青系）
        self._text.tag_configure("header", background="#0D47A1", foreground="#BBDEFB")
        # ファイル情報行
        self._text.tag_configure("file_info", foreground="#64B5F6",
                                 font=("monospace", 10, "bold"))

        # 差分テキストを色分けして挿入
        if diff_text.strip():
            self._insert_colored_diff(diff_text)
        else:
            self._text.insert(tk.END, "差分はありません（ファイルは同一です）")

        # 読み取り専用に設定
        self._text.config(state=tk.DISABLED)

        # ボタンフレーム
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="閉じる", command=self.destroy).pack(side=tk.RIGHT)

    def _insert_colored_diff(self, diff_text: str) -> None:
        """差分テキストを色分けして挿入する"""
        for line in diff_text.split("\n"):
            if line.startswith("+++") or line.startswith("---"):
                # ファイル情報行
                self._text.insert(tk.END, line + "\n", "file_info")
            elif line.startswith("@@"):
                # 位置情報行
                self._text.insert(tk.END, line + "\n", "header")
            elif line.startswith("+"):
                # 追加行
                self._text.insert(tk.END, line + "\n", "add")
            elif line.startswith("-"):
                # 削除行
                self._text.insert(tk.END, line + "\n", "delete")
            else:
                # 変更なしの行
                self._text.insert(tk.END, line + "\n")


def show_diff(parent: tk.Widget, title: str, diff_text: str, **kwargs) -> None:
    """差分表示ダイアログを表示するヘルパー関数"""
    DiffViewer(parent, title, diff_text, **kwargs)


def generate_diff(old_content: str, new_content: str,
                  old_label: str = "変更前", new_label: str = "変更後") -> str:
    """2つの文字列からunified diff形式の差分テキストを生成する"""
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    diff = difflib.unified_diff(
        old_lines, new_lines,
        fromfile=old_label, tofile=new_label,
        lineterm=""
    )
    return "\n".join(diff)
