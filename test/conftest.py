import subprocess

import pytest


pytest_plugins = "pytest_twisted"


@pytest.yield_fixture(scope='session')
def redis_db():
    yield
    subprocess.check_call(['redis-cli', 'flushall'])


@pytest.fixture
def redis_conn(redis_server):
    from txredisapi import Connection
    return pytest.blockon(Connection(*redis_server))
