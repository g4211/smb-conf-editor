# -*- coding: utf-8 -*-
"""
定数定義モジュール
アプリケーション全体で使用する定数を定義する
"""

import os

# === アプリケーション情報 ===
APP_NAME = "Samba設定エディター"
APP_VERSION = "1.2.0"
APP_LICENSE = "MIT License"
APP_REPOSITORY_URL = "https://github.com/g4211/smb-conf-editor"
APP_ISSUES_URL = "https://github.com/g4211/smb-conf-editor/issues"

# === ファイルパス ===
# Sambaメイン設定ファイルのパス
SMB_CONF_PATH = "/etc/samba/smb.conf"
# Sambaデフォルト設定ファイルのパス（初期状態に戻す用）
DEFAULT_SMB_CONF = "/usr/share/samba/smb.conf"
# デフォルトのログディレクトリ
DEFAULT_LOG_DIR = "/var/log/samba"

# === アプリケーション設定のデフォルト値 ===
APP_CONFIG_DIR = os.path.expanduser("~/.config/smb-conf-editor")

# 直接編集で使用するデフォルトのエディター (Ubuntu 24.04 デフォルト)
DEFAULT_EDITOR = "gnome-text-editor"
# デフォルトエディターの候補リスト（GUIエディター優先、CUIフォールバック）
DEFAULT_EDITOR_CANDIDATES = [
    "gnome-text-editor",  # Ubuntu 22.04+ (GNOME)
    "gedit",              # GNOME（旧バージョン）
    "kate",               # KDE
    "mousepad",           # Xfce
    "xed",                # Linux Mint
    "pluma",              # MATE
    "nano",               # CUI（ほぼ全環境に存在）
    "vi",                 # CUI（必ず存在）
]

# エディターの種類定数
EDITOR_TYPE_TERMINAL = "ターミナル"
EDITOR_TYPE_GRAPHICAL = "グラフィカル"

# デフォルトエディターの種類定義（内部保持）
DEFAULT_EDITORS = {
    "gnome-text-editor": EDITOR_TYPE_GRAPHICAL,
    "gedit":             EDITOR_TYPE_GRAPHICAL,
    "kate":              EDITOR_TYPE_GRAPHICAL,
    "mousepad":          EDITOR_TYPE_GRAPHICAL,
    "xed":               EDITOR_TYPE_GRAPHICAL,
    "pluma":             EDITOR_TYPE_GRAPHICAL,
    "nano":              EDITOR_TYPE_TERMINAL,
    "vi":                EDITOR_TYPE_TERMINAL,
}

# ターミナルエミュレータの候補（CUIエディター起動用）
# 各タプル: (cmd名, ベース引数リスト, コマンドを結合するか)
TERMINAL_CANDIDATES = [
    {"cmd": "gnome-terminal", "args": ["--wait", "--"], "join": False},
    {"cmd": "konsole",        "args": ["-e"],           "join": False},
    {"cmd": "xfce4-terminal", "args": ["-e"],           "join": True},
    {"cmd": "mate-terminal",  "args": ["-e"],           "join": True},
    {"cmd": "xterm",          "args": ["-e"],           "join": False},
]
# バックアップディレクトリのデフォルトパス
DEFAULT_BACKUP_DIR = os.path.join(APP_CONFIG_DIR, "backups")
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
# pathのデフォルトは /srv/samba/（FHS準拠、/home配下のアクセス権問題を回避）
NEW_SHARE_TEMPLATE = {
    "path": "/srv/samba/",
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

# パーミッションプリセット（共有フォルダのアクセス権設定）
PERMISSION_PRESETS = [
    {"label": "全員が読み書き可能", "create_mask": "0666", "directory_mask": "0777"},
    {"label": "一般的",         "create_mask": "0664", "directory_mask": "0775"},
    {"label": "セキュア",       "create_mask": "0660", "directory_mask": "0770"},
]

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
CATEGORY_SHARE = "share"
CATEGORY_SERVER = "server"
CATEGORY_DIRECT_EDIT = "direct_edit"
CATEGORY_RESTORE = "restore"

# カテゴリーの日本語表示名
CATEGORY_LABELS = {
    CATEGORY_SHARE: "共有設定の変更",
    CATEGORY_SERVER: "サーバー設定の変更",
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
