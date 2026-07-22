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
SwitchBotLocalLauncher-portable\.env
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

テンプレートのみのパッケージでは、認証情報と設定ファイルは同梱されません。
初回起動前に次の準備をしてください。

1. `.env.example` をコピーして `.env` を作成します。
2. `.env` に `SWITCHBOT_TOKEN` と `SWITCHBOT_SECRET` を設定します。
3. `config.example.json` をコピーして `config.json` を作成します。
4. `config.json` を編集するか、起動後に編集モードから設定します。
5. `start.cmd` を実行します。

`.env` または `config.json` が無い場合、`start.cmd` はアプリを起動せずに停止します。
通常版の保存先へ静かに切り替わることはありません。

## 設定込みでパッケージを作る場合

開発ディレクトリから次を実行すると、現在の `.env` と `config.json` を含めた
ポータブルパッケージを作成できます。

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

PyInstaller の中間生成物も作り直す場合:

```cmd
package-portable.cmd --clean
```
