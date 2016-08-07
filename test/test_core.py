import pytest
from twisted.internet import defer


@pytest.inlineCallbacks
def test_async_cache_basic(redis_db):
    from twisted.internet import reactor
    from walnut import async_cache

    calls = []
    delay = 0.3

    @async_cache
    def func(a, b):
        calls.append('a={0}, b={1}'.format(a, b))
        d = defer.Deferred()
        result = '{0} likes {1}'.format(a, b)
        reactor.callLater(delay, d.callback, result)
        return d

    result = yield func('john', 'fruit')
    assert calls == ['a=john, b=fruit']
    assert result == 'john likes fruit'

    result = yield func('john', 'fruit')
    assert calls == ['a=john, b=fruit']
    assert result == 'john likes fruit'

    result = yield func(a='john', b='fruit')
    assert calls == ['a=john, b=fruit'] * 2
    assert result == 'john likes fruit'

    result = yield func('john', b='fruit')
    assert calls == ['a=john, b=fruit'] * 3
    assert result == 'john likes fruit'

    calls = []

    d_rob1 = func('rob', 'drums')
    d_rob2 = func('rob', 'drums')

    result = yield d_rob1
    assert calls == ['a=rob, b=drums']
    assert result == 'rob likes drums'
    result = yield d_rob2
    assert calls == ['a=rob, b=drums']
    assert result == 'rob likes drums'
