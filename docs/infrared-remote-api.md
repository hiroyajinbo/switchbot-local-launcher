# SwitchBot赤外線リモコンAPI調査

調査日: 2026-07-20

## 取得できる情報

`GET /v1.1/devices` の `infraredRemoteList` から、リモコンID、表示名、
`remoteType`、親Hub IDを取得できる。手元のエクスポートでは次を確認した。

- Air Conditioner: 2台
- DIY Fan: 1台
- DIY Light: 1台
- Others: 1台

赤外線リモコンには状態取得APIがないため、画面へ実状態を表示しない。
操作後は「最後に送信した設定」と明示する。

## エアコン操作

公式仕様では `POST /v1.1/devices/{deviceId}/commands` に次を送る。

```json
{
  "command": "setAll",
  "parameter": "26,2,3,on",
  "commandType": "command"
}
```

`parameter` は `{温度},{モード},{風量},{電源}` の順。

- モード: `1` 自動、`2` 冷房、`3` 除湿、`4` 送風、`5` 暖房
- 風量: `1` 自動、`2` 弱、`3` 中、`4` 強
- 電源: `on` / `off`

本アプリの初期UIでは温度を16～30℃に限定する。これは操作ミスを防ぐための
UI側の実用範囲であり、SwitchBot公式仕様が明記する範囲ではない。

## その他のリモコン

- 多くの機器は `turnOn` / `turnOff` を利用できる
- DIYボタンはボタン名を `command` にし、`commandType` を `customize` にする
- テレビ系、スピーカー、扇風機、照明には種別固有コマンドがある

機種固有UIはエアコンの実機確認後に順次追加する。

参照: [SwitchBot API v1.1公式README](https://github.com/OpenWonderLabs/SwitchBotAPI/blob/main/README.md#command-set-for-virtual-infrared-remote-devices)
