# -*- coding: utf-8 -*-
"""
設定管理モジュール
アプリケーションの設定ファイル（config.json）の読み書きを管理する
"""

import json
import os
from typing import Any

from . import constants as const


class ConfigManager:
    """アプリケーション設定の管理クラス"""

    def __init__(self):
        """設定マネージャーを初期化する"""
        # 設定ファイルのパスを構築
        self._config_path = os.path.join(const.APP_CONFIG_DIR, const.CONFIG_FILENAME)
        # デフォルト設定を定義
        self._defaults = {
            "editor": const.DEFAULT_EDITOR,                  # 直接編集で使用するエディター
            "backup_dir": const.DEFAULT_BACKUP_DIR,          # バックアップディレクトリ
            "max_backups": const.DEFAULT_MAX_BACKUPS,         # バックアップ最大数
            "default_smb_conf": const.DEFAULT_SMB_CONF,      # 初期設定ファイルパス
            "log_dir": const.DEFAULT_LOG_DIR,                # ログファイルディレクトリ
            "theme": "auto",                                 # sv_ttkテーマ（未設定時はauto）
        }
        # 設定を読み込む
        self._config = self._load()

    def _load(self) -> dict:
        """設定ファイルを読み込む。存在しない場合はデフォルト設定を返す"""
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    # ファイルから設定を読み込み
                    loaded = json.load(f)
                # デフォルト設定をベースにして、読み込んだ設定で上書き
                config = self._defaults.copy()
                config.update(loaded)
                return config
            except (json.JSONDecodeError, IOError) as e:
                # 読み込みエラー時はデフォルト設定を使用
                print(f"警告: 設定ファイルの読み込みに失敗しました: {e}")
                return self._defaults.copy()
        else:
            # ファイルが存在しない場合（初回起動）はデフォルト設定を使用
            config = self._defaults.copy()
            # インストール済みのエディターを自動検出してデフォルトに設定
            config["editor"] = self._detect_default_editor()
            return config

    def _detect_default_editor(self) -> str:
        """デフォルトエディターの候補から最初にインストールされているものを返す"""
        import shutil
        for candidate in const.DEFAULT_EDITOR_CANDIDATES:
            # shutil.whichでコマンドの存在を確認
            if shutil.which(candidate):
                print(f"デフォルトエディターを自動検出: {candidate}")
                return candidate
        # どれも見つからない場合はフォールバック
        return const.DEFAULT_EDITOR

    def save(self) -> None:
        """現在の設定をファイルに保存する"""
        try:
            # 設定ファイルのディレクトリが存在しない場合は作成
            os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
            with open(self._config_path, "w", encoding="utf-8") as f:
                # JSON形式で書き出し（日本語を含むのでensure_ascii=False）
                json.dump(self._config, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"エラー: 設定ファイルの保存に失敗しました: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """設定値を取得する"""
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """設定値を更新する"""
        self._config[key] = value

    def get_backup_dir(self) -> str:
        """バックアップディレクトリの絶対パスを取得する"""
        backup_dir = self.get("backup_dir", const.DEFAULT_BACKUP_DIR)
        # 相対パスの場合は設定ディレクトリからの相対パスとして解決（システムの規約に合わせるため）
        if not os.path.isabs(backup_dir):
            backup_dir = os.path.join(const.APP_CONFIG_DIR, backup_dir)
        return os.path.abspath(backup_dir)

    def get_all(self) -> dict:
        """全設定を辞書として取得する"""
        return self._config.copy()

    def get_custom_editors(self) -> list[dict]:
        """ユーザーが追加したカスタムエディターのリストを取得する"""
        return self.get("custom_editors", [])

    def set_custom_editors(self, editors: list[dict]) -> None:
        """カスタムエディターのリストを保存する"""
        self.set("custom_editors", editors)

    def get_available_editors(self) -> list[dict]:
        """
        利用可能なエディターの一覧を返す。
        デフォルトエディター + カスタムエディターのうち、
        実行可能なもののみを返す。
        戻り値: [{"name": str, "type": str, "command": str}, ...]
        """
        import shutil
        available = []

        # デフォルトエディターからインストール済みのものを追加
        for name, editor_type in const.DEFAULT_EDITORS.items():
            if shutil.which(name):
                available.append({
                    "name": name,
                    "type": editor_type,
                    "command": "",  # システムインストール済み
                })

        # カスタムエディターから利用可能なものを追加
        for editor in self.get_custom_editors():
            name = editor.get("name", "").strip()
            command = editor.get("command", "").strip()
            editor_type = editor.get("type", const.EDITOR_TYPE_GRAPHICAL)
            if not name:
                continue
            # コマンドが空ならシステムインストール確認
            if not command:
                if shutil.which(name):
                    available.append({"name": name, "type": editor_type, "command": ""})
            else:
                # コマンドの実行ファイル部分が存在するか確認
                exec_path = command.split()[0] if command else ""
                if os.path.isfile(exec_path) or shutil.which(exec_path):
                    available.append({"name": name, "type": editor_type, "command": command})

        return available

    def get_editor_info(self, editor_name: str) -> dict | None:
        """指定エディターの情報を取得する（名前で検索）"""
        for editor in self.get_available_editors():
            if editor["name"] == editor_name:
                return editor
        return None

    def detect_terminal_emulator(self) -> dict | None:
        """利用可能なターミナルエミュレータを検出する"""
        import shutil
        for terminal in const.TERMINAL_CANDIDATES:
            if shutil.which(terminal["cmd"]):
                return terminal
        return None

    def build_terminal_command(self, terminal: dict, editor_cmd: str, filepath: str) -> list[str]:
        """ターミナルエミュレータ用のコマンドリストを構築する"""
        base = [terminal["cmd"]] + terminal["args"]
        if terminal.get("join", False):
            # コマンドを1つの文字列として結合（xfce4-terminal等）
            base.append(f"{editor_cmd} {filepath}")
        else:
            # コマンドとファイルを個別の引数として追加（gnome-terminal等）
            base.extend([editor_cmd, filepath])
        return base

    @property
    def config_path(self) -> str:
        """設定ファイルのパスを返す"""
        return self._config_path
