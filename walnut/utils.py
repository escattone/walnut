#
# The MIT License (MIT)
#
# Copyright (c) 2015 Ryan Johnson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import inspect
import functools
from hashlib import sha1


SHA1_HEXDIGEST_SIZE = sha1().digest_size * 2


def get_qualified_name(func):
    """
    """
    module = inspect.getmodule(func)

    if inspect.isfunction(func):
        objs = (module, func)
    elif inspect.ismethod(func):
        objs = (module, func.im_class, func)
    elif callable(func):
        if hasattr(func, '__name__'):
            objs = (module, func)
        elif hasattr(func, '__class__'):
            objs = (module, func.__class__, func.__call__)
        else:
            raise TypeError('{!r} is not a '
                            'supported callable'.format(func))
    else:
        raise TypeError('{!r} is not callable'.format(func))

    return '.'.join(o.__name__ for o in objs if o)


def wraps(wrapped):
    """
    This mimics the functionality of the Python 3.4 functools.wraps
    in its addition of the "__wrapped__" attribute which always refers
    to the wrapped function, even if that function defined a "__wrapped__"
    attribute.
    """
    def wrapper(func):
        func = functools.wraps(wrapped)(func)
        func.__wrapped__ = wrapped
        return func
    return wrapper


def make_key(func, args, kwargs):
    """
    Make the key for this call of "func" with the given "args" and "kwargs".
    This implementation has limitations in terms of the data types allowed
    for the positional and keyword arguments passed into "func". Specifically,
    an instance of any data-type whose "repr" value is consistent as well as
    equivalent to the "repr" value of any other instance of that same data-type
    that would be considered equivalent. This certainly holds for numbers
    (integers, floats), strings, and datetime.datetime objects, as well as
    tuples, lists, or any other ordered container of those objects. It does not
    hold for unordered containers, like sets and dictionaries, unless their
    "__repr__" method has been overridden to return an ordered representation.
    """
    if not (args or kwargs):
        return None

    value = ''

    if args:
        if inspect.ismethod(func):
            # Skip the first argument ("self" or "cls") if
            # the function is a method or classmethod.
            args = args[1:]
        value += repr(args)

    if kwargs:
        value += repr(sorted(kwargs.iteritems()))

    if len(value) > SHA1_HEXDIGEST_SIZE:
        return sha1(value).hexdigest()

    return value
