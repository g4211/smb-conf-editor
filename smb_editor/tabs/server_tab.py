# -*- coding: utf-8 -*-
"""
サーバー設定タブ
smb.confの[global]セクションの設定を管理するタブ。
workgroup、hosts allow、およびその他の設定パラメータを編集する。
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from .. import constants as const
from ..smb_parser import SmbConfig
from ..smb_writer import SmbConfWriter
from .. import system_utils


class ServerTab(ttk.Frame):
    """サーバー設定タブ"""

    def __init__(self, parent: tk.Widget, app):
        """タブを初期化する"""
        super().__init__(parent, padding=10)
        self._app = app
        self._config: SmbConfig = None

        # UIを構築
        self._build_ui()

    def _build_ui(self) -> None:
        """UIウィジェットを構築する"""
        # 説明ラベル
        ttk.Label(
            self,
            text="[global]セクションの設定を編集し、上部の[適用]で保存します",
            font=("", 9), foreground="gray"
        ).pack(anchor=tk.W, pady=(0, 8))

        # メインコンテンツ
        content_frame = ttk.Frame(self)
        content_frame.pack(fill=tk.BOTH, expand=True)

        self._build_workgroup_section(content_frame)
        self._build_hosts_allow_section(content_frame)
        self._build_extra_settings_section(content_frame)

    def _build_workgroup_section(self, parent: tk.Widget) -> None:
        """ワークグループ設定セクションを構築する"""
        wg_frame = ttk.Frame(parent)
        wg_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(wg_frame, text="workgroup:", width=12).pack(side=tk.LEFT)
        self._workgroup_var = tk.StringVar(value="WORKGROUP")
        ttk.Entry(wg_frame, textvariable=self._workgroup_var, width=30).pack(side=tk.LEFT, padx=(5, 0))

    def _build_hosts_allow_section(self, parent: tk.Widget) -> None:
        """アクセス許可（hosts allow）セクションを構築する"""
        hosts_frame = ttk.LabelFrame(parent, text="アクセスを許可するアドレス（hosts allow）", padding=10)
        hosts_frame.pack(fill=tk.X, pady=(0, 10))

        hosts_top = ttk.Frame(hosts_frame)
        hosts_top.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(
            hosts_top,
            text="改行区切りでIPアドレス/ネットワーク/ホスト名を入力\n"
                 "（IPv4, IPv6, ホスト名, EXCEPT構文に対応。空欄の場合はhosts allowを削除）",
            font=("", 9), foreground="gray"
        ).pack(side=tk.LEFT)
        ttk.Button(
            hosts_top, text="自分が所属するネットワークアドレスを自動入力",
            command=self._auto_fill_network
        ).pack(side=tk.RIGHT)

        hosts_text_frame = ttk.Frame(hosts_frame)
        hosts_text_frame.pack(fill=tk.X)
        self._hosts_text = tk.Text(hosts_text_frame, height=5, width=50, font=("monospace", 10))
        hosts_scrollbar = ttk.Scrollbar(hosts_text_frame, orient=tk.VERTICAL, command=self._hosts_text.yview)
        self._hosts_text.configure(yscrollcommand=hosts_scrollbar.set)
        self._hosts_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        hosts_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _build_extra_settings_section(self, parent: tk.Widget) -> None:
        """その他の設定（折りたたみ可能）セクションを構築する"""
        self._extra_expanded = tk.BooleanVar(value=False)
        extra_header = ttk.Frame(parent)
        extra_header.pack(fill=tk.X, pady=(10, 0))

        self._toggle_btn = ttk.Button(
            extra_header, text="▶ その他の設定",
            command=self._toggle_extra, width=20
        )
        self._toggle_btn.pack(side=tk.LEFT)

        self._extra_frame = ttk.LabelFrame(parent, text="その他の設定", padding=10)
        self._extra_vars: dict[str, tk.StringVar] = {}

        for param_info in const.GLOBAL_EXTRA_PARAMS:
            param_frame = ttk.Frame(self._extra_frame)
            param_frame.pack(fill=tk.X, pady=(0, 5))
            ttk.Label(param_frame, text=f"{param_info['label']}:", width=20).pack(side=tk.LEFT)
            var = tk.StringVar(value=param_info["default"])
            ttk.Entry(param_frame, textvariable=var, width=40).pack(side=tk.LEFT, padx=(5, 0))
            self._extra_vars[param_info["key"]] = var

    def _toggle_extra(self) -> None:
        """その他の設定の折りたたみを切り替える"""
        if self._extra_expanded.get():
            self._extra_frame.pack_forget()
            self._toggle_btn.config(text="▶ その他の設定")
            self._extra_expanded.set(False)
        else:
            self._extra_frame.pack(fill=tk.X, pady=(5, 10))
            self._toggle_btn.config(text="▼ その他の設定")
            self._extra_expanded.set(True)

    def _auto_fill_network(self) -> None:
        """自分が所属するネットワークアドレスを自動入力する"""
        networks = system_utils.get_network_addresses()
        if networks:
            current = self._hosts_text.get("1.0", tk.END).strip()
            existing = set(current.split("\n")) if current else set()
            new_entries = [n for n in networks if n not in existing]
            if new_entries:
                if current:
                    self._hosts_text.insert(tk.END, "\n" + "\n".join(new_entries))
                else:
                    self._hosts_text.insert(tk.END, "\n".join(new_entries))
                messagebox.showinfo(
                    "自動入力",
                    f"以下のネットワークアドレスを追加しました:\n{chr(10).join(new_entries)}",
                    parent=self
                )
            else:
                messagebox.showinfo("自動入力", "追加するネットワークアドレスはありません", parent=self)
        else:
            messagebox.showwarning("自動入力", "ネットワークアドレスを取得できませんでした", parent=self)

    def load_data(self, config: SmbConfig) -> None:
        """smb.confのデータを読み込んで表示する"""
        self._config = config
        global_section = config.get_section("global")
        if global_section is None:
            return

        # workgroup
        workgroup = global_section.get_param("workgroup") or "WORKGROUP"
        self._workgroup_var.set(workgroup)

        # hosts allow
        hosts_allow = global_section.get_param("hosts allow") or ""
        self._hosts_text.delete("1.0", tk.END)
        if hosts_allow:
            hosts_list = []
            for part in hosts_allow.replace(",", " ").split():
                part = part.strip()
                if part:
                    hosts_list.append(part)
            self._hosts_text.insert(tk.END, "\n".join(hosts_list))

        # その他の設定
        for param_info in const.GLOBAL_EXTRA_PARAMS:
            key = param_info["key"]
            value = global_section.get_param(key)
            if value is not None and key in self._extra_vars:
                self._extra_vars[key].set(value)

    def collect_changes(self, writer: SmbConfWriter) -> Optional[bool]:
        """
        サーバー設定の変更をWriterに適用する。
        戻り値: True=成功、None=バリデーションエラー
        """
        # hosts allow のバリデーション
        hosts_text = self._hosts_text.get("1.0", tk.END).strip()
        if hosts_text:
            is_valid, errors = system_utils.validate_hosts_allow(hosts_text)
            if not is_valid:
                error_msg = "\n".join(errors)
                messagebox.showerror(
                    "入力エラー",
                    f"アドレスの入力に問題があります:\n\n{error_msg}",
                    parent=self
                )
                return None

        # workgroup を更新
        workgroup = self._workgroup_var.get().strip()
        if workgroup:
            writer.update_param("global", "workgroup", workgroup)

        # hosts allow を更新
        if hosts_text:
            hosts_value = " ".join(hosts_text.split("\n"))
            writer.update_param("global", "hosts allow", hosts_value)
        else:
            writer.remove_param("global", "hosts allow")

        # その他の設定を更新
        for param_info in const.GLOBAL_EXTRA_PARAMS:
            key = param_info["key"]
            if key in self._extra_vars:
                value = self._extra_vars[key].get().strip()
                if value:
                    writer.update_param("global", key, value)

        return True
