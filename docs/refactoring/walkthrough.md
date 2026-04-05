# 設定パスおよびデフォルトエディターの修正の確認

## 修正内容
Debianパッケージ（`.deb`）としてシステムにインストール可能な構成へ修正するため、パスやデフォルトエディターの見直しを実施しました。

- **`smb_editor/constants.py`の修正**:
  - `APP_CONFIG_DIR` を追加し、`os.path.expanduser("~/.config/smb-conf-editor")` を定義しました。
  - Ubuntu 24.04 の変更に合わせ、`DEFAULT_EDITOR` を `"gnome-text-editor"` に変更しました。
  - `DEFAULT_BACKUP_DIR` が `APP_CONFIG_DIR` 配下の `backups` になるように定義を変更しました。

- **`smb_editor/config_manager.py`の修正**:
  - 設定ファイル (`config.json`) の保存先が `APP_CONFIG_DIR` を参照するように修正しました（前回セッションで完了済み）。
  - `get_backup_dir()` で相対パス（例: `"backups"`）が設定されている場合に、解決の基準を「アプリの実行ディレクトリ」から「設定ディレクトリ（`APP_CONFIG_DIR`）」へ変更しました。これにより、アプリのインストール場所によらず、バックアップは常に `~/.config/smb-conf-editor/backups/` 配下に格納されます。

- **`smb_editor/backup_manager.py`の確認**:
  - 履歴ファイル (`history.json`) の保存パスがバックアップディレクトリ配下になっており、設定ディレクトリに正常に追従していることを確認しました。

## テスト結果（動作確認）
以下の検証用スクリプトを利用して、パスが正確に解決されることを確認しました。

```python
import os, sys
sys.path.insert(0, os.path.abspath('.'))
from smb_editor.config_manager import ConfigManager

c = ConfigManager()
c.save()
print('Config path:', c.config_path)
print('Backup dir:', c.get_backup_dir())
```

**実行結果:**
```text
Config path: /home/a/.config/smb-conf-editor/config.json
Backup dir: /home/a/.config/smb-conf-editor/backups
```
これにより、期待通り一般ユーザーの権限で管理可能なディレクトリ構造にファイルが保存されることを確認しました。
