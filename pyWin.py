from tkinter import Tk
from yaml import load

class InvalidWidgetError(Exception): pass

def _get_if_exist(dict, key, or_ = None):
    try: return dict[key]
    except KeyError: return or_

def _read_interface_file(path):
    with open(path, "r") as f:
        data = load(f)
    return data

class Widget:
    BUTTON = 0
    ENTRY = 1
    TEXT = 2

class _Widget:
    def __init__(self, type, **kwargs):
        self.type = type
        self.pos = _get_if_exist(kwargs, "pos")
        if self.type == Widget.BUTTON:
            pass

class _Interface:
    def __init__(self, app, path):
        data = _read_interface_file(path)
        self.title = _get_if_exist(data, "title", "PyWinApp")
        self.size = _get_if_exist(data, "title", "500, 300").split(" ")
        self.size = (int(size[0].strip()), int(size[1].strip()))
        self.widgets = []
        i = 0
        for w in _get_if_exist(data, "widgets", []):
            try:
                self.widgets.append(w["type"])
            except KeyError:
                raise InvalidWidgetError(f"Invalid widget with id {i}")

class _Window:
    def __init__(self, interface, script):
        self._window = Tk()
        self.script = script

class App:
    def __init__(self):
        self.windows = []
    def get_interface(self, name):
        return _Interface(self, "interface/"+name+".yaml")
    def open(self, interface: _Interface):
        self.windows.append(_Window(interface, self.script))
    def script(self, win):
        pass