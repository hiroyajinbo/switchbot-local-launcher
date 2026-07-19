from app.single_instance import ERROR_ALREADY_EXISTS, SW_RESTORE, SingleInstance, focus_window


class FakeKernel32:
    def __init__(self, handle=123) -> None:
        self.handle = handle
        self.closed = []

    def CreateMutexW(self, _attributes, _initial_owner, _name):
        return self.handle

    def CloseHandle(self, handle):
        self.closed.append(handle)
        return True


def test_first_instance_keeps_mutex_handle_until_closed() -> None:
    kernel32 = FakeKernel32()
    instance = SingleInstance(kernel32=kernel32, get_last_error=lambda: 0)

    assert instance.acquire() is True
    assert kernel32.closed == []

    instance.close()

    assert kernel32.closed == [123]


def test_second_instance_closes_duplicate_handle_immediately() -> None:
    kernel32 = FakeKernel32()
    instance = SingleInstance(
        kernel32=kernel32,
        get_last_error=lambda: ERROR_ALREADY_EXISTS,
    )

    assert instance.acquire() is False
    assert kernel32.closed == [123]


class FakeUser32:
    def __init__(self, handle=456) -> None:
        self.handle = handle
        self.shown = []
        self.focused = []

    def FindWindowW(self, _class_name, _title):
        return self.handle

    def ShowWindow(self, handle, command):
        self.shown.append((handle, command))
        return True

    def SetForegroundWindow(self, handle):
        self.focused.append(handle)
        return True


def test_focus_window_restores_existing_window() -> None:
    user32 = FakeUser32()

    assert focus_window("SwitchBot Local Launcher", user32) is True
    assert user32.shown == [(456, SW_RESTORE)]
    assert user32.focused == [456]


def test_focus_window_returns_false_when_window_is_not_found() -> None:
    assert focus_window("SwitchBot Local Launcher", FakeUser32(handle=0)) is False
