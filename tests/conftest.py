"""pytest共享配置：注册asyncio标记并在无pytest-asyncio时直接驱动协程测试"""
import asyncio

import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "asyncio: mark test as an async coroutine test"
    )


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem):
    testfunction = pyfuncitem.obj
    if asyncio.iscoroutinefunction(testfunction):
        funcargs = pyfuncitem.funcargs
        testargs = {name: funcargs[name] for name in pyfuncitem._fixtureinfo.argnames}
        asyncio.run(testfunction(**testargs))
        return True
    return None
