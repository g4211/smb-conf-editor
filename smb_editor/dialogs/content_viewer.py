# -*- coding: utf-8 -*-
"""
内容表示ダイアログ
テキストファイルの内容を読み取り専用で表示するダイアログ。
テキスト検索機能付き。
"""

import tkinter as tk
from tkinter import ttk


class ContentViewer(tk.Toplevel):
    """テキスト内容表示ダイアログ"""

    def __init__(self, parent: tk.Widget, title: str, content: str,
                 width: int = 750, height: int = 550):
        """ダイアログを初期化する"""
        super().__init__(parent)
        self.title(title)

        # ウィンドウサイズを設定
        self.geometry(f"{width}x{height}")
        self.minsize(500, 400)

        # モーダルダイアログとして設定
        self.transient(parent)

        # UIを構築
        self._build_ui(content)

        # ウィンドウを親の中央に配置
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(0, x)}+{max(0, y)}")

        # Ctrl+Fで検索欄にフォーカス
        self.bind("<Control-f>", lambda e: self._show_search())
        self.bind("<Escape>", lambda e: self.destroy())

    def _build_ui(self, content: str) -> None:
        """UIウィジェットを構築する"""
        # メインフレーム
        main_frame = ttk.Frame(self, padding=5)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 検索フレーム（初期状態は非表示）
        self._search_frame = ttk.Frame(main_frame)
        self._search_var = tk.StringVar()
        ttk.Label(self._search_frame, text="検索:").pack(side=tk.LEFT, padx=(0, 5))
        self._search_entry = ttk.Entry(
            self._search_frame, textvariable=self._search_var, width=30
        )
        self._search_entry.pack(side=tk.LEFT, padx=(0, 5))
        # 検索入力時にリアルタイム検索
        self._search_var.trace_add("write", lambda *args: self._do_search())
        ttk.Button(
            self._search_frame, text="次へ", width=6,
            command=lambda: self._find_next()
        ).pack(side=tk.LEFT, padx=(0, 3))
        ttk.Button(
            self._search_frame, text="閉じる", width=6,
            command=self._hide_search
        ).pack(side=tk.LEFT)
        self._search_count_label = ttk.Label(self._search_frame, text="")
        self._search_count_label.pack(side=tk.LEFT, padx=(10, 0))

        # テキスト表示エリア（スクロールバー付き）
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 5))

        # 縦スクロールバー
        v_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 横スクロールバー
        h_scrollbar = ttk.Scrollbar(text_frame, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        # テキストウィジェット
        self._text = tk.Text(
            text_frame,
            wrap=tk.NONE,
            state=tk.NORMAL,
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set,
            font=("monospace", 10),
        )
        self._text.pack(fill=tk.BOTH, expand=True)
        v_scrollbar.config(command=self._text.yview)
        h_scrollbar.config(command=self._text.xview)

        # 内容を挿入
        self._text.insert(tk.END, content)
        # 読み取り専用に設定
        self._text.config(state=tk.DISABLED)

        # 検索ハイライト用のタグを設定
        self._text.tag_configure("search_highlight", background="#FFEB3B", foreground="#000000")
        self._text.tag_configure("search_current", background="#FF9800", foreground="#000000")

        # ボタンフレーム
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(
            btn_frame, text="検索 (Ctrl+F)", command=self._show_search
        ).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(
            btn_frame, text="閉じる", command=self.destroy
        ).pack(side=tk.RIGHT)

        # 検索マッチ位置のリスト
        self._search_matches = []
        self._current_match_index = -1

    def _show_search(self) -> None:
        """検索バーを表示する"""
        self._search_frame.pack(fill=tk.X, pady=(0, 5), before=self._search_frame.master.winfo_children()[1])
        self._search_entry.focus_set()
        self._search_entry.select_range(0, tk.END)

    def _hide_search(self) -> None:
        """検索バーを非表示にする"""
        self._search_frame.pack_forget()
        # ハイライトを解除
        self._text.tag_remove("search_highlight", "1.0", tk.END)
        self._text.tag_remove("search_current", "1.0", tk.END)
        self._search_count_label.config(text="")

    def _do_search(self) -> None:
        """テキスト内を検索してハイライトする"""
        # 既存のハイライトを解除
        self._text.tag_remove("search_highlight", "1.0", tk.END)
        self._text.tag_remove("search_current", "1.0", tk.END)
        self._search_matches = []
        self._current_match_index = -1

        query = self._search_var.get()
        if not query:
            self._search_count_label.config(text="")
            return

        # 検索を実行
        start_pos = "1.0"
        while True:
            # テキスト内で検索
            pos = self._text.search(query, start_pos, stopindex=tk.END, nocase=True)
            if not pos:
                break
            # マッチ位置を記録
            end_pos = f"{pos}+{len(query)}c"
            self._search_matches.append((pos, end_pos))
            # ハイライトを設定
            self._text.tag_add("search_highlight", pos, end_pos)
            # 次の検索開始位置を更新
            start_pos = end_pos

        # 検索結果数を表示
        count = len(self._search_matches)
        if count > 0:
            self._search_count_label.config(text=f"{count}件の一致")
            # 最初のマッチにジャンプ
            self._current_match_index = 0
            self._highlight_current_match()
        else:
            self._search_count_label.config(text="一致なし")

    def _find_next(self) -> None:
        """次のマッチ位置にジャンプする"""
        if not self._search_matches:
            return
        # 次のインデックスに移動（末尾に達したら先頭に戻る）
        self._current_match_index = (self._current_match_index + 1) % len(self._search_matches)
        self._highlight_current_match()

    def _highlight_current_match(self) -> None:
        """現在のマッチ位置をハイライトしてスクロールする"""
        if self._current_match_index < 0 or not self._search_matches:
            return
        # 現在のマッチのハイライトを解除
        self._text.tag_remove("search_current", "1.0", tk.END)
        # 現在のマッチをハイライト
        pos, end_pos = self._search_matches[self._current_match_index]
        self._text.tag_add("search_current", pos, end_pos)
        # マッチ位置にスクロール
        self._text.see(pos)
        # カウント表示を更新
        total = len(self._search_matches)
        current = self._current_match_index + 1
        self._search_count_label.config(text=f"{current}/{total}件")


def show_content(parent: tk.Widget, title: str, content: str, **kwargs) -> None:
    """内容表示ダイアログを表示するヘルパー関数"""
    ContentViewer(parent, title, content, **kwargs)
