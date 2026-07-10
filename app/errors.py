class LauncherError(Exception):
    """Base application error shown to the local UI."""

    user_message = "処理に失敗しました。"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.user_message)


class ConfigError(LauncherError):
    user_message = "設定ファイルに問題があります。"


class SecretConfigError(LauncherError):
    user_message = ".env のSwitchBot認証情報が未設定です。"


class SwitchBotApiError(LauncherError):
    user_message = "SwitchBot API呼び出しに失敗しました。"


class ActionNotFoundError(LauncherError):
    user_message = "指定されたボタンが見つかりません。"
