import tkinter as tk
from yaml import safe_load

class InvalidWidgetError(Exception): pass
class ScriptNotFoundError(Exception): pass

def _get_if_exist(dict, key, or_ = None):
    try: return dict[key]
    except KeyError: return or_

def _read_interface_file(path):
    with open(path, "r") as f:
        data = safe_load(f) or {}
    return data


class _Widget:
    nextId = 0
    def __init__(self, app, type, **kwargs):
        self.app = app
        self.id = _Widget.nextId
        _Widget.nextId += 1
        self.type = type
        self.args = kwargs.copy()
        if "action" in kwargs:
            del self.args["action"]
            try:
                getattr(app, "script_"+kwargs["action"])
            except AttributeError:
                raise ScriptNotFoundError(f"Script '{kwargs['action']}' not found")
            self.args["command"] = lambda: getattr(app, "script_"+kwargs["action"])(app.windows[-1], self)
    def delete(self):
        self.app.windows[-1]._delete_widget(self)

class _Interface:
    def __init__(self, app, path):
        data = _read_interface_file(path)
        self.title = _get_if_exist(data, "title", "PyWinApp")
        size = _get_if_exist(data, "size", "500, 300").split(",")
        self.size = (int(size[0].strip()), int(size[1].strip()))
        self.widgets = []
        i = 0
        for w in _get_if_exist(data, "widgets", []):
            try:
                type = w["type"]
                del w["type"]
            except KeyError:
                raise InvalidWidgetError(f"Invalid widget with id {i}")
            self.widgets.append(_Widget(app, type, **w))

class _Window:
    def __init__(self, app, interface, script):
        self.app = app
        if len(app.windows) >= 1:
            self._window = tk.Toplevel(app.windows[0])
        else:
            self._window = tk.Tk()
        self.script = script
        self.title = interface.title
        self.size = interface.size
        self.widgets = interface.widgets

        self._window.title(self.title)
        self._window.geometry(f"{self.size[0]}x{self.size[1]}")
        self._widgets = []
        for w in self.widgets: self._widgets.append(tk.Widget(self._window, w.type, kw=w.args))
        for w in self._widgets: w.pack()

        app.windows.append(self)
    def create_widget(self, type, **kwargs):
        self.widgets.append(_Widget(self.app, type, **kwargs))
        return self.widgets[-1]
    def _delete_widget(self, widget):
        self.widgets.remove(widget)
    def open(self):
        self._window.mainloop()

class App:
    def __init__(self, path):
        self.path = path
        self.windows = []
        self.run()
    def get_interface(self, name):
        return _Interface(self, self.path+"/interface/"+name+".yaml")
    def get_window(self, interface: _Interface):
        return _Window(self, interface, self.script)
    def script(self, win):
        pass
    def run(self):
        pass

if __name__ == "__main__":
    from sys import argv
    from importlib import import_module

    if len(argv) > 1:
        app = import_module(argv[1].replace("/", ".")+".main")
        app.App(argv[1])