walnut
======

![Build Status](https://travis-ci.org/escattone/walnut.svg?branch=master)

Summary
-------
An asynchronous cache decorator in Python for use with
[Twisted](http://twistedmatrix.com).

Installing
----------
```sh
pip install walnut
```
or
```sh
python setup.py install
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
