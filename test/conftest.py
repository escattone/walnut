import pytest
from twisted.internet.defer import Deferred
from twisted.internet.protocol import ProcessProtocol

pytest_plugins = "pytest_twisted"


class RedisServerProcessProtocol(ProcessProtocol):

    def __init__(self, ready_deferred, done_deferred):
        self.out = ''
        self.ready_deferred = ready_deferred
        self.done_deferred = done_deferred
        
    def outReceived(self, data):
        self.out += data
        if 'server is now ready to accept connections' in self.out:
            self.call_when_ready()

    def processEnded(self, reason):
        if reason:
            
        self.done_deferred(reason)


@pytest.fixture
def redis_server(request):
    d_ready, d_done = Deferred(), Deferred()
    protocol = RedisServerProcessProtocol(d_ready.callback)

    args = ['redis-server',
            '--port', '6380',
            '--bind', '127.0.0.1',
            '--daemonize', 'no',
            '--databases', '1',
            '--pidfile', '/var/run/redis/redis-walnut-test.pid',
            '--save', '""']
            
    proto = 


    from twisted.internet import reactor
    # Setting "env=None" passes os.environ to the child process.
    proc = reactor.spawnProcess(proto, 'redis-server', args, env=None)



@pytest.fixture
def redis_conn(redis_server):
    from txredisapi import Connection
    return pytest.blockon(Connection(*redis_server))
    
    
daemonize no
port xxxx
save ""
databases 1


flushdb()


