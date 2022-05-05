'''
Last Modified: 2022-04-28

@author: Jesse M. Barr

Contains:
    -ACEstatTest
    -ParameterError
    -TestParameters
    -TestResults

ToDo:

Notes:
    -I considered the export function being threaded, but I decided it would be
        a bad idea to handle that behind the scenes. If the user would like,
        they can still implement threading and handle it themselves.

'''
# Global
import csv
from datetime import datetime
from os import path as _path, makedirs
from re import sub
from time import time
from itertools import zip_longest
# Local
from . import Tests

class ACEstatTest(object):
    id = None
    parameters = None
    results = None
    __startTime = None
    __errors = None
    __duration = None

    def __init__(self, id, parameters):
        self.id = id
        if not isinstance(parameters, TestParameters):
            self.parameters = TestParameters(id, parameters)
        else:
            self.parameters = parameters
        self.results = TestResults(id)
        self.__errors = []
        self.__startTime = time()

    @property
    def info(self):
        return Tests[self.id]

    @property
    def startTime(self):
        return self.__startTime

    def updateStartTime(self):
        self.__startTime = time()

    @property
    def errors(self):
        return self.__errors

    def estimateDuration(self):
        if not self.info.timing:
            return None
        if self.__duration is not None:
            return self.__duration
        def repVars(m):
            return self.parameters[m.group(1)]
        try:
            self.__duration = eval(sub(r"\[(\w+)\]", repVars, self.info.timing))
        except:
            return None
        return self.__duration

    def estimateRemaining(self):
        dur = self.estimateDuration()
        if dur is None:
            return None
        return max(0, dur - (time() - self.__startTime))

    def addError(self, err):
        self.__errors.append(err)

    def export(self, path=None):
        dname = "{0}_{1}.csv".format(datetime.fromtimestamp(self.__startTime).strftime('%Y%m%d-%H%M%S'), self.info.name.replace(' ', '-'))
        if not path:
            path = _path.join(".", dname)
        elif _path.isdir(path):
            path = _path.join(path, dname)
        else:
            parts = _path.split(path)
            if parts[0] and not _path.isdir(parts[0]):
                makedirs(parts[0], exist_ok=True)
            if not parts[1]:
                path = _path.join(path, dname)
        if not path.endswith(".csv"):
            path = f"{path}.csv"
        return self.__export(path)

    def __export(self, path):
        with open(path, "w", newline='\n', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Write parameters if they exist
            data = []
            for p in self.parameters:
                param = self.info.parameters[p]
                col = "{0}".format(param.name)
                if hasattr(param, "units"):
                    col += " ({0})".format(param.units)
                if self.info.parameters[p].type == "select":
                    val = param.options[self.parameters[p]]
                else:
                    val = self.parameters[p]
                if not isinstance(val, list):
                    val = [val]
                data.append([col, val])
            if len(data):
                writer.writerow([c[0] for c in data])
                for values in zip_longest(*[d[1] for d in data]):
                    writer.writerow(values)
                writer.writerow([])
            # Write outputs
            for o in self.info.outputs:
                data = []
                for field in self.info.outputs[o].fields:
                    label = getattr(field, "label", "")
                    col = "{0}.{1}".format(o, label)
                    if hasattr(field, "units"):
                        col += " ({0})".format(field.units)
                    val = self.results.get(o, {}).get(label, [])
                    if not isinstance(val, list):
                        val = [val]
                    data.append([col, val])
                writer.writerow([c[0] for c in data])
                for values in zip_longest(*[d[1] for d in data]):
                    writer.writerow(values)
                writer.writerow([])
        return path


class ParameterError(Exception):
    def __init__(self, id, message="Invalid parameter"):
        self.id = id
        self.message = message
        super().__init__(self.message)


class TestParameters(object):
    def __init__(self, id, parameters=None):
        # Validate parameters
        if id not in Tests:
            raise ParameterError(id, "Invalid test ID")
        elif not isinstance(parameters, dict):
            raise Exception("parameters must be instance of dict")
        for item in Tests.get(id).parameters.items():
            if not parameters.get(item[0], False):
                raise ParameterError(id, "Missing parameter")
            elif item[1].type == "select":
                if not parameters[item[0]] in item[1].options:
                    raise ParameterError(item[0], "Invalid select option")
            elif item[1].type == "int":
                try:
                    val = int(parameters.get(item[0]))
                    if val < item[1].min or val > item[1].max:
                        raise ParameterError(item[0], "Value outside valid range")
                except ParameterError as e:
                    raise e
                except Exception as e:
                    raise ParameterError(item[0], "Expected int")

        self.id = id
        self.__parameters = parameters

    def info(self, key=None):
        params = Tests.get(self.id).parameters
        if key is None:
            return params
        elif key not in params:
            raise Exception(f"{key} not in parameters")
        return params[key]

    def get(self, key, *args, **kwargs):
        if "default" in kwargs:
            return self.__parameters.get(key, kwargs.get("default"))
        elif len(args):
            return self.__parameters.get(key, args[0])
        return self.__parameters.get(key)

    def getFormatted(self, key):
        val = self.get(key)
        param = Tests.get(self.id).parameters.get(key)
        negative = False
        if getattr(param, "signed", False):
            negative = int(val) < 0
            val = str(abs(int(val)))
        if hasattr(param, "lpad"):
            val = val.rjust(param.lpad.width, param.lpad.char)
        if hasattr(param, "rpad"):
            val = val.ljust(param.rpad.width, param.rpad.char)
        if getattr(param, "signed", False):
            if negative:
                val = f"-{val}"
            else:
                val = f"+{val}"
        return val

    def __contains__(self, key):
        return key in self.__parameters

    def __getitem__(self, key):
        return self.__parameters.get(key, None)

    def __iter__(self):
        return self.__parameters.__iter__()

    def export(self, path):
        Tests.saveCustomPreset(self.id, self.__parameters, path)


class TestResults(object):
    def __init__(self, id):
        if id not in Tests:
            raise Exception("Invalid test ID")
        self.__results = {}

    def get(self, key, default=None):
        return self.__results.get(key, default)

    def __contains__(self, key):
        return key in self.__results

    def __getitem__(self, key):
        return self.__results.get(key, None)

    def __setitem__(self, key, value):
        self.__results[key] = value

    def __iter__(self):
        return self.__results.__iter__()
