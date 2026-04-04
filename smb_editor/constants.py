# -*- coding: utf-8 -*-
"""
定数定義モジュール
アプリケーション全体で使用する定数を定義する
"""

import os

# === アプリケーション情報 ===
APP_NAME = "Samba設定エディター"
APP_VERSION = "1.1.0"

# === ファイルパス ===
# Sambaメイン設定ファイルのパス
SMB_CONF_PATH = "/etc/samba/smb.conf"
# Sambaデフォルト設定ファイルのパス（初期状態に戻す用）
DEFAULT_SMB_CONF = "/usr/share/samba/smb.conf"
# デフォルトのログディレクトリ
DEFAULT_LOG_DIR = "/var/log/samba"

# === アプリケーション設定のデフォルト値 ===
# 直接編集で使用するデフォルトのエディター
DEFAULT_EDITOR = "gedit"
# バックアップディレクトリのデフォルトパス（アプリディレクトリからの相対パス）
DEFAULT_BACKUP_DIR = "./backups"
# バックアップファイルの最大保持数
DEFAULT_MAX_BACKUPS = 5

# === ヘルパースクリプト ===
# ヘルパースクリプトのパス（アプリディレクトリからの相対パス）
HELPER_SCRIPT_NAME = "smb-helper.sh"
# ヘルパースクリプトのディレクトリ名
HELPERS_DIR = "helpers"

# === smb.conf 関連定数 ===
# 共有フォルダ一覧に表示しないシステムセクション
SYSTEM_SECTIONS = frozenset({
    "global",      # グローバル設定（別タブで管理）
    "printers",    # プリンターセクション
    "print$",      # プリンタードライバーセクション
    "homes",       # ホームディレクトリセクション
    "netlogon",    # ネットワークログオンセクション
    "profiles",    # プロファイルセクション
})

# 新規共有フォルダのデフォルト設定テンプレート
NEW_SHARE_TEMPLATE = {
    "path": "",
    "browseable": "yes",
    "read only": "no",
    "guest ok": "yes",
    "force user": "nobody",
    "force group": "nogroup",
    "create mask": "0777",
    "directory mask": "0777",
}

# ゲストアクセス時の設定項目
GUEST_SHARE_PARAMS = {
    "guest ok": "yes",
    "force user": "nobody",
    "force group": "nogroup",
    "create mask": "0777",
    "directory mask": "0777",
}

# 非ゲスト（ユーザー指定）時に除外する設定項目のキー
GUEST_ONLY_PARAMS = frozenset({
    "force user",
    "force group",
})

# === global設定のデフォルト値 ===
DEFAULT_GLOBAL_PARAMS = {
    "workgroup": "WORKGROUP",
    "server string": "%h server (Samba, Ubuntu)",
    "log file": "/var/log/samba/log.%m",
    "max log size": "1000",
    "logging": "file",
    "server role": "standalone server",
    "map to guest": "bad user",
}

# global設定の「その他」セクションに表示する設定項目
GLOBAL_EXTRA_PARAMS = [
    {"key": "server string", "label": "サーバー説明", "default": "%h server (Samba, Ubuntu)"},
    {"key": "log level", "label": "ログレベル", "default": "1"},
    {"key": "max log size", "label": "最大ログサイズ (KB)", "default": "1000"},
    {"key": "server min protocol", "label": "最小プロトコル", "default": "SMB2"},
]

# === バックアップ関連 ===
# バックアップファイル名のプレフィックス
BACKUP_PREFIX = "smb_"
# バックアップファイル名の日時フォーマット
BACKUP_DATETIME_FORMAT = "%Y%m%d_%H%M%S"
# バックアップファイル名の拡張子
BACKUP_EXTENSION = ".conf"
# 履歴ファイル名
HISTORY_FILENAME = "history.json"

# === バックアップカテゴリー ===
CATEGORY_SHARED_FOLDER = "shared_folder"
CATEGORY_GLOBAL = "global"
CATEGORY_DIRECT_EDIT = "direct_edit"
CATEGORY_RESTORE = "restore"

# カテゴリーの日本語表示名
CATEGORY_LABELS = {
    CATEGORY_SHARED_FOLDER: "共有設定の変更",
    CATEGORY_GLOBAL: "サーバー設定の変更",
    CATEGORY_DIRECT_EDIT: "エディターで直接編集",
    CATEGORY_RESTORE: "設定の復元",
}

# === UI定数 ===
# メインウィンドウのデフォルトサイズ
WINDOW_WIDTH = 950
WINDOW_HEIGHT = 750
# 一般ユーザーの最小UID
MIN_USER_UID = 1000

# === 設定ファイル名 ===
CONFIG_FILENAME = "config.json"


def get_app_dir() -> str:
    """アプリケーションのディレクトリパスを取得する"""
    # main.pyがあるディレクトリを返す
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_helper_path() -> str:
    """ヘルパースクリプトの絶対パスを取得する"""
    return os.path.join(get_app_dir(), HELPERS_DIR, HELPER_SCRIPT_NAME)
