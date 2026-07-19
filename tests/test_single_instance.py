from app.single_instance import ERROR_ALREADY_EXISTS, SingleInstance


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
