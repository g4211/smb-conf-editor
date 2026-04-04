# Samba設定エディター (smb.conf Editor)

Ubuntu向けのSamba設定ファイル（`/etc/samba/smb.conf`）をGUIで編集するPythonアプリケーションです。

## 機能

- **共有フォルダ管理**: 共有フォルダの追加・編集・削除
- **global設定**: workgroup、hosts allow等のglobalパラメータ設定
- **直接編集**: 外部エディターによるsmb.confの直接編集
- **ログ表示**: Sambaログファイルの閲覧（検索・自動更新機能付き）
- **バックアップ/復元**: 設定変更時の自動バックアップと復元機能
- **差分表示**: バックアップと現在の設定の差分をカラー表示

## 必要環境

- Ubuntu 22.04以降
- Python 3.10以降
- Samba（`samba`, `samba-common-bin`）
- tkinter（通常はPythonに同梱）
- PolicyKit（`policykit-1`）

## インストール

### 1. 依存パッケージのインストール

```bash
# Sambaとtkinterのインストール（未インストールの場合）
sudo apt install samba samba-common-bin python3-tk

# Python依存パッケージのインストール
pip3 install -r requirements.txt
```

### 2. ヘルパースクリプトの設定

ヘルパースクリプトに実行権限を付与します:

```bash
chmod +x helpers/smb-helper.sh
```

### 3. PolicyKitポリシーの設定（推奨）

PolicyKitポリシーファイルをシステムにインストールすると、
pkexecの認証ダイアログにアプリケーション名が表示されます:

```bash
# ヘルパースクリプトをシステムパスにコピー
sudo cp helpers/smb-helper.sh /usr/local/bin/smb-helper.sh
sudo chmod 755 /usr/local/bin/smb-helper.sh

# PolicyKitポリシーファイルをインストール
sudo cp helpers/com.github.smb-conf-editor.policy /usr/share/polkit-1/actions/
```

> **注意**: PolicyKitポリシーをインストールしない場合でも、
> pkexecによる認証は動作しますが、一般的な認証ダイアログが表示されます。

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
├── config.json          # アプリ設定（自動生成）
├── requirements.txt     # 依存パッケージ
├── helpers/
│   ├── smb-helper.sh    # root権限ヘルパースクリプト
│   └── *.policy         # PolicyKitポリシー
├── smb_editor/
│   ├── app.py           # メインアプリケーション
│   ├── smb_parser.py    # smb.confパーサー
│   ├── smb_writer.py    # smb.conf書き込み
│   ├── system_utils.py  # システムユーティリティ
│   ├── backup_manager.py # バックアップ管理
│   ├── apply_manager.py # 適用処理
│   ├── config_manager.py # 設定管理
│   ├── constants.py     # 定数定義
│   ├── tabs/            # UIタブ
│   └── dialogs/         # ダイアログ
└── backups/             # バックアップファイル（自動生成）
```

## ライセンス

MIT License
