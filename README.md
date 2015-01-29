walnut
======

An asynchronous cache for [Twisted](http://twistedmatrix.com)-based projects.

The documentation is really bare-bones at the moment but I will improve it
as I have time.  There is a fairly thorough set of unit tests for all of the
code here, but that doesn't mean I haven't forgotten something, so let me know
if you find something amiss.  Although I've only tested it on Ubuntu with Python
2.7, it should run with at least Python2.5 on any system, including Windows
(famous last words!).  Again, let me know if that's not the case.  Cheers!

Pool
----

*twisted_toolbox.process.pool.Pool* provides the ability to run Python
callables asynchronously within a pool of processes.  Here's a very
simple example to give you the idea:

```python
    from twisted.internet import reactor
    from twisted.internet.defer import inlineCallbacks
    from twisted_toolbox.process.pool import Pool
    
    pool = Pool()
    
    @inlineCallbacks
    def main():
        result = yield pool.apply('glob.glob', '*.pdf')
        print repr(result)
        reactor.stop()
        
    reactor.callWhenRunning(main)
    reactor.run()
```

fifo
----

*twisted_toolbox.fifo.fifo* is a decorator for asynchronous callables that
guarantees that the instances of twisted.internet.defer.Deferred from successive
calls will callback in the order requested, not the order in which the deferred
results arrive.

