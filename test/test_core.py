import pytest
from twisted.internet import defer


@pytest.inlineCallbacks
def test_async_cache_basic(redis_conn):
    from twisted.internet import reactor
    from walnut.redis.twisted import async_cache

    cache = async_cache(redis=redis_conn, skip_on_errors=())

    @cache
    def echo(val):
        d = defer.Deferred()
        reactor.callLater(0.5, d.callback, val)
        return d

    result = yield echo('hello world')

    assert result == 'hello world'

    result = yield echo('hello world')

    assert result == 'hello world'

    assert False
