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
Copy-Item .env.example .env
Copy-Item config.example.json config.json
```

`.env` にSwitchBotアプリで取得したOpen TokenとSecret Keyを設定します。

```text
SWITCHBOT_TOKEN=xxxx
SWITCHBOT_SECRET=yyyy
SWITCHBOT_CONFIG_PATH=config.json
SWITCHBOT_LOG_PATH=logs/switchbot-local-launcher.log
```

`config.json` に表示したいボタンを定義します。`.env` と `config.json` はGit管理しません。

各ボタンには省略可能な `group` を指定できます。画面では同じグループのボタンがまとまって表示され、省略時は「その他」になります。実行結果は直近5件まで新しい順に表示されます。

画面の「最新候補を取得」から、SwitchBotのシーンと安全なON/OFF対象デバイスを取得できます。追加する項目だけを選び「選択項目を設定へ追加」を押すと、既存設定を残したまま `config.json` へ追記します。反映後はアプリを再起動してください。

デバイスカードは `config.json` の `rooms` に記録された順で表示されます。編集モードでは部屋の三点メニューから並べ替え・削除ができ、部屋やデバイス設定は画面へ先に反映してローカルへ保存されます。クイック操作にはベースアイコンと上下・ON/OFFなどの操作バッジを組み合わせて設定できます。マイセットの編集・削除、ライト／ダーク表示の切り替えにも対応しています。

## 起動

```powershell
python -m app
```

日常利用では、PowerShellの実行ポリシーに影響されない次のコマンドを推奨します。`.venv`、`.env`、`config.json` が不足している場合は、その内容を表示して停止します。

```powershell
.\start.cmd
```

`start.ps1` も用意していますが、Windowsの実行ポリシーによって拒否される環境があります。ポリシーを変更する必要はありません。その場合は `start.cmd` を使用してください。

MVP3のPCアプリウィンドウを開く場合は、デスクトップ依存を導入してから `desktop.cmd` を実行します。

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev,desktop]"
.\desktop.cmd
```

ウィンドウを閉じると、内蔵ローカルサーバーも停止します。従来どおりブラウザで利用する場合は `start.cmd` を使用できます。

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
