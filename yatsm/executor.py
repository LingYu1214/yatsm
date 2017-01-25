""" Handler for execution using dask or dask.distributed
"""
from functools import partial
import logging

HAS_CONCURRENT = True
HAS_DISTRIBUTED = True

try:
    from concurrent.futures import (Executor,
                                    Future,
                                    ProcessPoolExecutor,
                                    ThreadPoolExecutor,
                                    as_completed)
except ImportError:
    HAS_CONCURRENT = False
try:
    import distributed
except ImportError:
    HAS_DISTRIBUTED = False

logger = logging.getLogger(__name__)

EXECUTOR_TYPES = ['sync', 'thread', 'process', 'distributed']

EXECUTOR_DEFAULTS = {
    'sync': None,
    'thread': 1,
    'process': 1,
    'distributed': '127.0.0.1:8786'
}


class SyncExecutor(object):

    def submit(self, func, *args, **kwargs):
        future = Future()
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            future.set_exception(e)
        else:
            future.set_result(result)
        return future

    @staticmethod
    def as_completed(futures):
        return as_completed(futures)


class ConcurrentExecutor(object):
    def __init__(self, executor):
        self._executor = executor

    def submit(self, func, *args, **kwargs):
        return self._executor.submit(func, *args, **kwargs)

    @staticmethod
    def as_completed(futures):
        return as_completed(futures)


class DistributedExecutor(object):
    """ concurrent.futures-like dask.distributed executor
    """
    def __init__(self, executor):
        self._executor = executor

    def submit(self, func, *args, **kwargs):
        return self._executor.submit(func, *args, **kwargs)

    @staticmethod
    def as_completed(futures):
        return distributed.as_completed(futures)



def _sync_executor(executor, arg):
    if not HAS_CONCURRENT:
        raise ImportError('You must have Python3 or "futures" package '
                          'installed to use SyncExecutor.')
    return SyncExecutor()


def _concurrent_executor(executor, args):
    if not HAS_CONCURRENT:
        raise ImportError('You must have Python3 or "futures" package '
                          'installed to use ConcurrentExecutor.')
    n = int(args) if args else 1
    return ConcurrentExecutor(ProcessPoolExecutor(n) if executor == 'process'
                              else ThreadPoolExecutor(n))


def _distributed_executor(executor, args):
    if not HAS_DISTRIBUTED:
        raise ImportError('You must have "distributed" installed to use '
                          'DistributedExecutor')

    return DistributedExecutor(distributed.Client(str(args)))


def get_executor(executor, arg):
    """ Click callback for determining executor type
    """
    _map = {
        'sync': _sync_executor,
        'thread': _concurrent_executor,
        'process': _concurrent_executor,
        'distributed': _distributed_executor
    }
    if executor not in _map:
        raise KeyError("Unknown executor '{}'".format(executor))
    try:
        exc = _map[executor](executor, arg)
    except Exception as err:
        logger.exception('Could not setup an executor of type "{}" '
                         'with args "{}": "{}"'
                         .format(executor, arg, err))
        raise
    else:
        return exc