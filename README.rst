walnut
======

.. figure:: https://travis-ci.org/escattone/walnut.svg?branch=master
   :alt: Build Status

   Build Status
Summary
-------

An asynchronous cache decorator in Python for use with
`Twisted <http://twistedmatrix.com>`__.

Installing
----------

.. code:: sh

    pip install walnut

or

.. code:: sh

    python setup.py install

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

