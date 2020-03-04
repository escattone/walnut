walnut
======

![Build Status](https://travis-ci.org/escattone/walnut.svg?branch=master)

Summary
-------
A cross-process/host Redis-based memoizing decorator in Python for asynchronous
(and sycnhronous) functions in [Twisted](http://twistedmatrix.com)
applications.

Installing
----------
```sh
pip install walnut
```

Examples
--------
Here are some simple examples to give you the idea:

```python
    from twisted.internet import reactor
    from twisted.internet.defer import inlineCallbacks
    import walnut

    @inlineCallbacks
    def main():
        reactor.stop()

    reactor.callWhenRunning(main)
    reactor.run()
```
