# -*- coding: utf-8 -*-
"""
ログビューアーダイアログ
Sambaのログファイルを表示するダイアログ。
末尾N行表示、全文表示、テキスト検索、自動更新機能を提供する。
"""

import os
import tkinter as tk
from tkinter import ttk

from .. import system_utils


class LogViewer(tk.Toplevel):
    """ログビューアーダイアログ"""

    # デフォルトの表示行数
    DEFAULT_TAIL_LINES = 100

    def __init__(self, parent: tk.Widget, filepath: str, title: str = None,
                 width: int = 800, height: int = 600):
        """ダイアログを初期化する"""
        super().__init__(parent)
        self._filepath = filepath
        self._filename = os.path.basename(filepath)
        self._auto_refresh = False       # 自動更新フラグ
        self._refresh_job = None         # after() のジョブID
        self._show_all = False           # 全文表示フラグ

        # タイトルを設定
        if title is None:
            title = f"ログビューアー - {self._filename}"
        self.title(title)

        # ウィンドウサイズを設定
        self.geometry(f"{width}x{height}")
        self.minsize(600, 400)

        # モーダルダイアログとして設定
        self.transient(parent)

        # UIを構築
        self._build_ui()

        # 初期表示（末尾N行）
        self._load_content()

        # ウィンドウを親の中央に配置
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(0, x)}+{max(0, y)}")

        # キーバインド
        self.bind("<Control-f>", lambda e: self._show_search())
        self.bind("<Escape>", lambda e: self.destroy())

        # ウィンドウ閉じる時に自動更新を停止
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        """UIウィジェットを構築する"""
        # メインフレーム
        main_frame = ttk.Frame(self, padding=5)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ツールバー
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 5))

        # ファイル名の表示
        ttk.Label(toolbar, text=f"ファイル: {self._filepath}",
                  font=("", 9)).pack(side=tk.LEFT)

        # 自動更新トグルボタン
        self._auto_refresh_var = tk.BooleanVar(value=False)
        self._auto_refresh_btn = ttk.Checkbutton(
            toolbar, text="自動更新", variable=self._auto_refresh_var,
            command=self._toggle_auto_refresh
        )
        self._auto_refresh_btn.pack(side=tk.RIGHT, padx=(5, 0))

        # 更新ボタン
        ttk.Button(toolbar, text="更新", width=8,
                   command=self._load_content).pack(side=tk.RIGHT, padx=(5, 0))

        # 全文表示/末尾表示切り替えボタン
        self._toggle_btn = ttk.Button(
            toolbar, text="全文表示", width=10,
            command=self._toggle_show_all
        )
        self._toggle_btn.pack(side=tk.RIGHT, padx=(5, 0))

        # 検索フレーム
        self._search_frame = ttk.Frame(main_frame)
        self._search_var = tk.StringVar()
        ttk.Label(self._search_frame, text="検索:").pack(side=tk.LEFT, padx=(0, 5))
        self._search_entry = ttk.Entry(
            self._search_frame, textvariable=self._search_var, width=30
        )
        self._search_entry.pack(side=tk.LEFT, padx=(0, 5))
        self._search_var.trace_add("write", lambda *args: self._do_search())
        ttk.Button(
            self._search_frame, text="次へ", width=6,
            command=self._find_next
        ).pack(side=tk.LEFT, padx=(0, 3))
        ttk.Button(
            self._search_frame, text="閉じる", width=6,
            command=self._hide_search
        ).pack(side=tk.LEFT)
        self._search_count_label = ttk.Label(self._search_frame, text="")
        self._search_count_label.pack(side=tk.LEFT, padx=(10, 0))

        # テキスト表示エリア
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        v_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar = ttk.Scrollbar(text_frame, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        self._text = tk.Text(
            text_frame,
            wrap=tk.NONE,
            state=tk.DISABLED,
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set,
            font=("monospace", 10),
        )
        self._text.pack(fill=tk.BOTH, expand=True)
        v_scrollbar.config(command=self._text.yview)
        h_scrollbar.config(command=self._text.xview)

        # 検索ハイライト用タグ
        self._text.tag_configure("search_highlight", background="#FFEB3B", foreground="#000000")
        self._text.tag_configure("search_current", background="#FF9800", foreground="#000000")

        # ステータスバー
        self._status_label = ttk.Label(main_frame, text="", font=("", 9))
        self._status_label.pack(fill=tk.X)

        # ボタンフレーム
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(btn_frame, text="検索 (Ctrl+F)",
                   command=self._show_search).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="閉じる",
                   command=self._on_close).pack(side=tk.RIGHT)

        # 検索マッチ位置
        self._search_matches = []
        self._current_match_index = -1

    def _load_content(self) -> None:
        """ログファイルの内容を読み込んで表示する"""
        tail_lines = 0 if self._show_all else self.DEFAULT_TAIL_LINES
        content = system_utils.read_log_file(self._filepath, tail_lines=tail_lines)

        if content is None:
            content = "ファイルを読み込めませんでした"

        # テキストを更新
        self._text.config(state=tk.NORMAL)
        self._text.delete("1.0", tk.END)
        self._text.insert(tk.END, content)
        self._text.config(state=tk.DISABLED)

        # 末尾にスクロール
        self._text.see(tk.END)

        # ステータス更新
        if self._show_all:
            self._status_label.config(text=f"全文表示中")
        else:
            self._status_label.config(text=f"末尾 {self.DEFAULT_TAIL_LINES} 行を表示中")

    def _toggle_show_all(self) -> None:
        """全文表示/末尾表示を切り替える"""
        self._show_all = not self._show_all
        if self._show_all:
            self._toggle_btn.config(text="末尾のみ")
        else:
            self._toggle_btn.config(text="全文表示")
        self._load_content()

    def _toggle_auto_refresh(self) -> None:
        """自動更新のオン/オフを切り替える"""
        self._auto_refresh = self._auto_refresh_var.get()
        if self._auto_refresh:
            self._schedule_refresh()
        elif self._refresh_job is not None:
            self.after_cancel(self._refresh_job)
            self._refresh_job = None

    def _schedule_refresh(self) -> None:
        """2秒ごとに内容を更新するスケジュールを設定する"""
        if self._auto_refresh:
            self._load_content()
            self._refresh_job = self.after(2000, self._schedule_refresh)

    def _show_search(self) -> None:
        """検索バーを表示する"""
        self._search_frame.pack(fill=tk.X, pady=(0, 5),
                                after=self._search_frame.master.winfo_children()[1])
        self._search_entry.focus_set()

    def _hide_search(self) -> None:
        """検索バーを非表示にする"""
        self._search_frame.pack_forget()
        self._text.tag_remove("search_highlight", "1.0", tk.END)
        self._text.tag_remove("search_current", "1.0", tk.END)

    def _do_search(self) -> None:
        """テキスト内を検索する"""
        self._text.tag_remove("search_highlight", "1.0", tk.END)
        self._text.tag_remove("search_current", "1.0", tk.END)
        self._search_matches = []
        self._current_match_index = -1

        query = self._search_var.get()
        if not query:
            self._search_count_label.config(text="")
            return

        start_pos = "1.0"
        while True:
            pos = self._text.search(query, start_pos, stopindex=tk.END, nocase=True)
            if not pos:
                break
            end_pos = f"{pos}+{len(query)}c"
            self._search_matches.append((pos, end_pos))
            self._text.tag_add("search_highlight", pos, end_pos)
            start_pos = end_pos

        count = len(self._search_matches)
        if count > 0:
            self._search_count_label.config(text=f"{count}件の一致")
            self._current_match_index = 0
            self._highlight_current()
        else:
            self._search_count_label.config(text="一致なし")

    def _find_next(self) -> None:
        """次のマッチにジャンプする"""
        if not self._search_matches:
            return
        self._current_match_index = (self._current_match_index + 1) % len(self._search_matches)
        self._highlight_current()

    def _highlight_current(self) -> None:
        """現在のマッチをハイライトする"""
        if self._current_match_index < 0 or not self._search_matches:
            return
        self._text.tag_remove("search_current", "1.0", tk.END)
        pos, end_pos = self._search_matches[self._current_match_index]
        self._text.tag_add("search_current", pos, end_pos)
        self._text.see(pos)
        total = len(self._search_matches)
        current = self._current_match_index + 1
        self._search_count_label.config(text=f"{current}/{total}件")

    def _on_close(self) -> None:
        """ウィンドウを閉じる時の処理"""
        # 自動更新を停止
        if self._refresh_job is not None:
            self.after_cancel(self._refresh_job)
        self.destroy()


def show_log(parent: tk.Widget, filepath: str, **kwargs) -> None:
    """ログビューアーを表示するヘルパー関数"""
    LogViewer(parent, filepath, **kwargs)
