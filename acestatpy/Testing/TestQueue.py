'''
Last Modified: 2021-04-29

@author: Jesse M. Barr

Contains:
    -TestQueue

Changes:
    -2021-04-29:
        -Added a few safety measures.

ToDo:

'''
# Global
from threading import Lock
# Local
from . import Tests
from .ACEstatTest import ACEstatTest, TestParameters


class TestQueue(object):
    __queue = None
    __lastTestEnd = None
    __lock = None

    class __Item(object):
        def __init__(self, id, parameters, **kwargs):
            # Verify parameters
            self.__id = id
            self.__parameters = TestParameters(id, parameters)
            self.__run_forever = kwargs.get("run_forever", False)
            self.__iterations = int(kwargs.get("iterations", 1))
            self.__start_delay = int(kwargs.get("start_delay", 0))
            self.__inner_delay = int(kwargs.get("inner_delay", 0))
            self.__export = kwargs.get("export", False)

            if self.__iterations < 1:
                raise Exception("A queue item must perform at least 1 iteration")
            if self.__start_delay < 0:
                self.__start_delay = 0
            if self.__inner_delay < 0:
                self.__inner_delay = 0

            self.__delay = self.start_delay
            self.__lock = Lock()

        @property
        def id(self):
            return self.__id

        @property
        def parameters(self):
            return self.__parameters

        @property
        def info(self):
            return Tests.get(self.__id)

        @property
        def delay(self):
            return self.__delay

        @property
        def start_delay(self):
            return self.__start_delay

        @property
        def inner_delay(self):
            return self.__inner_delay

        @property
        def iterations(self):
            return self.__iterations

        @property
        def run_forever(self):
            return self.__run_forever

        @property
        def export(self):
            return self.__export

        def getTest(self):
            return ACEstatTest(self.__id, self.__parameters)

        def decrement(self):
            with self.__lock:
                if not self.__run_forever:
                    self.__iterations -= 1
                # Consider safe to switch to inner delay (between iterations)
                self.__delay = self.__inner_delay
                return self.__iterations

        def cancel(self):
            self.__iterations = 0
            self.__run_forever = False

    def __init__(self):
        self.__queue = []
        self.__lastTestEnd = 0
        self.__lock = Lock()

    def __getitem__(self, index):
        return self.__queue[index]

    def __iter__(self):
        return self.__queue.__iter__()

    def __len__(self):
        return len(self.__queue)

    @property
    def delay(self):
        return self.__delay

    def nextItem(self):
        with self.__lock:
            if not len(self.__queue):
                return None
            elif self.__queue[0].iterations < 1:
                del self.__queue[0]
            if len(self.__queue):
                return self.__queue[0]
            return None

    def addToQueue(self, id, parameters, **kwargs):
        self.__queue.append(self.__Item(id, parameters, **kwargs))

    def removeFromQueue(self, index):
        if 0 <= index < len(self.__queue):
            del self.__queue[index]

    def clear(self):
        self.__queue.clear()
