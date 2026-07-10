# SwitchBot Local Launcher

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
```

`config.json` に表示したいボタンを定義します。`.env` と `config.json` はGit管理しません。

## 起動

```powershell
python -m app
```

起動後、ブラウザで `http://127.0.0.1:8765` を開きます。

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

## テスト

```powershell
python -m ruff check .
python -m pytest
```

## 手動テスト

手動確認項目は [docs/manual-test-checklist.md](docs/manual-test-checklist.md) を使います。
