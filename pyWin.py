import tkinter as tk
from yaml import safe_load
from PIL.Image import open as openImg

class InvalidWidgetError(Exception): pass
class ScriptNotFoundError(Exception): pass
class CommandNotFoundError(ScriptNotFoundError): pass

def _get_if_exist(dict, key, or_ = None):
    try: return dict[key]
    except KeyError: return or_

def _read_interface_file(path):
    with open(path, "r") as f:
        data = safe_load(f) or {}
    return data

class _MetaWidget:
    def __init__(self, app, type, **kwargs):
        self.app = app
        self.type = type
        self.args = kwargs

class _Widget:
    nextId = 0
    def __init__(self, window, meta):
        self.window = window
        self.app = meta.app
        self.id = _Widget.nextId
        _Widget.nextId += 1
        self.type = meta.type
        self.args = meta.args.copy()
        self.var = tk.StringVar() if self.type in ["entry"] else None
        if self.var: self.args["textvariable"] = self.var
        self.binds = []
        if "text" in self.args and self.var:
            self.var.set(self.args["text"])
            del self.args["text"]
        if "action" in meta.args:
            del self.args["action"]
            if self.type == "button":
                try:
                    getattr(self.app, "command_"+meta.args["action"])
                except AttributeError:
                    raise CommandNotFoundError(f"Command '{meta.args['action']}' not found")
                self.args["command"] = lambda: getattr(self.app, "command_"+meta.args["action"])(self.window, self)
            elif self.type == "entry":
                try:
                    getattr(self.app, "command_"+meta.args["action"])
                except AttributeError:
                    raise CommandNotFoundError(f"Command '{meta.args['action']}' not found")
                self.binds.append(("Return", lambda e: getattr(self.app, "command_"+meta.args["action"])(self.window, self)))
    def set(self, key, value):
        if key == "text" and self.var:
            self.var.set(value)
            return
        self.args[key] = value

        i = self.window.widgets.index(self)
        self.window._widgets[i].config(**{key: value})
    def get_value(self):
        if self.var: return self.var.get()
    def set_value(self, value):
        if self.var: self.var.set(value)
    def delete(self):
        self.window._delete_widget(self)

class _Interface:
    def __init__(self, app, path):
        data = _read_interface_file(path)
        self.title = _get_if_exist(data, "title", "PyWinApp")
        self.icon = _get_if_exist(data, "icon", None)
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
            self.widgets.append(_MetaWidget(app, type, **w))

class _Window:
    def __init__(self, app, interface):
        self.app = app
        if len(app.windows) >= 1:
            self._window = tk.Toplevel(app.windows[0]._window)
        else:
            self._window = tk.Tk()
        self.interface = interface
        self._title = interface.title
        self._iconPath = self.app.path+"/"+(interface.icon or "icon.ico")
        self._size = interface.size

        self._window.title(self._title)
        try: self._window.iconbitmap(self._iconPath)
        except tk._tkinter.TclError:
            self._iconPath = "./defaultIcon.ico"
            self._window.iconbitmap(self._iconPath)
        self._window.geometry(f"{self._size[0]}x{self._size[1]}")

        self.widgets = []
        for mw in interface.widgets: self.widgets.append(_Widget(self, mw))

        self._widgets = []
        for w in self.widgets:
            self._widgets.append(tk.Widget(self._window, w.type, kw=w.args))
            for b in w.binds:
                self._widgets[-1].bind("<"+b[0]+">", b[1])
        for w in self._widgets: w.pack()

        app.windows.append(self)
    @property
    def title(self):
        return self._title
    @title.setter
    def title(self, title):
        self._title = title
        self._window.title(self._title)
    @title.deleter
    def title(self, title):
        self._title = self.interface.title
        self._window.title(self._title)
    def run(self, script: str = ...):
        if script == Ellipsis:
            getattr(self.app, "script")(self)
        else:
            try:
                getattr(self.app, "script_"+str(script))(self)
            except AttributeError:
               raise ScriptNotFoundError(f"Script '{script}' not found")
    def create_widget(self, type, **kwargs):
        self.widgets.append(_Widget(self, _MetaWidget(self.app, type,  **kwargs)))
        w = self.widgets[-1]
        self._widgets.append(tk.Widget(self._window, w.type, kw=w.args))
        self._widgets[-1].pack()
        return w
    def _delete_widget(self, widget):
        i = self.widgets.index(widget)
        del self.widgets[i]
        self._widgets[i].destroy()
        del self._widgets[i]
    def open(self):
        self._window.mainloop()
    def close(self):
        self._window.destroy()
        del self.app.windows[self.app.windows.index(self)]

class App:
    def __init__(self, path):
        self.path = path
        self.windows = []
        self.run()
    def get_interface(self, name):
        return _Interface(self, self.path+"/interface/"+name+".yaml")
    def create_window(self, interface: _Interface):
        return _Window(self, interface)
    def script(self, win): pass
    def run(self): pass

if __name__ == "__main__":
    from sys import argv
    from importlib import import_module

    if len(argv) > 1:
        app = import_module(argv[1].replace("/", ".")+".main")
        app.App(argv[1])