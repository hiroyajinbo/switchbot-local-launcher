from app.desktop_integration import RUN_VALUE_NAME, DesktopIntegration


class FakeKey:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None


class FakeRegistry:
    HKEY_CURRENT_USER = "HKCU"
    KEY_READ = 1
    KEY_SET_VALUE = 2
    REG_SZ = 1

    def __init__(self) -> None:
        self.values = {}

    def OpenKey(self, *_args):
        if RUN_VALUE_NAME not in self.values:
            raise FileNotFoundError
        return FakeKey()

    def CreateKeyEx(self, *_args):
        return FakeKey()

    def QueryValueEx(self, _key, name):
        if name not in self.values:
            raise FileNotFoundError
        return self.values[name], self.REG_SZ

    def SetValueEx(self, _key, name, _reserved, _value_type, value):
        self.values[name] = value

    def DeleteValue(self, _key, name):
        if name not in self.values:
            raise FileNotFoundError
        del self.values[name]


def test_autostart_can_be_enabled_and_disabled(tmp_path) -> None:
    registry = FakeRegistry()
    service = DesktopIntegration(
        tmp_path / "logs" / "launcher.log",
        command='"C:\\App\\Launcher.exe"',
        registry=registry,
    )

    assert service.autostart_enabled() is False
    assert service.set_autostart(True) is True
    assert registry.values[RUN_VALUE_NAME] == '"C:\\App\\Launcher.exe"'
    assert service.set_autostart(False) is False


def test_open_log_directory_creates_and_opens_folder(tmp_path) -> None:
    opened = []
    service = DesktopIntegration(
        tmp_path / "logs" / "launcher.log",
        command="launcher",
        registry=FakeRegistry(),
        folder_opener=opened.append,
    )

    result = service.open_log_directory()

    assert result == str(tmp_path / "logs")
    assert (tmp_path / "logs").is_dir()
    assert opened == [str(tmp_path / "logs")]
