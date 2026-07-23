# Manual Test Results

## 2026-07-10 MVP1

Environment:

- Windows local PC
- FastAPI local server
- Browser UI at `http://127.0.0.1:8765`

Results:

- Local startup: passed
- Browser display: passed
- Config file button rendering: passed
- Scene execution for bath-related scene: passed
- Result display after execution: passed
- Resource export: passed
- Config generation from exported scenes: passed
- Misusing `switchbot.resources.json` as `config.json`: blocked with clear error

Notes:

- Monitor-related scenes returned success from the API, but physical behavior was not fully verified because related game devices were not powered on.
- Secret files and local device data remained ignored by Git.
