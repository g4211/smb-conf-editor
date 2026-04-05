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
            # ファイルが存在しない場合はデフォルト設定を使用
            return self._defaults.copy()

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

    @property
    def config_path(self) -> str:
        """設定ファイルのパスを返す"""
        return self._config_path
