# -*- coding: utf-8 -*-
"""
共有設定タブ
smb.confの共有フォルダ設定を管理するタブ。
各共有フォルダをカード形式で表示し、追加・編集・削除を行う。
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional

from .. import constants as const
from ..smb_parser import SmbConfParser, SmbConfig, SmbSection
from ..smb_writer import SmbConfWriter
from ..system_utils import SystemUser, find_missing_path_part
from ..dialogs.password_dialog import ask_samba_password


class ShareCard(ttk.LabelFrame):
    """1つの共有フォルダ設定を表すカードウィジェット"""

    def __init__(self, parent: tk.Widget, section: Optional[SmbSection],
                 users: list[SystemUser], is_new: bool = False,
                 on_delete: callable = None):
        """
        共有フォルダカードを初期化する。
        section: 既存の共有フォルダセクション（新規の場合はNone）
        users: システムユーザー一覧
        is_new: 新規作成用カードかどうか
        """
        # カードのタイトル
        if is_new:
            card_title = "✦ 新規共有フォルダ"
        else:
            card_title = f"📁 {section.name}" if section else "共有フォルダ"

        super().__init__(parent, text=card_title, padding=10)
        self._section = section
        self._users = users
        self._is_new = is_new
        self._on_delete = on_delete
        self._deleted = False  # 削除フラグ
        self._dir_pending_creation = False  # ディレクトリ作成予定フラグ

        # UIを構築
        self._build_ui()

        # 既存の設定がある場合は値を読み込む
        if section and not is_new:
            self._load_values(section)

    def _build_ui(self) -> None:
        """UIウィジェットを構築する"""
        self._build_basic_section()
        self._build_comment_section()
        self._build_access_section()
        self._on_guest_toggled()
        self._path_entry.bind("<FocusOut>", self._on_path_focus_out)

    def _build_basic_section(self) -> None:
        """共有名、ディレクトリ、読み取り専用の行を構築"""
        row1 = ttk.Frame(self)
        row1.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(row1, text="共有名:").pack(side=tk.LEFT, padx=(0, 5))
        self._name_var = tk.StringVar()
        self._name_entry = ttk.Entry(row1, textvariable=self._name_var, width=18)
        self._name_entry.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(row1, text="ディレクトリ:").pack(side=tk.LEFT, padx=(0, 5))
        self._path_var = tk.StringVar()
        self._path_entry = ttk.Entry(row1, textvariable=self._path_var, width=28)
        self._path_entry.pack(side=tk.LEFT, padx=(0, 3))

        self._pending_label = ttk.Label(row1, text="📁 作成予定", foreground="#4CAF50")

        ttk.Button(row1, text="参照", width=5, command=self._browse_directory).pack(side=tk.LEFT, padx=(0, 8))

        self._readonly_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row1, text="読み取り専用", variable=self._readonly_var).pack(side=tk.LEFT, padx=(0, 8))

        if not self._is_new and self._on_delete:
            ttk.Button(row1, text="削除", width=5, command=self._confirm_delete).pack(side=tk.RIGHT)

    def _build_comment_section(self) -> None:
        """コメント行を構築"""
        comment_frame = ttk.Frame(self)
        comment_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(comment_frame, text="コメント:").pack(side=tk.LEFT, padx=(0, 5))
        self._comment_var = tk.StringVar()
        ttk.Entry(comment_frame, textvariable=self._comment_var, width=60).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _build_access_section(self) -> None:
        """アクセス可否行（ゲスト、ユーザー一覧）を構築"""
        access_frame = ttk.LabelFrame(self, text="アクセス許可", padding=5)
        access_frame.pack(fill=tk.X, pady=(0, 5))

        self._guest_var = tk.BooleanVar(value=self._is_new)
        guest_cb = ttk.Checkbutton(access_frame, text="ゲスト", variable=self._guest_var, command=self._on_guest_toggled)
        guest_cb.pack(side=tk.LEFT, padx=(0, 15))

        self._user_vars: dict[str, tk.BooleanVar] = {}
        self._user_checkbuttons: dict[str, ttk.Checkbutton] = {}
        for user in self._users:
            var = tk.BooleanVar(value=False)
            from ..system_utils import SAMBA_STATUS_LABELS
            status_icon = SAMBA_STATUS_LABELS.get(user.samba_status, "[未]")
            icon = status_icon.split(" ")[0]
            cb = ttk.Checkbutton(access_frame, text=f"{user.username} {icon}", variable=var)
            cb.pack(side=tk.LEFT, padx=(0, 10))
            self._user_vars[user.username] = var
            self._user_checkbuttons[user.username] = cb

        legend_frame = ttk.Frame(self)
        legend_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(
            legend_frame,
            text="[未] 未登録  [有] Samba有効  [無] Samba無効（適用時に自動で有効化されます）",
            font=("", 8), foreground="gray"
        ).pack(anchor=tk.W, padx=5)

    def _load_values(self, section: SmbSection) -> None:
        """既存のセクションから値を読み込む"""
        # 共有名
        self._name_var.set(section.name)

        # ディレクトリパス
        path = section.get_param("path") or ""
        self._path_var.set(path)

        # コメント
        comment = section.get_param("comment") or ""
        self._comment_var.set(comment)

        # 読み取り専用
        read_only = section.get_param("read only") or "no"
        self._readonly_var.set(read_only.lower() in ("yes", "true", "1"))

        # ゲストアクセス
        guest_ok = section.get_param("guest ok") or "no"
        self._guest_var.set(guest_ok.lower() in ("yes", "true", "1"))

        # valid users（ゲストでない場合）
        valid_users = section.get_param("valid users") or ""
        if valid_users and not self._guest_var.get():
            user_list = [u.strip() for u in valid_users.split(",")]
            if len(user_list) == 1 and " " in user_list[0]:
                user_list = user_list[0].split()
            for username in user_list:
                username = username.strip()
                if username in self._user_vars:
                    self._user_vars[username].set(True)

        # ゲストの状態に応じてUIを更新
        self._on_guest_toggled()

    def _browse_directory(self) -> None:
        """ディレクトリ選択ダイアログを開く"""
        initial_dir = self._path_var.get() or "/"
        if not os.path.isdir(initial_dir):
            initial_dir = "/"

        selected = filedialog.askdirectory(
            parent=self,
            title="共有ディレクトリの選択",
            initialdir=initial_dir
        )
        if selected:
            self._path_var.set(selected)
            # 共有名が空なら、ディレクトリ名を自動入力
            if not self._name_var.get().strip():
                dir_name = os.path.basename(selected)
                if dir_name:
                    self._name_var.set(dir_name)
            # 参照で選んだディレクトリは必ず存在するので作成予定を解除
            self._dir_pending_creation = False
            self._pending_label.pack_forget()

    def _on_path_focus_out(self, event) -> None:
        """ディレクトリEntry欄からフォーカスが外れた時の処理"""
        path = self._path_var.get().strip()
        if not path:
            # 空欄の場合は何もしない
            self._dir_pending_creation = False
            self._pending_label.pack_forget()
            return

        if os.path.isdir(path):
            # ディレクトリが存在する場合は作成予定を解除
            self._dir_pending_creation = False
            self._pending_label.pack_forget()
            return

        # ディレクトリが存在しない場合
        existing_prefix, missing_part = find_missing_path_part(path)
        if missing_part:
            # 確認ダイアログを表示
            result = messagebox.askyesno(
                "ディレクトリの作成",
                f"指定されたディレクトリ \"{path}\" のうち、\n"
                f"\"{missing_part}\" が存在しません。\n\n"
                f"適用時に作成しますか？",
                parent=self
            )
            if result:
                # 作成予定としてマーク
                self._dir_pending_creation = True
                # 「作成予定」ラベルを表示
                self._pending_label.pack(side=tk.LEFT, padx=(3, 0))
            else:
                # ユーザーが「いいえ」を選択（誤入力の可能性）
                self._dir_pending_creation = False
                self._pending_label.pack_forget()

    def _on_guest_toggled(self) -> None:
        """ゲストチェックボックスの状態が変わった時の処理"""
        is_guest = self._guest_var.get()
        for username, cb in self._user_checkbuttons.items():
            if is_guest:
                cb.config(state=tk.DISABLED)
            else:
                cb.config(state=tk.NORMAL)

    def _confirm_delete(self) -> None:
        """削除確認ダイアログを表示する"""
        name = self._name_var.get() or "この共有フォルダ"
        result = messagebox.askyesno(
            "削除確認",
            f"共有フォルダ '{name}' をsmb.confから削除しますか？\n\n"
            "※ディレクトリ自体は削除されません",
            parent=self
        )
        if result and self._on_delete:
            self._deleted = True
            self._on_delete(self)

    @property
    def is_empty(self) -> bool:
        """カードが完全に空（未入力）かどうかを返す"""
        return not self._name_var.get().strip() and not self._path_var.get().strip()

    def get_config(self) -> Optional[dict]:
        """
        カードの入力内容から設定辞書を取得する。
        バリデーションエラー時はNoneを返す。
        """
        name = self._name_var.get().strip()
        path = self._path_var.get().strip()
        comment = self._comment_var.get().strip()

        # バリデーション
        if not name:
            messagebox.showwarning("入力エラー", "共有名を入力してください", parent=self)
            return None
        if not path:
            messagebox.showwarning("入力エラー", "ディレクトリを指定してください", parent=self)
            return None

        # 設定辞書を構築
        config = {
            "name": name,
            "path": path,
            "comment": comment,
            "is_new": self._is_new,
            "is_deleted": self._deleted,
            "dir_pending_creation": self._dir_pending_creation,
            "params": {},
            "samba_users_to_add": [],
        }

        # パラメータを設定
        config["params"]["path"] = path
        if comment:
            config["params"]["comment"] = comment
        config["params"]["browseable"] = "yes"
        config["params"]["read only"] = "yes" if self._readonly_var.get() else "no"

        if self._guest_var.get():
            # ゲストアクセスの場合
            config["params"]["guest ok"] = "yes"
            config["params"]["force user"] = "nobody"
            config["params"]["force group"] = "nogroup"
            config["params"]["create mask"] = "0777"
            config["params"]["directory mask"] = "0777"
        else:
            # ユーザー指定アクセスの場合
            config["params"]["guest ok"] = "no"
            selected_users = []
            config["enable_users"] = []  # 無効→有効にするユーザー
            for username, var in self._user_vars.items():
                if var.get():
                    selected_users.append(username)
                    user_obj = next(
                        (u for u in self._users if u.username == username), None
                    )
                    if user_obj:
                        from ..system_utils import (
                            SAMBA_STATUS_UNREGISTERED, SAMBA_STATUS_DISABLED
                        )
                        if user_obj.samba_status == SAMBA_STATUS_UNREGISTERED:
                            # Sambaユーザー未登録 → 登録が必要
                            config["samba_users_to_add"].append(username)
                        elif user_obj.samba_status == SAMBA_STATUS_DISABLED:
                            # Sambaユーザー無効 → 有効化が必要
                            config["enable_users"].append(username)

            if selected_users:
                config["params"]["valid users"] = " ".join(selected_users)
            else:
                messagebox.showwarning(
                    "入力エラー",
                    "ゲストアクセスが無効の場合、\n少なくとも1人のユーザーを選択してください",
                    parent=self
                )
                return None

        return config

    @property
    def is_new(self) -> bool:
        return self._is_new

    @property
    def is_deleted(self) -> bool:
        return self._deleted

    @property
    def section_name(self) -> str:
        if self._section:
            return self._section.name
        return ""


class SharesTab(ttk.Frame):
    """共有設定タブ"""

    def __init__(self, parent: tk.Widget, app):
        """タブを初期化する"""
        super().__init__(parent, padding=10)
        self._app = app
        self._cards: list[ShareCard] = []

        # UIを構築
        self._build_ui()

    def _build_ui(self) -> None:
        """UIウィジェットを構築する"""
        # 説明ラベル
        ttk.Label(
            self,
            text="共有フォルダの設定を編集し、上部の[適用]で保存します",
            font=("", 9), foreground="gray"
        ).pack(anchor=tk.W, pady=(0, 8))

        # スクロール可能なフレーム
        self._canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self._canvas.yview)
        self._scrollable_frame = ttk.Frame(self._canvas)

        self._scrollable_frame.bind(
            "<Configure>",
            lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        )
        self._canvas_window = self._canvas.create_window(
            (0, 0), window=self._scrollable_frame, anchor="nw"
        )
        self._canvas.configure(yscrollcommand=scrollbar.set)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

        # マウスホイールスクロール
        self._canvas.bind_all("<Button-4>",
                              lambda e: self._canvas.yview_scroll(-1, "units"))
        self._canvas.bind_all("<Button-5>",
                              lambda e: self._canvas.yview_scroll(1, "units"))

        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _on_canvas_configure(self, event) -> None:
        self._canvas.itemconfig(self._canvas_window, width=event.width)

    def load_data(self, config: SmbConfig, users: list[SystemUser]) -> None:
        """smb.confのデータを読み込んでカードを表示する"""
        self._users = users
        self._config = config

        # 既存のカードをクリア
        for card in self._cards:
            card.destroy()
        self._cards.clear()

        # 共有フォルダセクションを取得（システムセクション除外）
        share_sections = SmbConfParser.get_share_sections(config)

        # 既存の共有フォルダカードを作成
        for section in share_sections:
            card = ShareCard(
                self._scrollable_frame,
                section=section,
                users=users,
                is_new=False,
                on_delete=self._on_card_delete
            )
            card.pack(fill=tk.X, pady=(0, 10), padx=5)
            self._cards.append(card)

        # 新規共有フォルダカードを追加
        new_card = ShareCard(
            self._scrollable_frame,
            section=None,
            users=users,
            is_new=True
        )
        new_card.pack(fill=tk.X, pady=(0, 10), padx=5)
        self._cards.append(new_card)

    def _on_card_delete(self, card: ShareCard) -> None:
        card.pack_forget()

    def collect_changes(self, writer: SmbConfWriter) -> Optional[dict]:
        """
        全カードの変更を収集してWriterに適用する。
        戻り値: {"samba_users": [...], "new_dirs": [...], "comment_parts": [...]}
                バリデーションエラー時はNone
        """
        samba_users_to_add = []
        new_share_dirs = []
        comment_parts = []
        enable_users = []  # 無効→有効にするユーザー

        for card in self._cards:
            if card.is_deleted:
                if card.section_name:
                    writer.remove_section(card.section_name)
                continue

            # 新規カードが完全に空ならスキップ
            if card.is_new and card.is_empty:
                continue

            card_config = card.get_config()
            if card_config is None:
                return None  # バリデーションエラー（新規・既存共通）

            name = card_config["name"]
            params = card_config["params"]
            comment = card_config.get("comment", "")

            if card.is_new:
                writer.add_section(name, params)
                if card_config.get("dir_pending_creation", False):
                    new_share_dirs.append(params["path"])
            else:
                # 既存セクションのディレクトリが変更され、作成予定の場合
                if card_config.get("dir_pending_creation", False):
                    new_share_dirs.append(params["path"])

                if card.section_name and card.section_name != name:
                    writer.remove_section(card.section_name)
                    writer.add_section(name, params)
                else:
                    writer.set_section_params(name, params)
                    if "comment" not in params:
                        writer.remove_param(name, "comment")

            # Sambaユーザー登録が必要なユーザー
            for username in card_config.get("samba_users_to_add", []):
                password = ask_samba_password(self, username)
                if password is None:
                    messagebox.showinfo("中断", "操作がキャンセルされました", parent=self)
                    return None
                samba_users_to_add.append({
                    "username": username,
                    "password": password
                })

            # 無効→有効にするユーザー（重複排除）
            for username in card_config.get("enable_users", []):
                if username not in enable_users:
                    enable_users.append(username)

            # バックアップコメント用パーツ
            if comment:
                comment_parts.append(f"[{name}] {comment}")

        return {
            "samba_users": samba_users_to_add,
            "new_dirs": new_share_dirs,
            "enable_users": enable_users,
            "comment_parts": comment_parts,
        }
