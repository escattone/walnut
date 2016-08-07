walnut
======

.. figure:: https://travis-ci.org/escattone/walnut.svg?branch=master
   :alt: Build Status

   Build Status
Summary
-------

A cross-process/cross-host Redis-based memoizing decorator in Python for
asynchronous (and sycnhronous) functions in Twisted
`Twisted <http://twistedmatrix.com>`__ applications.

Installing
----------

.. code:: sh

    pip install walnut

Examples
--------

Here are some simple examples to give you the idea:

.. code:: python

        from twisted.internet import reactor
        from twisted.internet.defer import inlineCallbacks
        import walnut

        @inlineCallbacks
        def main():
            reactor.stop()

        reactor.callWhenRunning(main)
        reactor.run()
