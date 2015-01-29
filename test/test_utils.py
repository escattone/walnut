from walnut import PYTHON_VERSION
from walnut.utils import get_qualified_name


class A(object):

    class B(object):

        def meth1(self):
            pass

        def meth2(self):
            yield None

        def __call__(self):
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
    assert get_qualified_name(any) == '__builtin__.any'
    assert get_qualified_name(type) == '__builtin__.type'
    assert get_qualified_name(a.meth1) == exp('A.meth1')
    assert get_qualified_name(a.meth2) == exp('A.meth2')
    assert get_qualified_name(A.meth1) == exp('A.meth1')
    assert get_qualified_name(A.meth2) == exp('A.meth2')
    assert get_qualified_name(a) == exp('A.__call__')
    assert get_qualified_name(A.__call__) == exp('A.__call__')
    assert get_qualified_name(A) == exp('A')
    # Nested classes are NOT handled correctly.
    assert get_qualified_name(b.meth1) == exp('B.meth1')
    assert get_qualified_name(b.meth2) == exp('B.meth2')
    assert get_qualified_name(A.B.meth1) == exp('B.meth1')
    assert get_qualified_name(A.B.meth2) == exp('B.meth2')
    assert get_qualified_name(b) == exp('B.__call__')
    assert get_qualified_name(A.B.__call__) == exp('B.__call__')
    assert get_qualified_name(A.B) == exp('B')
