# -*- coding: utf-8 -*-
"""
UIメッセージ定数定義モジュール
アプリケーション全体で使用するユーザー向けメッセージやラベルを定義する
"""

class UI:
    # 共通ボタン
    BTN_APPLY = "✓ 適用"
    BTN_THEME = "🌙/☀ テーマ"
    BTN_RELOAD = "🔄 再読み込み"
    BTN_BROWSE = "参照"
    BTN_DELETE = "削除"
    BTN_CONFIRM = "確認"
    BTN_UPDATE = "更新"
    BTN_SAVE = "設定を保存"

    # タブ名
    TAB_SHARES = " 📁 共有設定 "
    TAB_GLOBAL = " ⚙ サーバー設定 "
    TAB_ADVANCED = " 🔧 ツール "
    TAB_HISTORY = " 📋 バックアップ "

    # アプリ全体説明
    DESC_APP_APPLY = "共有設定とサーバー設定をまとめて smb.conf に適用します"

    # 共有設定タブ
    DESC_SHARES_TAB = "共有フォルダの設定を編集し、上部の[適用]で保存します"
    LBL_SHARE_NAME = "共有名:"
    LBL_DIRECTORY = "ディレクトリ:"
    LBL_COMMENT = "コメント:"
    LBL_READONLY = "読み取り専用"
    LBL_GUEST = "ゲスト"
    LBL_ACCESS_PERM = "アクセス許可"
    LBL_PENDING_CREATE = "📁 作成予定"
    DESC_SAMBA_STATUS = "[未] 未登録  [有] Samba有効  [無] Samba無効（適用時に自動で有効化されます）"

    # サーバー設定タブ (Global)
    DESC_GLOBAL_TAB = "[global]セクションの設定を編集し、上部の[適用]で保存します"
    LBL_BASIC_SETTINGS = "基本設定"
    LBL_WORKGROUP = "workgroup:"
    LBL_HOSTS_ALLOW = "アクセス許可（hosts allow）"
    DESC_HOSTS_ALLOW = "改行区切りでIPアドレス/ネットワーク/ホスト名を入力\n（IPv4, IPv6, ホスト名, EXCEPT構文に対応。空欄の場合はhosts allowを削除）"
    BTN_AUTO_FILL_NET = "自分が所属するネットワークアドレスを自動入力"
    LBL_EXTRA_SETTINGS = "その他の設定"

    # ツールタブ (Advanced)
    LBL_USER_MANAGE = "Sambaユーザー管理"
    LBL_USERNAME = "ユーザー名"
    LBL_STATUS = "状態"
    LBL_REGISTER_UNREGISTER = "登録/解除"
    LBL_ENABLE_DISABLE = "有効/無効"
    LBL_DIRECT_EDIT = "設定ファイルの直接編集"
    LBL_USE_EDITOR = "使用するエディター:"
    BTN_EDIT_WITH_EDITOR = "エディターで編集"
    DESC_DIRECT_EDIT = "[エディターで編集]をクリックすると、指定したエディターでsmb.confを編集できます。\nエディター終了後、変更があれば構文チェック→適用を実行します。"
    LBL_LOG_FILE = "ログファイル"
    LBL_LOG_DIR = "ログディレクトリ:"

    # バックアップタブ (History)
    LBL_BACKUP_SETTINGS = "バックアップ設定"
    LBL_DEFAULT_CONF = "初期設定ファイル:"
    LBL_BACKUP_DIR = "バックアップディレクトリ:"
    LBL_MAX_BACKUPS = "バックアップ最大数:"
    LBL_BACKUP_LIST = "バックアップ一覧"
    BTN_UPDATE_LIST = "一覧を更新"
    BTN_SHOW_CONTENT = "内容表示"
    BTN_SHOW_DIFF = "差分表示"
    BTN_RESTORE = "この設定に戻す"
    LBL_EXCLUDE_DELETE = "削除対象から除外"

class MSGS:
    # エラーメッセージ等
    ERR_CONF_NOT_FOUND = "設定ファイル '{path}' が見つかりません"
    ERR_HELPER_NOT_FOUND = "ヘルパースクリプトが見つかりません: {path}"
    ERR_READ_FAIL = "ファイルの読み取りに失敗: {err}"
