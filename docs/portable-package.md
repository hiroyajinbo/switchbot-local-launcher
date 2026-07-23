# SwitchBot Local Launcher ポータブル版

このフォルダは、Python の開発環境を用意せずに Windows PC で起動するための
ポータブル版です。

## 起動方法

基本的には `SwitchBotLocalLauncher.exe` を直接起動せず、同じフォルダにある
`start.cmd` から起動してください。

```cmd
start.cmd
```

`start.cmd` から起動した場合、設定とログはこのフォルダ内に保存されます。

```text
SwitchBotLocalLauncher-portable\.env（従来方式を使う場合のみ）
SwitchBotLocalLauncher-portable\config.json
SwitchBotLocalLauncher-portable\logs
```

`SwitchBotLocalLauncher.exe` を直接起動した場合は通常版扱いになり、保存先は
Windows のアプリデータフォルダになります。

```text
%LOCALAPPDATA%\SwitchBotLocalLauncher
```

どちらの保存先を使っているかは、アプリの編集モード内にある PC アプリ欄の
`Mode` / `Config` / `Log` で確認できます。

## 初回セットアップ

テンプレートのみのパッケージには認証情報を同梱しません。
初回起動は次の手順です。

1. `start.cmd`または`SwitchBotLocalLauncher.exe`を実行します。
2. 初回セットアップ画面へOpen TokenとSecret Keyを入力します。
3. 接続確認後、通常画面が表示されます。
4. 編集モードから機器・シーンを取得して設定します。

`config.json`がない場合、`start.cmd`が`config.example.json`から自動作成します。
EXEを直接起動した場合も`portable.marker`を検出してポータブルモードへ入り、
同じように`config.example.json`から`config.json`を自動作成します。
認証情報はWindows資格情報マネージャーへ保存され、ポータブルフォルダやZIPには入りません。
同じWindowsユーザーで起動する複数の配置先は認証情報だけを共有し、ロック・部屋・表示設定は
それぞれの`config.json`で独立して管理します。従来どおり`.env`を配置した場合は、そちらを
優先して利用できます。

TokenまたはSecret Keyを更新した場合は、通常画面上部の「API設定」から再入力します。
新しい認証情報でSwitchBot APIへ接続できた場合だけ、Windows資格情報が上書きされます。
`.env`を利用している場合は画面から更新せず、`.env`を書き換えてアプリを再起動してください。

## 設定込みでパッケージを作る場合

開発ディレクトリから次を実行すると、現在の`config.json`を含めた
ポータブルパッケージを作成できます。開発ディレクトリに`.env`も存在する場合は、
互換動作のため`.env`も同梱されます。

```cmd
package-portable.cmd --with-local-config
```

`.env` には SwitchBot の認証情報が入るため、このパッケージは公開せず、
自分の管理できる場所だけで扱ってください。

## パッケージ作成コマンド

テンプレートのみのポータブル版を作る場合:

```cmd
package-portable.cmd
```

出力先:

```text
dist\portable\SwitchBotLocalLauncher-portable
dist\portable\SwitchBotLocalLauncher-portable.zip
```

作成後はフォルダとZIPを自動検査します。通常パッケージに`.env`または`config.json`が
混入している場合や、起動に必要なファイルが不足している場合はエラーで停止します。
`--with-local-config`を指定した個人用パッケージでは、明示的に設定ファイルの同梱を許可します。

PyInstaller の中間生成物も作り直す場合:

```cmd
package-portable.cmd --clean
```
