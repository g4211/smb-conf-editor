# タスクリスト: エディター管理 & パーミッションプリセット

## エディター管理機能

- [x] constants.py: DEFAULT_EDITORS辞書、TERMINAL_CANDIDATES、エディタータイプ定数を追加
- [x] config_manager.py: custom_editors、利用可能エディター一覧、ターミナル検出を追加
- [x] dialogs/editor_manager.py: エディター管理ダイアログを新規作成
- [x] tools_tab.py: Entry→Combobox変更、[確認]削除→[エディター管理]追加、CUIエディター対応
- [x] messages.py: 新しいUI文字列を追加

## force user / パーミッションプリセット

- [x] constants.py: PERMISSION_PRESETS定数を追加
- [x] shares_tab.py: パーミッションCombobox追加、/home判定でforce_user自動設定

## 検証

- [x] 全ファイル構文チェック: OK
- [ ] エディター管理ダイアログの動作確認
- [ ] CUIエディターのターミナル起動確認
- [ ] パーミッションプリセットの動作確認
- [ ] /home配下のforce_user自動変更確認
