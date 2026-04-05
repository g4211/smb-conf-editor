# DEBパッケージ化に向けたシステムパスの規約修正計画

ご質問いただいた点（`./backups`、`gedit`、`config.json`の配置）は、Debianパッケージ（システム展開）を行う上で非常に重要なポイントですので、このタイミングでLinuxの標準的な作法（FHSやXDG Base Directory仕様）に合わせてすべて修正します。

## 対象の課題と修正方針

### 1. `config.json` と `history.json` の配置場所
- **現状**: アプリの実行場所 (`./`) に直接ファイルを作ってしまう。
- **課題**: `/opt/` や `/usr/bin/` にインストールされた場合、一般ユーザーに書き込み権限がないためエラーになる。
- **解決策**: ユーザーのホームディレクトリ配下である `~/.config/smb-conf-editor/` フォルダを自動で作って、そこへ保存するように変更します。

### 2. バックアップフォルダの場所 (`./backups`)
- **現状**: 実行直下に `backups` を作成している。
- **解決策**: 同様に、一般ユーザーが権限を持てる `~/.config/smb-conf-editor/backups/` へ保存されるようにコード側（`config_manager.py` および `constants.py`）を書き換えます。

### 3. デフォルトエディター（`gedit`）
- **現状**: `DEFAULT_EDITOR = "gedit"`
- **事実**: 鋭いご指摘の通り、Ubuntu Desktop 24.04 では `gedit` がプリインストールから外れ、代わりに **`gnome-text-editor`** が標準のGUIテキストエディターになっています。
- **解決策**: デフォルトを `"gnome-text-editor"` に変更します。（もし見つからない場合は `gedit` やターミナル上の `nano` などにフォールバックする仕組みを入れることも可能ですが、24.04専用であれば `"gnome-text-editor"` 決め打ちでも動作します）。今回は `"gnome-text-editor"` をデフォルトにします。

## 修正のステップ
1. `constants.py` で定義している `DEFAULT_BACKUP_DIR` および `DEFAULT_EDITOR` を変更します。（環境変数からホームディレクトリのパスを読み取るようにします）。
2. `config_manager.py` にて、ファイルの保存先が `~/.config/smb-conf-editor/` となるように保存ロジック（`os.path.expanduser` 等を用いたパス展開）を書き換えます。
3. すでに現在のフォルダに作られている古い `config.json` や `history.json`、`backups/` フォルダなどはそのまま無視するか手動で削除していただきます。

> [!NOTE]
> このパス修正を先に行うことで、`.deb` パッケージを入れた後でも問題なくユーザー権限でアプリが動くようになります！

上記の実装方針（`~/.config/smb-conf-editor/` をホームに利用する修正）で進めてよろしいでしょうか？
