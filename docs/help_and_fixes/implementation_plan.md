# ヘルプダイアログ追加・バグ修正・デフォルトエディター・デフォルトパス変更

## 概要

4つの改善を実装する:
1. メニューバーに「ヘルプ」→「バージョン情報」ダイアログを追加
2. 「その他の設定」がデフォルト値を表示するバグを修正
3. デフォルトエディター候補の自動選択
4. 新規共有フォルダのデフォルトパスを `/srv/samba/` にする

---

## 変更内容

### 1. ヘルプ → バージョン情報ダイアログ

#### [MODIFY] [app.py](file:///home/a/mydata/scripts/Python/smb-conf-editor/smb_editor/app.py)

- `_build_ui()` にメニューバーを追加: ヘルプ → バージョン情報
- `_show_about_dialog()` メソッドを追加
  - Toplevelウィンドウで以下を表示:
    - アプリ名 + バージョン
    - ライセンス情報（MIT）
    - 設定ファイルのパス (`~/.config/smb-conf-editor/`)
    - バックアップの保存先 (`~/.config/smb-conf-editor/backups/`)
    - 必要環境（Samba, PolicyKit）
    - プロジェクトリポジトリへのリンク（クリックでブラウザ起動）
    - 問題報告先（GitHub Issues）

#### [MODIFY] [constants.py](file:///home/a/mydata/scripts/Python/smb-conf-editor/smb_editor/constants.py)

- `APP_REPOSITORY_URL` 定数を追加
- `APP_LICENSE` 定数を追加

---

### 2. 「その他の設定」バグ修正

#### [MODIFY] [server_tab.py](file:///home/a/mydata/scripts/Python/smb-conf-editor/smb_editor/tabs/server_tab.py)

**現在の問題:**
`_build_extra_settings_section()` (L100) で `param_info["default"]` を初期値に設定しているが、
`load_data()` (L160-164) で `global_section.get_param(key)` が `None` を返す場合（smb.confに該当パラメータが存在しない場合）、
`default` の値がそのまま表示され続ける。

**修正:**
- `load_data()` で、`GLOBAL_EXTRA_PARAMS` の各項目について:
  - smb.confに値がある → その値を表示
  - smb.confに値がない → **空欄**にする（現在はdefaultが残ったまま）
- UI構築時の初期値も `""` (空欄) にする

---

### 3. デフォルトエディター候補の自動選択

#### [MODIFY] [constants.py](file:///home/a/mydata/scripts/Python/smb-conf-editor/smb_editor/constants.py)

- `DEFAULT_EDITOR_CANDIDATES` リストを追加:
  ```python
  DEFAULT_EDITOR_CANDIDATES = [
      "gnome-text-editor",  # Ubuntu 22.04+
      "gedit",              # GNOME（旧バージョン）
      "kate",               # KDE
      "mousepad",           # Xfce
      "xed",                # Linux Mint
      "pluma",              # MATE
      "nano",               # CUI（ほぼ全環境に存在）
      "vi",                 # CUI（必ず存在）
  ]
  ```

#### [MODIFY] [config_manager.py](file:///home/a/mydata/scripts/Python/smb-conf-editor/smb_editor/config_manager.py)

- `_load()` メソッドで、`config.json` が存在しない（初回起動）場合:
  - `DEFAULT_EDITOR_CANDIDATES` の候補を順にチェック
  - 最初にインストールされているエディターをデフォルトに設定
  - どれもなければ現在の `DEFAULT_EDITOR` をフォールバック

---

### 4. 新規共有フォルダのデフォルトパス

#### [MODIFY] [constants.py](file:///home/a/mydata/scripts/Python/smb-conf-editor/smb_editor/constants.py)

- `NEW_SHARE_TEMPLATE` の `path` を `""` → `"/srv/samba/"` に変更

#### [MODIFY] [shares_tab.py](file:///home/a/mydata/scripts/Python/smb-conf-editor/smb_editor/tabs/shares_tab.py)

- 新規カードの `_path_var` 初期値に `/srv/samba/` を反映

---

## ユーザーの質問への回答（実装後に回答予定）

- CUI/GUIエディター判別とエディター登録機能
- force user / パーミッション / /home配下の警告

## 検証

- アプリ起動 → ヘルプ → バージョン情報ダイアログの表示確認
- 「その他の設定」を展開 → smb.confの実際の値が表示されるか確認
- config.jsonを削除して再起動 → インストール済みエディターが自動選択されるか確認
- 新規共有フォルダのパス欄に `/srv/samba/` がプリセットされているか確認
