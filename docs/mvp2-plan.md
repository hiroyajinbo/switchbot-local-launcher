# MVP2 Plan

MVP1でSwitchBot scene実行まで確認できたため、MVP2では日常利用しやすくする改善と、SwitchBot Open APIで扱えるデータ/操作範囲の調査を進める。

## Goals

- Manual test results are recorded.
- Startup is easier on Windows.
- Button UI is easier to scan and operate.
- SwitchBot API capabilities are documented from official docs and local inspection.
- Device status fields are exported for real devices where the API supports them.

## Work Items

1. Record MVP1 manual test results.
2. Show Hub 2 temperature, humidity, and light level in the browser UI.
3. Show readable device statuses in the browser UI.
4. Add `start.bat` or `start.ps1` for daily launch.
5. Add UI grouping and recent execution history.
6. Add config validation and safer config generation.
7. Inspect SwitchBot API data:
   - devices
   - infrared remotes
   - device statuses
   - scenes
   - hub temperature/humidity if exposed in status
   - unsupported or unknown areas such as rooms and automations

## Out of Scope for MVP2

- Cloud-hosted server.
- External network access.
- Alexa integration.
- Device registration from this app unless the official API clearly supports it.
- Automation creation/editing unless the official API clearly supports it.
