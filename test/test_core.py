import pytest
from twisted.internet import defer

from walnut import async_cache


@pytest.inlineCallbacks
def test_async_cache_basic(redis_db):
    from twisted.internet import reactor

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


def test_async_cache_exceptions(redis_db):

    invalids = (
        dict(ttl='3'),
        dict(max_wait='4'),
        dict(keymaker='text'),
        dict(skip_cache_on='text'),
        dict(namespace=3),
        dict(json_encode_func='text'),
        dict(json_decode_func='text'),
        dict(id_tag=5),
        dict(key_sep=5),
        dict(lock_key_prefix=5),
        dict(value_key_prefix=5),
    )

    for kwargs in invalids:
        with pytest.raises(TypeError):
            async_cache(**kwargs)

    invalids = (
        dict(ttl=0),
        dict(max_wait=-1),
        dict(lock_key_prefix='|', value_key_prefix='|'),
    )

    for kwargs in invalids:
        with pytest.raises(ValueError):
            async_cache(**kwargs)
