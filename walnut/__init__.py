import sys
from walnut.core import async_cache  # noqa


if sys.version_info[:2] < (2, 7):
    raise Exception('Python versions less than 2.7 are not supported')
