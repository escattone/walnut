import pytest

from walnut.utils import get_qualified_name


class A(object):

    class B(object):

        @staticmethod
        def smeth(cls):
            pass

        @classmethod
        def cmeth(cls):
            pass

        def meth1(self):
            pass

        def meth2(self):
            yield None

        def __call__(self):
            pass

    @staticmethod
    def smeth(cls):
        pass

    @classmethod
    def cmeth(cls):
        pass

    def meth1(self):
        pass

    def meth2(self):
        yield None

    def __call__(self):
        pass


def func(*args, **kw):
    return None


def gen(*args, **kw):
    yield None


a = A()
b = A.B()
fx = lambda x: x


def test_get_qualified_name():
    def exp(name):
        return '{}.{}'.format(__name__, name)

    assert get_qualified_name(fx) == exp('<lambda>')
    assert get_qualified_name(gen) == exp('gen')
    assert get_qualified_name(func) == exp('func')
    assert get_qualified_name(A.smeth) == exp('smeth')
    assert get_qualified_name(A.B.smeth) == exp('smeth')
    assert get_qualified_name(a.smeth) == exp('smeth')
    assert get_qualified_name(b.smeth) == exp('smeth')

    invalids = (
        any,
        type,
        a,
        a.cmeth,
        a.meth1,
        a.meth2,
        a.__call__,
        b,
        b.cmeth,
        b.meth1,
        b.meth2,
        b.__call__,
        A,
        A.cmeth,
        A.meth1,
        A.meth2,
        A.__call__,
        A.B,
        A.B.cmeth,
        A.B.meth1,
        A.B.meth2,
        A.B.__call__,
    )

    for call in invalids:
        with pytest.raises(TypeError):
            get_qualified_name(call)
