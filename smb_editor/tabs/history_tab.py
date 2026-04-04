# -*- coding: utf-8 -*-
"""
バックアップタブ
smb.confのバックアップ管理と復元機能を提供するタブ。
バックアップの一覧表示、内容表示、差分表示、復元、コメント編集を行う。
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from .. import constants as const
from ..backup_manager import BackupManager, BackupEntry
from ..dialogs.content_viewer import show_content
from ..dialogs.diff_viewer import show_diff


class HistoryTab(ttk.Frame):
    """バックアップタブ"""

    def __init__(self, parent: tk.Widget, app):
        """タブを初期化する"""
        super().__init__(parent, padding=10)
        self._app = app

        # UIを構築
        self._build_ui()

    def _build_ui(self) -> None:
        """UIウィジェットを構築する"""
        # === 設定セクション ===
        settings_frame = ttk.LabelFrame(self, text="バックアップ設定", padding=10)
        settings_frame.pack(fill=tk.X, pady=(0, 10))

        # 初期設定ファイル
        row1 = ttk.Frame(settings_frame)
        row1.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(row1, text="初期設定ファイル:", width=18).pack(side=tk.LEFT)
        self._default_conf_var = tk.StringVar(
            value=self._app.config_manager.get("default_smb_conf", const.DEFAULT_SMB_CONF)
        )
        ttk.Entry(row1, textvariable=self._default_conf_var, width=40).pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(row1, text="参照", width=5,
                   command=self._browse_default_conf).pack(side=tk.LEFT)

        # バックアップディレクトリ
        row2 = ttk.Frame(settings_frame)
        row2.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(row2, text="バックアップディレクトリ:", width=18).pack(side=tk.LEFT)
        self._backup_dir_var = tk.StringVar(
            value=self._app.config_manager.get("backup_dir", const.DEFAULT_BACKUP_DIR)
        )
        ttk.Entry(row2, textvariable=self._backup_dir_var, width=40).pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(row2, text="参照", width=5,
                   command=self._browse_backup_dir).pack(side=tk.LEFT)

        # バックアップ最大数
        row3 = ttk.Frame(settings_frame)
        row3.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(row3, text="バックアップ最大数:", width=18).pack(side=tk.LEFT)
        self._max_backups_var = tk.IntVar(
            value=self._app.config_manager.get("max_backups", const.DEFAULT_MAX_BACKUPS)
        )
        ttk.Spinbox(
            row3, from_=1, to=100, textvariable=self._max_backups_var, width=5
        ).pack(side=tk.LEFT, padx=(5, 5))

        ttk.Button(
            row3, text="設定を保存", width=10,
            command=self._save_settings
        ).pack(side=tk.LEFT, padx=(15, 0))

        # === バックアップ一覧セクション ===
        list_frame = ttk.LabelFrame(self, text="バックアップ一覧", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True)

        # 更新ボタン
        list_top = ttk.Frame(list_frame)
        list_top.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(list_top, text="一覧を更新", width=10,
                   command=self._refresh_list).pack(side=tk.LEFT)

        # スクロール可能なバックアップリスト
        list_scroll_frame = ttk.Frame(list_frame)
        list_scroll_frame.pack(fill=tk.BOTH, expand=True)

        self._list_canvas = tk.Canvas(list_scroll_frame, highlightthickness=0)
        list_scrollbar = ttk.Scrollbar(list_scroll_frame, orient=tk.VERTICAL,
                                        command=self._list_canvas.yview)
        self._list_scrollable = ttk.Frame(self._list_canvas)
        self._list_scrollable.bind(
            "<Configure>",
            lambda e: self._list_canvas.configure(scrollregion=self._list_canvas.bbox("all"))
        )
        self._list_canvas_window = self._list_canvas.create_window(
            (0, 0), window=self._list_scrollable, anchor="nw"
        )
        self._list_canvas.configure(yscrollcommand=list_scrollbar.set)
        self._list_canvas.bind("<Configure>", self._on_list_canvas_configure)

        self._list_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _on_list_canvas_configure(self, event) -> None:
        self._list_canvas.itemconfig(self._list_canvas_window, width=event.width)

    def load_data(self) -> None:
        self._refresh_list()

    def _refresh_list(self) -> None:
        """バックアップ一覧を更新する"""
        for widget in self._list_scrollable.winfo_children():
            widget.destroy()

        # 初期設定ファイルのエントリ
        self._add_default_conf_entry()
        ttk.Separator(self._list_scrollable, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

        # バックアップ一覧を取得
        backups = self._app.backup_manager.get_backup_list()
        if not backups:
            ttk.Label(
                self._list_scrollable, text="バックアップがありません",
                foreground="gray"
            ).pack(anchor=tk.W, pady=10)
            return

        for entry in backups:
            self._add_backup_entry(entry)

    def _add_default_conf_entry(self) -> None:
        """初期設定ファイルのエントリを追加する"""
        entry_frame = ttk.Frame(self._list_scrollable)
        entry_frame.pack(fill=tk.X, pady=3)

        ttk.Label(entry_frame, text="📋 初期設定", font=("", 10, "bold")).pack(side=tk.LEFT, padx=(0, 10))

        btn_frame = ttk.Frame(entry_frame)
        btn_frame.pack(side=tk.RIGHT)

        ttk.Button(btn_frame, text="内容表示", width=8,
                   command=self._show_default_content).pack(side=tk.LEFT, padx=(0, 3))
        ttk.Button(btn_frame, text="差分表示", width=8,
                   command=self._show_default_diff).pack(side=tk.LEFT, padx=(0, 3))
        ttk.Button(btn_frame, text="この設定に戻す", width=12,
                   command=self._restore_default).pack(side=tk.LEFT)

    def _add_backup_entry(self, entry: BackupEntry) -> None:
        """バックアップエントリを追加する"""
        entry_frame = ttk.Frame(self._list_scrollable)
        entry_frame.pack(fill=tk.X, pady=3)

        # 上段: 日時、カテゴリー
        top_row = ttk.Frame(entry_frame)
        top_row.pack(fill=tk.X)

        timestamp_display = self._format_timestamp(entry.timestamp)
        category_label = const.CATEGORY_LABELS.get(entry.category, entry.category)
        ttk.Label(
            top_row,
            text=f"📋 {timestamp_display} [{category_label}]",
            font=("", 9)
        ).pack(side=tk.LEFT, padx=(0, 10))

        btn_frame = ttk.Frame(top_row)
        btn_frame.pack(side=tk.RIGHT)

        # 削除対象から除外チェックボックス
        exclude_var = tk.BooleanVar(value=entry.exclude_from_deletion)
        ttk.Checkbutton(
            btn_frame, text="削除対象から除外", variable=exclude_var,
            command=lambda fn=entry.filename, var=exclude_var:
                self._on_exclude_changed(fn, var.get())
        ).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(btn_frame, text="内容表示", width=8,
                   command=lambda fn=entry.filename: self._show_backup_content(fn)
                   ).pack(side=tk.LEFT, padx=(0, 3))
        ttk.Button(btn_frame, text="差分表示", width=8,
                   command=lambda fn=entry.filename: self._show_backup_diff(fn)
                   ).pack(side=tk.LEFT, padx=(0, 3))
        ttk.Button(btn_frame, text="この設定に戻す", width=12,
                   command=lambda fn=entry.filename: self._restore_backup(fn)
                   ).pack(side=tk.LEFT)

        # 下段: コメント
        bottom_row = ttk.Frame(entry_frame)
        bottom_row.pack(fill=tk.X, pady=(2, 0))
        ttk.Label(bottom_row, text="   コメント:", foreground="gray").pack(side=tk.LEFT, padx=(0, 5))
        comment_var = tk.StringVar(value=entry.comment)
        comment_entry = ttk.Entry(bottom_row, textvariable=comment_var, width=50)
        comment_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        comment_entry.bind(
            "<FocusOut>",
            lambda e, fn=entry.filename, var=comment_var:
                self._on_comment_changed(fn, var.get())
        )

        ttk.Separator(self._list_scrollable, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=3)

    def _format_timestamp(self, timestamp: str) -> str:
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(timestamp)
            return dt.strftime("%Y年%m月%d日 %H:%M:%S")
        except (ValueError, TypeError):
            return timestamp

    def _show_default_content(self) -> None:
        default_path = self._default_conf_var.get().strip()
        if not default_path or not os.path.isfile(default_path):
            messagebox.showwarning("エラー", "初期設定ファイルが見つかりません", parent=self)
            return
        try:
            with open(default_path, "r", encoding="utf-8") as f:
                content = f.read()
            show_content(self, f"初期設定 - {default_path}", content)
        except IOError as e:
            messagebox.showerror("エラー", f"ファイルの読み取りに失敗: {e}", parent=self)

    def _show_default_diff(self) -> None:
        default_path = self._default_conf_var.get().strip()
        if not default_path or not os.path.isfile(default_path):
            messagebox.showwarning("エラー", "初期設定ファイルが見つかりません", parent=self)
            return
        try:
            with open(default_path, "r", encoding="utf-8") as f:
                old_lines = f.readlines()
            with open(const.SMB_CONF_PATH, "r", encoding="utf-8") as f:
                new_lines = f.readlines()
            import difflib
            diff = difflib.unified_diff(
                old_lines, new_lines,
                fromfile="初期設定", tofile="現在の設定",
                lineterm=""
            )
            diff_text = "\n".join(diff)
            show_diff(self, "差分表示 - 初期設定 vs 現在の設定", diff_text)
        except IOError as e:
            messagebox.showerror("エラー", f"ファイルの読み取りに失敗: {e}", parent=self)

    def _restore_default(self) -> None:
        result = messagebox.askyesno(
            "確認",
            "初期設定に戻しますか？\n\n現在の設定は自動的にバックアップされます。",
            parent=self
        )
        if not result:
            return

        default_path = self._default_conf_var.get().strip()
        if not default_path or not os.path.isfile(default_path):
            messagebox.showwarning("エラー", "初期設定ファイルが見つかりません", parent=self)
            return

        try:
            with open(default_path, "r", encoding="utf-8") as f:
                content = f.read()
        except IOError as e:
            messagebox.showerror("エラー", f"ファイルの読み取りに失敗: {e}", parent=self)
            return

        apply_result = self._app.apply_manager.apply_changes(
            new_conf_content=content,
            category=const.CATEGORY_RESTORE,
            comment="初期設定に復元"
        )

        if apply_result.success:
            messagebox.showinfo("完了", "初期設定に復元しました", parent=self)
            self._app.reload_data()
        else:
            error_msg = "\n".join(apply_result.errors)
            messagebox.showerror("エラー", f"復元に失敗しました:\n\n{error_msg}", parent=self)

    def _show_backup_content(self, filename: str) -> None:
        content = self._app.backup_manager.read_backup(filename)
        if content:
            show_content(self, f"バックアップ内容 - {filename}", content)
        else:
            messagebox.showerror("エラー", "バックアップファイルの読み取りに失敗しました", parent=self)

    def _show_backup_diff(self, filename: str) -> None:
        diff_text = self._app.backup_manager.get_diff(filename, const.SMB_CONF_PATH)
        show_diff(self, f"差分表示 - {filename} vs 現在の設定", diff_text)

    def _restore_backup(self, filename: str) -> None:
        result = messagebox.askyesno(
            "確認",
            f"バックアップ '{filename}' の設定に戻しますか？\n\n"
            "現在の設定は自動的にバックアップされます。",
            parent=self
        )
        if not result:
            return

        content = self._app.backup_manager.read_backup(filename)
        if not content or content.startswith("エラー"):
            messagebox.showerror("エラー", "バックアップファイルの読み取りに失敗しました", parent=self)
            return

        apply_result = self._app.apply_manager.apply_changes(
            new_conf_content=content,
            category=const.CATEGORY_RESTORE,
            comment=f"バックアップ '{filename}' から復元"
        )

        if apply_result.success:
            messagebox.showinfo("完了", "設定を復元しました", parent=self)
            self._app.reload_data()
        else:
            error_msg = "\n".join(apply_result.errors)
            messagebox.showerror("エラー", f"復元に失敗しました:\n\n{error_msg}", parent=self)

    def _on_exclude_changed(self, filename: str, exclude: bool) -> None:
        self._app.backup_manager.set_exclude(filename, exclude)

    def _on_comment_changed(self, filename: str, comment: str) -> None:
        self._app.backup_manager.update_comment(filename, comment)

    def _browse_default_conf(self) -> None:
        selected = filedialog.askopenfilename(
            parent=self, title="初期設定ファイルの選択",
            filetypes=[("設定ファイル", "*.conf"), ("すべてのファイル", "*.*")]
        )
        if selected:
            self._default_conf_var.set(selected)

    def _browse_backup_dir(self) -> None:
        selected = filedialog.askdirectory(
            parent=self, title="バックアップディレクトリの選択"
        )
        if selected:
            self._backup_dir_var.set(selected)

    def _save_settings(self) -> None:
        self._app.config_manager.set("default_smb_conf", self._default_conf_var.get().strip())
        self._app.config_manager.set("backup_dir", self._backup_dir_var.get().strip())
        self._app.config_manager.set("max_backups", self._max_backups_var.get())
        self._app.config_manager.save()
        self._app.backup_manager.max_backups = self._max_backups_var.get()
        messagebox.showinfo("完了", "設定を保存しました", parent=self)
