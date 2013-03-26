# -*- test-case-name: twisted.trial._dist.test.test_workertrial -*-
#
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Implementation of C{AMP} worker commands, and main executable entry point for
the workers.

@since: 12.3
"""

import sys
import os
import errno

if 'TRIAL_PYTHONPATH' in os.environ:
    sys.path[:] = os.environ['TRIAL_PYTHONPATH'].split(os.pathsep)

from twisted.internet.protocol import FileWrapper
from twisted.python.log import startLoggingWithObserver, textFromEventDict
from twisted.trial._dist.options import WorkerOptions
from twisted.trial._dist import _WORKER_AMP_STDIN, _WORKER_AMP_STDOUT



class WorkerLogObserver(object):
    """
    A log observer that forward its output to a C{AMP} protocol.
    """

    def __init__(self, protocol):
        """
        @param protocol: a connected C{AMP} protocol instance.
        @type protocol: C{AMP}
        """
        self.protocol = protocol


    def emit(self, eventDict):
        """
        Produce a log output.
        """
        from twisted.trial._dist import managercommands
        text = textFromEventDict(eventDict)
        if text is None:
            return
        self.protocol.callRemote(managercommands.TestWrite, out=text)



def main(_fdopen=os.fdopen):
    """
    Main function to be run if __name__ == "__main__".

    @param _fdopen: If specified, the function to use in place of C{os.fdopen}.
    @param _fdopen: C{callable}
    """
    config = WorkerOptions()
    config.parseOptions()

    from twisted.trial._dist.worker import WorkerProtocol
    workerProtocol = WorkerProtocol(config['force-gc'])

    protocolIn = _fdopen(_WORKER_AMP_STDIN)
    protocolOut = _fdopen(_WORKER_AMP_STDOUT, 'w')
    workerProtocol.makeConnection(FileWrapper(protocolOut))

    observer = WorkerLogObserver(workerProtocol)
    startLoggingWithObserver(observer.emit, False)

    while True:
        try:
            r = protocolIn.read(1)
        except IOError, e:
            if e.args[0] == errno.EINTR:
                sys.exc_clear()
                continue
            else:
                raise
        if r == '':
            break
        else:
            workerProtocol.dataReceived(r)
            protocolOut.flush()
            sys.stdout.flush()
            sys.stderr.flush()

    if config.tracer:
        sys.settrace(None)
        results = config.tracer.results()
        results.write_results(show_missing=True, summary=False,
                              coverdir=config.coverdir().path)



if __name__ == '__main__':
    main()
