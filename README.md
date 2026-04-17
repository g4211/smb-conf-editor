# Samba設定エディター (smb-conf-editor)

Ubuntu向けのSamba設定ファイル（`/etc/samba/smb.conf`）をGUIで編集するPythonアプリケーションです。

## 機能

- **共有フォルダ管理**: 共有フォルダの追加・編集・削除
- **パーミッションプリセット**: 「全員が読み書き可能」「一般的」「セキュア」から選択
- **パス判定による自動設定**: `/home`配下の共有は`force user`をログインユーザーに自動設定
- **サーバー設定**: workgroup、hosts allow等のglobalパラメータ設定
- **直接編集**: 外部エディターによるsmb.confの直接編集（CUI/GUIエディター対応）
- **エディター管理**: カスタムエディターの追加・編集・削除（AppImage等にも対応）
- **ログ表示**: Sambaログファイルの閲覧（検索・自動更新機能付き）
- **バックアップ/復元**: 設定変更時の自動バックアップと復元機能
- **差分表示**: バックアップと現在の設定の差分をカラー表示
- **Sambaユーザー管理**: ユーザーの登録・解除・有効化・無効化
- **バージョン情報**: メニューバーの「ヘルプ」から確認可能

## 必要環境

- Ubuntu 22.04以降
- Python 3.10以降
- Samba（`samba`, `samba-common-bin`）
- tkinter（通常はPythonに同梱）
- PolicyKit（`polkitd`, `pkexec`）

## インストール

### 方法1: APTリポジトリから（推奨）

```bash
# リポジトリの追加とインストール
curl -fsSL https://g4211.github.io/apt-repo/install.sh | bash
sudo apt install smb-conf-editor
```

### 方法2: DEBパッケージを直接インストール

[Releases](https://github.com/g4211/smb-conf-editor/releases)からdebパッケージをダウンロードしてインストールします。

```bash
sudo apt install ./smb-conf-editor_*.deb
```

### 方法3: ソースから実行

#### 1. リポジトリのクローン

```bash
git clone https://github.com/g4211/smb-conf-editor.git
cd smb-conf-editor
```

#### 2. セットアップスクリプトの実行

依存パッケージのインストール、PolicyKitポリシーの設定、デスクトップエントリの作成を一括で行います。

```bash
bash scripts/setup.sh
```

#### 3. 起動

```bash
python3 main.py
```

セットアップ完了後は、アプリケーションメニューからも起動できます。

## タブの説明

### 📁 共有設定
共有フォルダの一覧表示と編集。各フォルダのアクセス権限（ゲスト/ユーザー指定）やパーミッションプリセットを設定できます。新規作成時のデフォルトパスは `/srv/samba/` です。

### ⚙ サーバー設定
[global]セクションのworkgroupやhosts allow等を設定します。その他の設定（サーバー説明、ログレベル等）も編集可能です。

### 🔧 ツール
- **Sambaユーザー管理**: ユーザーの登録・有効化・無効化
- **設定ファイルの直接編集**: 外部エディター（グラフィカル/ターミナル）によるsmb.confの編集
- **エディター管理**: デフォルト以外のカスタムエディターの追加・削除
- **ログファイル**: Sambaログの閲覧

### 📋 バックアップ
バックアップの管理と設定の復元を行います。変更時に自動作成されるバックアップから、過去の設定に戻すことができます。内容表示や差分表示も可能です。

## 設定ファイル

アプリケーションの設定は以下のディレクトリに保存されます。

| パス | 内容 |
|---|---|
| `~/.config/smb-conf-editor/config.json` | エディター設定、テーマ等 |
| `~/.config/smb-conf-editor/backups/` | smb.confの自動バックアップ |
| `~/.config/smb-conf-editor/history.json` | バックアップ履歴 |

## プロジェクト構成

```
smb-conf-editor/
├── main.py                  # エントリーポイント
├── requirements.txt         # Python依存パッケージ
├── build-deb.sh             # DEBパッケージビルドスクリプト
├── .github/
│   └── workflows/
│       └── release.yml      # 自動リリース/デプロイ（GitHub Actions）
├── helpers/
│   └── smb-helper.sh        # root権限ヘルパースクリプト
├── scripts/
│   ├── setup.sh             # セットアップスクリプト（ソース実行用）
│   ├── setup-polkit.sh      # Polkitポリシーセットアップ
│   └── publish-repo.sh      # APTリポジトリ手動パブリッシュ
├── packaging/
│   ├── com.smbconfeditor.helper.policy  # Polkitポリシー
│   ├── smb-conf-editor.desktop          # デスクトップエントリ
│   └── smb-conf-editor.png              # アプリケーションアイコン
├── smb_editor/
│   ├── app.py               # メインアプリケーション
│   ├── smb_parser.py        # smb.confパーサー
│   ├── smb_writer.py        # smb.conf書き込み
│   ├── system_utils.py      # システムユーティリティ
│   ├── backup_manager.py    # バックアップ管理
│   ├── apply_manager.py     # 適用処理
│   ├── config_manager.py    # 設定管理
│   ├── constants.py         # 定数定義
│   ├── messages.py          # メッセージ定義
│   ├── tabs/                # UIタブ
│   │   ├── shares_tab.py    #   共有設定タブ
│   │   ├── server_tab.py    #   サーバー設定タブ
│   │   ├── tools_tab.py     #   ツールタブ
│   │   └── history_tab.py   #   バックアップタブ
│   └── dialogs/             # ダイアログ
│       ├── editor_manager.py    # エディター管理
│       ├── content_viewer.py    # 内容表示
│       ├── diff_viewer.py       # 差分表示
│       ├── log_viewer.py        # ログビューア
│       └── password_dialog.py   # パスワード入力
└── docs/                    # 開発ドキュメント
```

## CI/CD

mainブランチへのpush時に `APP_VERSION` の変更を検出すると、GitHub Actionsで以下を自動実行します。

1. debパッケージのビルド
2. GitHub Releaseの作成
3. APTリポジトリへのデプロイ

バージョンのロールバック（例: 1.2.0 → 1.1.0）にも対応しており、前回のReleaseを自動削除してからデプロイし直します。

## ライセンス

MIT License
