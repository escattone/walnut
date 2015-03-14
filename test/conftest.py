import pytest
from twisted.internet.defer import Deferred
from twisted.internet.protocol import ProcessProtocol


pytest_plugins = "pytest_twisted"


@pytest.fixture
def redis_conn(redis_server):
    from txredisapi import Connection
    return pytest.blockon(Connection(*redis_server))
