# 名称変更に伴うリネーム実装計画

ユーザーがUI上で採用した新しい名称（ツール、サーバー設定、バックアップ等）に合わせて、内部の変数名、クラス名、およびファイル名を改名し、齟齬を解消します。

## 対象となる変更点

### 1. タブのファイル名変更
- `smb_editor/tabs/advanced_tab.py` ➔ `smb_editor/tabs/tools_tab.py`
- `smb_editor/tabs/global_tab.py` ➔ `smb_editor/tabs/server_tab.py`
- `smb_editor/tabs/history_tab.py` ➔ `smb_editor/tabs/backup_tab.py`

### 2. クラス名の変更
- `AdvancedTab` ➔ `ToolsTab`
- `GlobalTab` ➔ `ServerTab`
- `HistoryTab` ➔ `BackupTab`

### 3. 変数名の変更
- `app.py` におけるインスタンス変数
  - `self._advanced_tab` ➔ `self._tools_tab`
  - `self._global_tab` ➔ `self._server_tab`
  - `self._history_tab` ➔ `self._backup_tab`
- その他関連モジュール内での `global` や `advanced`, `history` などの命名を `server`, `tools`, `backup` に統一

## User Review Required

> [!WARNING]
> バックアップカテゴリー名 (`CATEGORY_SHARED_FOLDER`, `CATEGORY_GLOBAL`) を定数ファイル (`constants.py`) で内部的に管理していますが、これを `CATEGORY_SHARE`, `CATEGORY_SERVER` のように変更すると、既存の `history.json` に保存されたカテゴリーの名前と一致しなくなってしまいます（過去のバックアップのカテゴリーが正しく表示されなくなる等の影響）。
> 
> これに対する対応方針として、以下のどちらが良いかご確認をお願いします：
> 1. **定数の値（内部データ文字列）自体は過去との互換性のために変更せず、ソース内の変数名（`CATEGORY_SERVER`など）だけを変更する**
> 2. **データ文字列も変更する（過去の履歴については表示が少し崩れるか、歴史ファイル「history.json」も一緒にマイグレーション書き換えを行う）**

## 手順
1. `git mv` コマンドを使用して対象タブファイルをリネーム（Gitの履歴を保持）
2. `app.py`, `messages.py`, `constants.py` のクラス名および変数名のインポートを修正
3. 最新の `history.json` へのマイグレーション（ユーザーの要望に応じて）
4. ASTチェックおよびアプリケーションの起動確認
5. コミットして提出
