'''
Last Modified: 2021-08-17

@author: Jesse M. Barr

Contains:
    -Tests

Changes:
-2021-08-17:
    -Plots are now defined separately from the outputs.
-2021-05-28:
    -Added signed integers.
-2021-05-05:
    -Make Tests a custom object with extra methods for loading additional info.
-2021-04-23:
    -Update package resource loading.
-2021-04-21:
    -Switch from Qt XML parser to a Python standard library parser.
-2020-05-18:
    -Converted techniques, tests, parameters, outputs to objects.
        -Allows us to use object attributes instead of key lookups.
-2020-05-21:
    -"Parameters" is now defined as an OrderedDict.
        -This preserves the order while making the values more easily accessible.
        -"select" type parameters are now defined in an OrderedDict for the same reason.
    -Added preset parsing.
-2020-06-17:
    -Fixed local file being removed on exit.
-2020-06-30:
    -Added version checking.
-2020-08-21:
    -Updated parameter parsing to allow more options for select type.

ToDo:

'''
# Global
from collections import OrderedDict
from json import dump, load
from os.path import basename, splitext
from types import SimpleNamespace as Object
from xml.etree.ElementTree import iterparse
# Local
from ..Utilities import resource_stream

FILENAME = "Tests.xml"

Tests = None


class _Tests(OrderedDict):
  # __definitions = None
  __version = None

  def __init__(self, fpath=None):
    if fpath is None:
      fpath = resource_stream(FILENAME)
    self.importTests(fpath, "")

  @property
  def VERSION(self):
    return self.__version

  def loadCustomPreset(self, fpath):
    with open(fpath, "r") as presetFile:
      data = load(presetFile)
      preset = Object()
      preset.name = f"*{splitext(basename(fpath))[0]}"
      preset.parameters = data["parameters"]
      if data["id"] not in self:
        raise Exception(f"No test with ID: {data['id']}.")
      self[data["id"]].presets[preset.name] = preset

  def saveCustomPreset(self, id, params, fpath):
    if not fpath.endswith(".json"):
      fpath = f"{fpath}.json"
    with open(fpath, 'w') as exportFile:
      dump({
          "id": id,
          "parameters": params
      }, exportFile)
    self.loadCustomPreset(fpath)

  def importTests(self, fpath, prefix="*"):
    tests, version = parseTests(fpath)
    if self.__version is not None and version != self.__version:
      self.clear()
    self.__version = version
    for t in tests:
      t.name = f"{prefix}{t.name}"
      self[t.id] = t

  def copyDefaultTests(self, fpath):
    # Write the packed XML file to disk
    if not fpath.endswith(".xml"):
      fpath = f"{fpath}.xml"
    with open(fpath, "wb") as xml:
      xml.write(resource_stream(FILENAME).read())


class Iterator:
  def __init__(self, iterator):
    self.iterator = iterator
    self.current = None

  def __next__(self):
    try:
      self.current = next(self.iterator)
    except StopIteration:
      self.current = None
    finally:
      return self.current


class VersionError(Exception):
  def __init__(self, version):
    if not version:
      version = "old"
    self.version = version
    self.message = "Expected version {0}, found {1}".format(
        EXPECTED_VERSION, version)
    super().__init__(self.message)


def parseParameter(context):
  event, xml = context.current
  param = Object()
  param.name = xml.get("name")
  param.id = xml.get("id")
  param.type = xml.get("type")

  if param.type == "select":
    param.options = OrderedDict()
  elif param.type == "int":
    param.signed = bool(xml.get("signed", False))
    if xml.get("min", False):
      param.min = int(xml.get("min"))
    if xml.get("max", False):
      param.max = int(xml.get("max"))
  elif param.type == "float":
    param.signed = bool(xml.get("signed", False))
    param.precision = int(xml.get("precision", 1))  # default 1
    if xml.get("min", False):
      param.min = float(xml.get("min"))
    if xml.get("max", False):
      param.max = float(xml.get("max"))
  elif param.type == "number":
    param.signed = bool(xml.get("signed", False))
    param.precision = int(xml.get("precision", 1))  # default 1
    if xml.get("min", False):
      param.min = float(xml.get("min"))
    if xml.get("max", False):
      param.max = float(xml.get("max"))
    if xml.get("float-min", False):
      param.float_min = float(xml.get("float-min"))
    if xml.get("float-max", False):
      param.float_max = float(xml.get("float-max"))
  elif param.type == "static":
    param.value = xml.get("value")

  if xml.get("lpad", False):
    lpad = xml.get("lpad").split("|")
    param.lpad = Object()
    param.lpad.char = lpad[1]
    param.lpad.width = int(lpad[0])
  if xml.get("rpad", False):
    rpad = xml.get("rpad").split("|")
    param.rpad = Object()
    param.rpad.char = rpad[1]
    param.rpad.width = int(rpad[0])

  if xml.get("units", False):
    param.units = xml.get("units")
  while not (event == "end" and xml.tag == "parameter"):
    if event == "end" and param.type == "select" and xml.tag == "option":
      if xml.get("value", False):
        param.options[xml.get("value")] = xml.text
      else:
        val = xml.text
        param.options[val] = val
    event, xml = next(context)
  return param


def parseParameters(context):
  event, xml = context.current
  # Use an array because order matters
  parameters = []
  parameters = OrderedDict()
  while not (event == "end" and xml.tag == "parameters"):
    if event == "start" and xml.tag == "parameter":
      parameters[xml.get("id")] = parseParameter(context)
    event, xml = next(context)
  return parameters


def parseOutput(context):
  event, xml = context.current
  output = Object()
  output.type = "field"
  output.fields = []
  if xml.get("type", False):
    output.type = xml.get("type")
    if output.type == "list" and xml.get("separator", False):
      output.separator = xml.get("separator")
    elif output.type == "matrix":
      if xml.get("col-separator", False):
        output.col_separator = xml.get("col-separator")
      if xml.get("row-separator", False):
        output.row_separator = xml.get("row-separator")
  while not (event == "end" and xml.tag == "output"):
    if event == "start" and xml.tag == "field":
      field = Object()
      field.label = xml.get("label")
      field.type = xml.get("type")
      if xml.get("units", False):
        field.units = xml.get("units")
      output.fields.append(field)
    event, xml = next(context)
  return output


def parseOutputs(context):
  event, xml = context.current
  outputs = OrderedDict()
  while not (event == "end" and xml.tag == "outputs"):
    if event == "start" and xml.tag == "output":
      outputs[xml.get("id")] = parseOutput(context)
    event, xml = next(context)
  return outputs


def parseSeries(context):
  event, xml = context.current
  series = Object()
  series.name = xml.get("name")
  while not (event == "end" and xml.tag == "series"):
    if event == "end":
      axis = Object()
      axis.output = xml.get("output")
      axis.field = xml.get("field")
      setattr(series, xml.tag, axis)
    event, xml = next(context)
  return series


def parsePlot(context):
  event, xml = context.current
  plot = Object()
  plot.title = xml.get("title")
  plot.x_label = xml.get("x-label")
  plot.y_label = xml.get("y-label")
  plot.series = []
  while not (event == "end" and xml.tag == "plot"):
    if event == "start" and xml.tag == "series":
      plot.series.append(parseSeries(context))
    event, xml = next(context)
  return plot


def parsePlots(context):
  event, xml = context.current
  plots = OrderedDict()
  while not (event == "end" and xml.tag == "plots"):
    if event == "start" and xml.tag == "plot":
      plot = parsePlot(context)
      plots[plot.title] = plot
    event, xml = next(context)
  return plots


def parsePreset(context):
  event, xml = context.current
  preset = Object()
  preset.name = xml.get("name")
  parameters = {}
  while not (event == "end" and xml.tag == "preset"):
    if event == "start" and xml.tag == "parameter":
      parameters[xml.get("id")] = xml.get("value")
    event, xml = next(context)
  preset.parameters = parameters
  return preset


def parsePresets(context):
  event, xml = context.current
  presets = OrderedDict()
  while not (event == "end" and xml.tag == "presets"):
    if event == "start" and xml.tag == "preset":
      preset = parsePreset(context)
      presets[preset.name] = preset
    event, xml = next(context)
  return presets


def parseTest(context):
  event, xml = context.current
  test = Object()
  test.name = xml.get("name")
  test.description = ""
  test.value = xml.get("value")
  test.id = xml.get("id")
  test.timing = None
  test.parameters = []
  test.outputs = {}
  test.plots = {}
  test.presets = []
  while not (event == "end" and xml.tag == "test"):
    if event == "start":
      if xml.tag == "parameters":
        test.parameters = parseParameters(context)
      elif xml.tag == "outputs":
        test.outputs = parseOutputs(context)
      elif xml.tag == "plots":
        test.plots = parsePlots(context)
      elif xml.tag == "presets":
        test.presets = parsePresets(context)
      elif xml.tag == "timing":
        test.timing = xml.get("equation")
    elif event == "end":
      if xml.tag == "description":
        test.description = xml.text or ""
    event, xml = next(context)
  xml.clear()
  return test


def parseTests(xmlDoc):
  results = []
  version = None
  # results = _Tests()
  context = iterparse(xmlDoc, events=("start", "end"))

  # turn it into an iterator
  context = Iterator(context)

  # get the root element
  event, xml = next(context)
  root = xml.tag

  while not (event == "end" and xml.tag == root):
    if event == "start" and xml.tag == "techniques":
      version = xml.get("version")
    elif event == "start" and xml.tag == "technique":
      technique = xml.get("name")
      while not (event == "end" and xml.tag == "technique"):
        if event == "start" and xml.tag == "test" and xml.get("enabled", "true").lower() == "true":
          test = parseTest(context)
          test.technique = technique
          results.append(test)
        event, xml = next(context)
      xml.clear()
    event, xml = next(context)
  return results, version


Tests = _Tests()
