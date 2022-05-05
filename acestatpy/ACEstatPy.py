'''
Last Modified: 2021-05-11

@author: Jesse M. Barr

Contains:
    -ACEstatPy

ToDo:

'''
# Global
from pydispatch import dispatcher
from queue import Queue
from re import compile as re_compile
from time import sleep, time
from threading import Thread, Timer, Lock
# Local
from .Comms import Serial
from .Testing import Tests, ACEstatTest, TestQueue
from .Utilities import Signal

# Disconnecting from signals is not directly supported, but can still be done
# by using class_instance.signal.disconnect(func)

MessageRE = re_compile(r'([^\[\]]+|\]|\[)')
ERROR_TIMEOUT = 5


class ACEstatPy:
    Definitions = Tests

    def __init__(self):
        self.__delayStart = 0
        # Please note: The next two variables are both necessary, since the
        #   board may not be ready even when not running a test.
        self.__ready = False # Is the board ready for a test
        self.__testInProgress = False # Is the board running a test
        self.__paused = False
        self.__qTimer = None
        self.__eTimer = None
        self.__worker = None
        self.__currentItem = None
        self.__currentTest = None
        self.__buffer = []
        self.__testQueue = TestQueue()
        self.__messageQueue = Queue()
        self.__lock = Lock()

        self.sigReady = Signal("acestatlib_ready")
        self.sigResult = Signal("acestatlib_result")
        self.sigTestStart = Signal("acestatlib_start")
        self.sigTestEnd = Signal("acestatlib_end")
        self.sigError = Signal("acestatlib_error")

        self.Serial = Serial()
        self.Serial.onConnected(self.__startWorker)
        self.Serial.onDisconnected(self.__stopWorker)
        self.Serial.onMessageReceived(self.__messageQueue.put)

    @property
    def ready(self):
        return self.__ready

    @property
    def running(self):
        return self.__testInProgress

    @property
    def paused(self):
        return self.__paused

    @property
    def currentTest(self):
        return self.__currentTest

    @property
    def queue(self):
        return self.__testQueue

    def connect(self, port, baud):
        return self.Serial.connect(port, baud)

    def disconnect(self):
        return self.Serial.disconnect()

    def togglePause(self, pause=None):
        if pause is not None:
            self.__paused = pause
        else:
            self.__paused = not self.__paused
        if self.__paused and self.__qTimer is not None:
            self.__qTimer.cancel()
            self.__qTimer = None
        elif not self.__paused:
            self.__resumeQueue()
        return self.__paused

    def addToQueue(self, id, parameters, **kwargs):
        self.__testQueue.addToQueue(id, parameters, **kwargs)
        self.__resumeQueue()
        return True

    def removeFromQueue(self, index, force=False):
        # force: boolean, if True and index is 0, will cancel a running test.
        #   Otherwise, a running test will be allowed to continue, though
        #   remaining iterations will be set to 0.
        if index == 0 and self.__testInProgress:
            self.__currentItem.cancel()
            if force:
                self.sendCancel()
            return
        self.__testQueue.removeFromQueue(index)

    def clearQueue(self, force=False):
        self.__testQueue.clear()
        self.sendCancel()

    def sendCancel(self):
        if self.Serial.Connected:
            self.Serial.send(chr(27), False)

    ########################
    #    Message Worker    #
    ########################

    def __startWorker(self, *args, **kwargs):
        self.__keepRunning = True
        self.sendCancel()

        def work():
            while self.__keepRunning:
                self.__readQueue()
                sleep(0.01)

        self.__worker = Thread(target=work)
        self.__worker.daemon = True
        self.__worker.start()

    def __stopWorker(self, *args, **kwargs):
        self.__keepRunning = False
        self.__ready = False
        self.__testInProgress = False
        self.sigReady(self.__ready)
        if self.__worker is not None:
            self.__worker.join()
            self.__worker = None

    def __readQueue(self):
        while not self.__messageQueue.empty():
            self.__handleMessage(self.__messageQueue.get())

    def __inputTimeout(self):
        if self.__eTimer is not None:
            self.__eTimer.cancel()
            self.__eTimer = None
            self.sigError("Input timeout, restarting test.")
            self.sendCancel()

    def __resumeQueue(self):
        with self.__lock:
            self.__currentItem = self.__testQueue.nextItem()
            if self.__qTimer is not None:
                self.__qTimer.cancel()
                self.__qTimer = None

            if self.__currentItem is None:
                return
            elif not self.__ready:
                return
            elif self.__paused:
                return

            remaining = self.__currentItem.delay - (time() - self.__delayStart)
            if remaining > 0:
                self.__qTimer = Timer(max(remaining, 0), self.__resumeQueue)
                self.__qTimer.start()
            else:
                self.__currentTest = self.__currentItem.getTest()
                self.Serial.send("{0}".format(self.__currentItem.info.value))
                self.__eTimer = Timer(ERROR_TIMEOUT, self.__inputTimeout)
                self.__eTimer.start()
                self.__ready = False
                self.sigReady(self.__ready)

    def __handleInput(self, id):
        if self.__eTimer is not None:
            self.__eTimer.cancel()
            self.__eTimer = None
        if id.startswith("MAIN"):
            # Clear any remaining parameters/results
            self.__testInProgress = False
            self.__buffer.clear()
            self.__delayStart = time()
            parts = id.split(":")
            if len(parts) < 2 or parts[1] != Tests.VERSION:
                self.sigError("Firmware version does not match definitions.")
                return
            self.__ready = True
            self.sigReady(self.__ready)
            self.__resumeQueue()
        elif self.__currentTest is None or id not in self.__currentTest.parameters:
            self.sigError("Unknown input request: {0}".format(id))
        else:
            value = self.__currentTest.parameters.getFormatted(id)
            self.Serial.send(value)
            self.__eTimer = Timer(ERROR_TIMEOUT, self.__inputTimeout)
            self.__eTimer.start()
            # self.__currentTest.updateStartTime()

    def __handleOutput(self, id, data):
        if self.__currentTest is None:
            return
        testDef = self.__currentTest.info
        if id not in testDef.outputs:
            self.sigError("Unknown output: {0}".format(id))
            return
        output = testDef.outputs[id]
        if output.type == "field":
            field = output.fields[0]
            result = {field.label: self.__handleField(data, field.type)}
        elif output.type == "list":
            fields = data.split(output.separator)
            result = dict([(output.fields[i].label, self.__handleField(
                fields[i], output.fields[i].type)) for i in range(0, len(fields))])
        elif output.type == "matrix":
            colsep = output.col_separator
            rowsep = output.row_separator
            data = data.strip(rowsep)
            matrix = []
            if len(data):
                matrix = list(zip(*[[self.__handleField(f, output.fields[i].type)
                                     for i, f in enumerate(l.split(colsep))] for l in data.split(rowsep)]))
            result = {}
            for c in range(0, len(output.fields)):
                field = output.fields[c]
                result[getattr(field, "label")] = list(matrix[c]) if c < len(matrix) else []
        else:
            self.sigError("Unknown output type: {0}".format(output.type))
            return
        self.__currentTest.results[id] = result
        self.sigResult(id)

    def __handleMessage(self, msg):
        for m in MessageRE.finditer(msg):
            if m.group(0) == '[':
                self.__buffer.append([])
            elif len(self.__buffer):
                # Ignore messages that don't have a start, for now
                if m.group(0) == ']':
                    self.__parseData("".join(self.__buffer.pop()))
                else:
                    self.__buffer[-1].append(m.group(0))

    def __parseData(self, msg):
        if msg.startswith(":"):
            self.__handleInput(msg[1:])
        elif msg.startswith("START"):
            if self.__eTimer is not None:
                self.__eTimer.cancel()
                self.__eTimer = None
            # self.__ready = False
            # self.sigReady(self.__ready)
            self.__currentTest.updateStartTime()
            self.__testInProgress = True
            if msg[6:] != self.__currentItem.id:
                # If the test is wrong, input handling won't work.
                self.sigError("Test mismatch, expected {0}, received {1}".format(
                    self.__currentItem.id, msg[6:]))
                self.sendCancel()
                return
            # self.__currentTest = self.__currentItem.getTest()
            self.sigTestStart(self.__currentTest)
        elif msg.startswith("ERR"):
            self.sigError("Error occurred: {0}".format(msg[4:]))
        elif msg.startswith("END"):
            if msg[4:] != self.__currentTest.id:
                # If the test is wrong, any results are unreliable.
                self.sigError("Test mismatch, expected {0}, received {1}".format(
                    self.__currentTest.id, msg[5:]))
                self.sendCancel()
                return
            if self.__currentItem.export:
                self.__currentTest.export(self.__currentItem.export)
            self.sigTestEnd(self.__currentTest)
            self.__currentItem.decrement()
        else:
            data = msg.split(":", 1)
            try:
                self.__handleOutput(data[0], data[1])
            except Exception as e:
                self.sigError("An error has occurred: {0}".format(e))

    def __handleField(self, data, type):
        if not data:
            return
        if type == "float":
            try:
                return float(data)
            except:
                raise Exception("Invalid float: {0}".format(data))
        elif type == "int":
            try:
                return int(data)
            except:
                raise Exception("Invalid integer: {0}".format(data))
        elif type == "string":
            return str(data)
        else:
            self.sigError("Unknown field type: {0}".format(type))
            return data
            # raise Exception("Unknown field type: {0}".format(type))

    ################
    #    Events    #
    ################

    def onReady(self, func, weak=None):
        # Fires when the board is ready to start a test
        # Passes: Boolean
        if not callable(func):
            return
        self.sigReady.connect(func, weak)

    def onResult(self, func, weak=None):
        # Fires when new data is ready
        # Passes: Output ID String
        if not callable(func):
            return
        self.sigResult.connect(func, weak)

    def onTestStart(self, func, weak=None):
        # Fires when a test has been started
        # Passes: ACEstatTest object
        if not callable(func):
            return
        self.sigTestStart.connect(func, weak)

    def onTestEnd(self, func, weak=None):
        # Indicates a test completed successfully
        # Passes: ACEstatTest object
        if not callable(func):
            return
        self.sigTestEnd.connect(func, weak)

    def onError(self, func, weak=None):
        # Fires when an error is received
        # Passes: Exception or error String
        if not callable(func):
            return
        self.sigError.connect(func, weak)
