import sys

import xbmc
import xbmcgui


class Debugger(object):
    instance = None

    def __init__(self):
        if not Debugger.instance:
            Debugger.instance = Debugger.__Debugger()
            self.instance.start_debugger()

    def is_in_debug(self):
        return self.instance.is_in_debug

    class __Debugger:
        def __init__(self):
            self.is_initialized = False
            self.is_in_debug = False
            self.debugger_port = 5678

        def start_debugger(self):
            if self.is_in_debug and not self.is_initialized:
                sys.path.append('e:\dev\pysrc')
                import pydevd
#                sys.path.append('/opt/Pycharm/debug-eggs/pycharm-debug.egg')
                xbmc.log("Opening port on localhost:5678 to connect with Pycharm debugger")
                pydevd.settrace('localhost',
                                port=self.debugger_port,
                                stdoutToServer=True,
                                stderrToServer=True,
                                suspend=False)
                self.is_initialized = pydevd.connected
            elif self.is_initialized:
                xbmcgui.Dialog().notification("Debugger",
                                              "Already initialized"
                                              "%s" % self.debugger_port,
                                              sound=False)

        def stop_debugger(self):
            if self.is_in_debug and self.is_initialized:
                import pydevd
                if pydevd.connected:
                    pydevd.stoptrace()
