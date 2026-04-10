# Samba設定エディター (smb.conf Editor)

Ubuntu向けのSamba設定ファイル（`/etc/samba/smb.conf`）をGUIで編集するPythonアプリケーションです。

## 機能

- **共有フォルダ管理**: 共有フォルダの追加・編集・削除
- **global設定**: workgroup、hosts allow等のglobalパラメータ設定
- **直接編集**: 外部エディターによるsmb.confの直接編集
- **ログ表示**: Sambaログファイルの閲覧（検索・自動更新機能付き）
- **バックアップ/復元**: 設定変更時の自動バックアップと復元機能
- **差分表示**: バックアップと現在の設定の差分をカラー表示
- **Sambaユーザー管理**: ユーザーの登録・解除・有効化・無効化

## 必要環境

- Ubuntu 22.04以降
- Python 3.10以降
- Samba（`samba`, `samba-common-bin`）
- tkinter（通常はPythonに同梱）
- PolicyKit（`polkitd`, `pkexec`）

## インストール

### 方法1: DEBパッケージ（推奨）

```bash
# パッケージをビルド
./build-deb.sh

# パッケージをインストール
sudo apt install ./build_deb/smb-conf-editor_*.deb
```

### 方法2: 手動インストール

#### 1. 依存パッケージのインストール

```bash
# Sambaとtkinterのインストール（未インストールの場合）
sudo apt install samba samba-common-bin python3-tk

# Python依存パッケージのインストール
pip3 install -r requirements.txt
```

#### 2. ヘルパースクリプトの設定

ヘルパースクリプトに実行権限を付与します:

```bash
chmod +x helpers/smb-helper.sh
```

#### 3. PolicyKitポリシーの設定（パスワード入力不要にする）

セットアップスクリプトを実行すると、以降の操作でパスワード入力が不要になります:

```bash
bash scripts/setup-polkit.sh
```

> **注意**: PolicyKitポリシーをインストールしない場合でも、
> pkexecによる認証は動作しますが、操作のたびにパスワード入力が求められます。

## 使い方

```bash
python3 main.py
```

## タブの説明

### 📁 共有フォルダ
共有フォルダの一覧表示と編集。各フォルダのアクセス権限（ゲスト/ユーザー指定）を設定できます。

### ⚙ global設定
[global]セクションのworkgroupやhosts allow等を設定します。

### 🔧 詳細設定
外部エディターによるsmb.confの直接編集と、Sambaログファイルの閲覧を行います。

### 🕐 過去の設定に戻す
バックアップの管理と設定の復元を行います。変更時に自動作成されるバックアップから、過去の設定に戻すことができます。

## プロジェクト構成

```
smb-conf-editor/
├── main.py              # エントリーポイント
├── requirements.txt     # 依存パッケージ
├── build-deb.sh         # DEBパッケージビルドスクリプト
├── helpers/
│   └── smb-helper.sh    # root権限ヘルパースクリプト
├── scripts/
│   └── setup-polkit.sh  # Polkitポリシーセットアップ（開発環境用）
├── packaging/
│   ├── com.smbconfeditor.helper.policy  # Polkitポリシー（DEBパッケージ用）
│   ├── smb-conf-editor.desktop          # デスクトップエントリ
│   └── smb-conf-editor.png             # アプリケーションアイコン
├── smb_editor/
│   ├── app.py           # メインアプリケーション
│   ├── smb_parser.py    # smb.confパーサー
│   ├── smb_writer.py    # smb.conf書き込み
│   ├── system_utils.py  # システムユーティリティ
│   ├── backup_manager.py # バックアップ管理
│   ├── apply_manager.py # 適用処理
│   ├── config_manager.py # 設定管理
│   ├── constants.py     # 定数定義
│   ├── messages.py      # メッセージ定義
│   ├── tabs/            # UIタブ
│   └── dialogs/         # ダイアログ
└── docs/                # ドキュメント
```

## ライセンス

MIT License
