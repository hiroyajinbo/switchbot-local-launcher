# SwitchBot Local Launcher

## Project Location

This project is managed under the shared development foundation:

```text
C:\Users\elega\Documents\CD開発フロー\projects\ローカル自動化ミニアプリ
```

Run setup, test, and application commands from this directory.

Windows PC上で起動し、ブラウザからSwitchBot機器やシーンを操作するローカル用ミニアプリです。

## セットアップ

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item config.example.json config.json
```

認証情報は、初回起動時の画面でSwitchBotアプリから取得したOpen TokenとSecret Keyを
入力します。接続確認後、現在のWindowsユーザーの「資格情報マネージャー」へ保存されます。
`.env` を使う従来方式も互換性のため利用でき、その場合は画面保存より優先されます。

`.env`方式を利用する場合だけ、次を実行して認証情報を記入します。

```powershell
Copy-Item .env.example .env
```

```text
SWITCHBOT_TOKEN=xxxx
SWITCHBOT_SECRET=yyyy
SWITCHBOT_CONFIG_PATH=config.json
SWITCHBOT_LOG_PATH=logs/switchbot-local-launcher.log
```

`.env` を利用しない場合、作成は省略できます。`config.json` に表示したいボタンを定義します。
`.env` と `config.json` はGit管理しません。

クイック操作グループは編集モードで先に登録し、シーンと赤外線クイック操作の「表示設定」から選択します。画面では同じグループのボタンがまとまって表示され、実行結果は直近5件まで新しい順に表示されます。

起動時にSwitchBotのシーンと安全なON/OFF対象デバイスの候補を取得します。未追加シーンがある場合はクイック操作の上部に件数が表示され、「すべて追加」または編集モードでの個別追加を選べます。追加内容は再起動なしで反映されます。

編集モードで既存シーンを「削除・除外」すると、以後の取得候補には表示されません。「除外済みシーン」から除外を解除すると再び追加候補へ戻せます。「新しいシーンを自動追加」を有効にした場合だけ、起動時に未追加シーンを自動でクイック操作へ追加します。除外設定は自動追加より優先され、自動追加がONの状態で除外解除したシーンは、SwitchBot一覧に存在すればその場で追加されます。この同期対象はSwitchBotシーンだけで、手動登録した赤外線クイック操作やデバイス設定は自動追加・除外されません。

デバイスカードは `config.json` の `rooms` に記録された順で表示されます。編集モードでは部屋の三点メニューから並べ替え・削除ができ、部屋やデバイス設定は画面へ先に反映してローカルへ保存されます。クイック操作グループも同じ流れで追加・並べ替え・削除でき、削除時は所属操作を既定の「シーン」へ移動します。グループ変更は登録済み一覧から選ぶと即時保存されます。各グループは件数付きの見出しから折りたため、状態はブラウザへ保存されます。クイック操作のアイコン設定、マイセットの編集・削除、ライト／ダーク表示の切り替えにも対応しています。

不要なデバイスは編集モードでランチャー上だけ非表示にできます。SwitchBot本体からは削除されず、部屋・アイコン・ロック・マイセット設定も保持されます。「機器・シーン設定」の非表示デバイス一覧からいつでも表示へ戻せます。

## 起動

```powershell
python -m app
```

日常利用では、PowerShellの実行ポリシーに影響されない次のコマンドを推奨します。
`.venv`または`config.json`が不足している場合は、その内容を表示して停止します。

```powershell
.\start.cmd
```

`start.ps1` も用意していますが、Windowsの実行ポリシーによって拒否される環境があります。ポリシーを変更する必要はありません。その場合は `start.cmd` を使用してください。

MVP3のPCアプリウィンドウを開く場合は、デスクトップ依存を導入してから `desktop.cmd` を実行します。

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev,desktop]"
.\desktop.cmd
```

ウィンドウを閉じると、内蔵ローカルサーバーも停止します。起動中にもう一度 `desktop.cmd` を実行した場合は新しいサーバーを作らず、既存ウィンドウを前面へ表示します。従来どおりブラウザで利用する場合は `start.cmd` を使用できます。

PCアプリの初回起動時は、プロジェクト直下に存在する`.env`と`config.json`を
`%LOCALAPPDATA%\SwitchBotLocalLauncher`へコピーします。`.env`がなくても起動でき、
初回画面で保存した認証情報はWindows資格情報マネージャーから読み込みます。
元ファイルは削除せず、コピー先に既存ファイルがある場合も上書きしません。
以後、PCアプリはコピー先の設定とログを使用します。

Windows GUIの基本動作は、次のスモークテストで自動確認できます。PCアプリを起動してウィンドウとヘルスAPIを検出し、自動で閉じた後にプロセスと8765番ポートが解放されたことを確認します。

```powershell
.\desktop-smoke.cmd
```

既定では初回状態取得の完了を待つため、ウィンドウを15秒表示します。表示時間を変える場合は、例えば `desktop-smoke.cmd --hold-seconds 5` と指定します。ログ内のPython例外も失敗として検出します。

## Windows PCアプリのビルド

Pythonを意識せず起動できる `onedir` 形式のWindowsアプリは、次のコマンドで作成します。

```powershell
.\build-desktop.cmd
```

生成先は `dist\SwitchBotLocalLauncher\SwitchBotLocalLauncher.exe` です。`onedir` 形式のため、配布時はEXEだけでなく `SwitchBotLocalLauncher` フォルダ全体をコピーします。
通常ビルドはキャッシュを利用します。リリース前などに中間生成物を破棄して作り直す場合は `build-desktop.cmd --clean` を使用します。

ビルドから生成EXEのGUIスモークテストまでまとめて実行する場合は、次を使用します。

```powershell
.\desktop-package-smoke.cmd
```

別PCへ持ち出せるフォルダとZIPは、次のコマンドで作成します。

```powershell
.\package-portable.cmd
```

通常パッケージは作成後に自動検査され、`.env`・`config.json`の混入や必須ファイルの不足が
見つかると失敗します。個人設定も含める場合だけ`--with-local-config`を指定してください。
詳細は`docs/portable-package.md`を参照してください。

GitHub Actionsでは、Linux上のlint・自動テストに加えて、Windows上で
`package-portable.cmd --clean`を実行します。デスクトップEXEのビルドと、
認証情報を含まないポータブルフォルダ／ZIPの生成まで継続的に検証します。

## ブラウザ拡張

`browser_extension` は、起動中のPCアプリに登録されたクイック操作をChromeまたは
Edgeのツールバーから実行するManifest V3拡張機能です。認証情報は保持せず、
`http://127.0.0.1:8765` だけへ接続します。

1. PCアプリを起動する
2. ブラウザの拡張機能管理画面で「デベロッパーモード」を有効にする
3. 「パッケージ化されていない拡張機能を読み込む」から `browser_extension` を選ぶ
4. ツールバーのSwitchBot拡張を開く

PCアプリが停止中の場合、ポップアップには起動案内が表示されます。

別PCで更新された最新版を取り込み、依存関係も更新してから起動する場合は、次を実行します。

```powershell
.\update-and-start.cmd
```

`update-and-start.cmd` は、現在のブランチを `git pull --ff-only` で安全に更新し、`.venv` のPython依存関係を同期してからアプリを起動します。ローカルに未コミットの変更がある場合は、変更を保護するため更新せずに停止します。日常利用では、このファイルへのデスクトップショートカットを作成すると、ダブルクリックだけで更新と起動を実行できます。

起動後、ブラウザで `http://127.0.0.1:8765` を開きます。
画面には操作ボタンに加えて、取得可能な環境情報とデバイス状態も表示されます。
サーバーログは既定で `logs/switchbot-local-launcher.log` に保存され、1MBごとに最大5世代までローテーションします。
保存先は `.env` の `SWITCHBOT_LOG_PATH` で変更できます。`Ctrl+C` で終了すると、サーバープロセスも停止します。

PowerShellの実行ポリシーで `Activate.ps1` が使えない場合は、仮想環境を有効化せずに直接実行できます。

```powershell
.\.venv\Scripts\python.exe -m app
```

## SwitchBot機器・シーン一覧のエクスポート

`.env` を設定したあと、SwitchBot APIから機器・シーン一覧を取得できます。

```powershell
.\.venv\Scripts\python.exe -m app.export_resources
```

結果は `switchbot.resources.json` に出力されます。このファイルはGit管理しません。
ここに出てきた `deviceId` や `sceneId` を `config.json` に写して、操作ボタンを作ります。

`switchbot.resources.json` 全体を `config.json` にコピーすることはできません。
`config.json` は以下のように、必ず `buttons` をルートにした実行用設定です。

```json
{
  "buttons": [
    {
      "id": "leaving_home",
      "label": "いってきます",
      "type": "scene",
      "scene_id": "replace-with-scene-id"
    }
  ]
}
```

エクスポート結果からシーンボタンの雛形を作る場合は、次を実行します。

```powershell
.\.venv\Scripts\python.exe -m app.config_from_resources
```

`config.generated.json` が作られます。内容を確認して、使いたいボタンを `config.json` にコピーしてください。

ON/OFF操作できそうなSwitchBot純正デバイスのボタン雛形を作る場合は、次を実行します。

```powershell
.\.venv\Scripts\python.exe -m app.config_device_commands
```

`config.device-buttons.generated.json` が作られます。対象は照明系とPlug Miniなど、ON/OFFが自然な機器に絞っています。
内容を確認して、使いたいボタンを `config.json` の `buttons` にコピーしてください。

## SwitchBot APIの深掘り調査

デバイス一覧、シーン一覧、取得可能なデバイス状態をまとめて調査できます。

```powershell
.\.venv\Scripts\python.exe -m app.inspect_switchbot
```

結果は `switchbot.inspection.json` に出力されます。このファイルはGit管理しません。
調査観点は [docs/switchbot-api-capability-notes.md](docs/switchbot-api-capability-notes.md) に記録します。
赤外線リモコンは一覧には出ますが、状態取得対象外として画面に表示します。

`Air Conditioner` と `DIY Air Conditioner` は、赤外線リモコン欄から温度・
モード・風量・電源をまとめて送信できます。APIでは実状態を取得できないため、
成功後の表示は「最後に送信した設定」です。詳細は
[`docs/infrared-remote-api.md`](docs/infrared-remote-api.md) を参照してください。
登録したエアコンのクイック操作は、編集モードで表示名・グループ・温度・モード・
風量・ON/OFFを変更できます。

エアコン以外の学習済み赤外線ボタンはAPIから一覧取得できないため、本アプリでは
直接操作せず、SwitchBotアプリで作成したシーンをクイック操作として利用します。

## 設定の検証

`config.json` の `scene_id` と `device_id` が、直近にエクスポートしたSwitchBot一覧に存在するか確認できます。

```powershell
.\.venv\Scripts\python.exe -m app.export_resources
.\.venv\Scripts\python.exe -m app.validate_config
```

未知のIDがある場合は該当するボタンIDを表示し、終了コード1で停止します。APIがリクエストを受け付けても実機が動くとは限らないため、設定変更後と実行テスト前にこの検証を行ってください。

## テスト

```powershell
python -m ruff check .
python -m pytest
```

### 失敗時UIの安全な確認

デバイスへコマンドを送信せず、操作APIだけを意図的に失敗させる場合は、`.env` に次を設定してアプリを再起動します。

```text
SWITCHBOT_FORCE_CONTROL_ERROR=true
```

この状態ではデバイス操作がすべてテスト用エラーになり、SwitchBotへコマンドは送信されません。カード内のエラー表示と、明るさ・色・色温度が操作前の値へ戻ることを確認できます。確認後は必ず `false` に戻して再起動してください。シーン実行と状態取得はこの設定の対象外です。

## 手動テスト

手動確認項目は [docs/manual-test-checklist.md](docs/manual-test-checklist.md) を使います。
