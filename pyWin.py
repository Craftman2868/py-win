import os.path
import sys
import tkinter as tk
import tkinter.messagebox as msgbox

from yaml import safe_load


class InvalidWidgetError(Exception): pass
class InvalidEventError(Exception): pass
class ScriptNotFoundError(Exception): pass
class CommandNotFoundError(ScriptNotFoundError): pass


class _MetaWidget:
    def __init__(self, app, type: str, lang = None, **kwargs):
        self.app = app
        self.type = type.lower()
        self.args = {}
        if lang:
            for k, v in kwargs.items():
                self.args[k] = lang.get(v)
        else:
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
        self.var = tk.StringVar() if self.type in ["entry", "text", "label"] else None
        self.intVar = tk.IntVar() if self.type in ["checkbutton", "scale"] else None
        if self.var:
            self.args["textvariable"] = self.var
        if self.intVar:
            self.args["variable"] = self.intVar
        self.binds = []
        if "from" in meta.args and self.type == "scale":
            del self.args["from"]
            self.args["from_"] = meta.args["from"]
        if "disabled" in meta.args:
            del self.args["disabled"]
            if meta.args["disabled"]:
                self.args["state"] = "disabled"
            else:
                self.args["state"] = "normal"
        if "text" in meta.args and self.var:
            del self.args["text"]
            self.var.set(meta.args["text"])
        if "pos" in meta.args:
            del self.args["pos"]
            pos = meta.args["pos"]
            if type(pos) == str:
                pos = pos.split(" ")
            try:
                posType = pos[0]
                if posType == "pack":
                    if len(pos) == 2:
                        if str(pos[1]).lower() not in ["left", "right", "top", "bottom"]:
                            raise InvalidWidgetError(f"Invalid widget with id {self.id}, invalid position")
                        self.pos = ("pack", str(pos[1]).lower())
                    else:
                        self.pos = ("pack", "top")
                elif posType == "place":
                    self.pos = ("place", pos[1], pos[2])
                elif posType == "grid":
                    self.pos = ("grid", pos[1], pos[2])
                else:
                    raise InvalidWidgetError(f"Invalid widget with id {self.id}, invalid position type '{posType}'")
            except IndexError:
                raise InvalidWidgetError(f"Invalid widget with id {self.id}, invalid position")
        else:
            self.pos = ("pack", "top")
        if "events" in meta.args:
            del self.args["events"]
            for e in meta.args["events"]:
                self.binds.append(e)
        if "action" in meta.args:
            del self.args["action"]
            if self.type in ["button", "scale"]:
                self.args["command"] = lambda: self.window.cmd(meta.args["action"], self)
            elif self.type in ["entry", "text", "label"]:
                self.binds.append(("Return", meta.args["action"]))
        if "tag" in meta.args:
            del self.args["tag"]
            self.tag = str(meta.args["tag"])
            self.window._tags[self.tag] = self

    @property
    def checked(self):
        return bool(self.type == "checkbutton" and self.intVar.get())

    def set(self, key, value):
        if key == "text" and self.var:
            self.var.set(value)
            return
        self.args[key] = value

        self.window._widgets[self.window.widgets.index(self)].config(**{key: value})

    def get_value(self):
        if self.var:
            return self.var.get()
        if self.intVar:
            return self.intVar.get()

    def set_value(self, value):
        if self.var:
            self.var.set(value)
        if self.intVar:
            self.intVar.set(value)

    def insert(self, text):
        if self.var:
            self.set_value(self.get_value() + text)

    def back(self, n=1):
        if self.var:
            self.set_value(self.get_value()[0:-n])

    def clear(self):
        if self.var:
            self.set_value("")

    def focus(self):
        self.window._widgets[self.window.widgets.index(self)].focus()

    def disable(self):
        self.window._widgets[self.window.widgets.index(self)]["state"] = "disabled"

    def enable(self):
        self.window._widgets[self.window.widgets.index(self)]["state"] = "normal"

    def delete(self):
        self.window._delete_widget(self)
        if self.id == _Widget.nextId - 1: _Widget.nextId -= 1
        if self.tag: del self.window._tags[self.tag]


# Code récupéré sur stackoverflow (Ne me juge pas)
class _TextWidget(tk.Text):
    def __init__(self, parent, *args, **kwargs):
        try:
            self._textvariable = kwargs.pop("textvariable")
        except KeyError:
            self._textvariable = None

        tk.Text.__init__(self, parent, *args, **kwargs)

        # if the variable has data in it, use it to initialize
        # the widget
        if self._textvariable is not None:
            self.insert("1.0", self._textvariable.get())

        # this defines an internal proxy which generates a
        # virtual event whenever text is inserted or deleted
        self.tk.eval('''
            proc widget_proxy {widget widget_command args} {

                # call the real tk widget command with the real args
                set result [uplevel [linsert $args 0 $widget_command]]

                # if the contents changed, generate an event we can bind to
                if {([lindex $args 0] in {insert replace delete})} {
                    event generate $widget <<Change>> -when tail
                }
                # return the result from the real widget command
                return $result
            }
            ''')

        # this replaces the underlying widget with the proxy
        self.tk.eval('''
            rename {widget} _{widget}
            interp alias {{}} ::{widget} {{}} widget_proxy {widget} _{widget}
        '''.format(widget=str(self)))

        # set up a binding to update the variable whenever
        # the widget changes
        self.bind("<<Change>>", self._on_widget_change)

        # set up a trace to update the text widget when the
        # variable changes
        if self._textvariable is not None:
            self._textvariable.trace("wu", self._on_var_change)

    def _on_var_change(self, *args):
        '''Change the text widget when the associated textvariable changes'''

        # only change the widget if something actually
        # changed, otherwise we'll get into an endless
        # loop
        text_current = self.get("1.0", "end-1c")
        var_current = self._textvariable.get()
        if text_current != var_current:
            self.delete("1.0", "end")
            self.insert("1.0", var_current)

    def _on_widget_change(self, event=None):
        '''Change the variable when the widget changes'''
        if self._textvariable is not None:
            self._textvariable.set(self.get("1.0", "end-1c"))


class _Lang:
    def __init__(self, path: (str, None)):
        if not path:
            self.data = {}
        else:
            try:
                with open(path, "r") as f:
                    self.data = safe_load(f) or {}
            except FileNotFoundError:
                raise FileNotFoundError(f"No such file or directory: '{path}'")

    def get(self, name):
        if type(name) == str and name[0] == "$" and name[-1] == "$" and name[1:-1] in super().__getattribute__("data"):
            return self[name[1:-1]]
        else:
            return name

    def __getattribute__(self, name):
        if name == "get": return super().__getattribute__("get")
        try:
            return super().__getattribute__("data")[name]
        except KeyError:
            return None

    def __getitem__(self, name):
        try:
            return super().__getattribute__("data")[name]
        except KeyError:
            return None


class _Interface:
    def __init__(self, app, path: str, lang: _Lang = None):
        try:
            with open(path, "r") as f:
                data = safe_load(f) or {}
        except FileNotFoundError:
            raise FileNotFoundError(f"No such file or directory: '{path}'")
        self.path = path
        self.lang = lang or _Lang(None)
        self.title = self.lang.get(data.get("title", "PyWinApp"))
        self.icon = self.lang.get(data.get("icon", None))
        self.events = data.get("events", [])
        size = data.get("size", "200, 200").split(",")
        self.size = (int(size[0].strip()), int(size[1].strip()))
        pos = data.get("pos")
        if pos:
            if pos == "center":
                self.pos = "center"
            elif pos == "auto":
                self.pos = None
            else:
                pos = pos.split(",")
                self.pos = (pos[0].strip(), pos[1].strip())
        else:
            self.pos = None
        self.widgets = []
        i = 0
        for w in data.get("widgets", []):
            try:
                type = w["type"]
                del w["type"]
            except KeyError:
                raise InvalidWidgetError(f"Invalid widget with id {i}")
            self.widgets.append(_MetaWidget(app, type, self.lang, **w))


class _Window:
    def __init__(self, app, interface: _Interface):
        self._tags = {}
        self.app = app
        if len(app.windows) >= 1:
            self._window = tk.Toplevel(app.windows[0]._window)
        else:
            self._window = tk.Tk()
        self.interface = interface
        self.lang = interface.lang
        self._title = interface.title
        self._iconPath = ((self.app.path + "/" + interface.icon) if not interface.icon.startswith(
            "c:/") and not interface.icon.startswith(
            "/") else interface.icon) if interface.icon else self.app.path + "/icon.ico"
        self._size = interface.size
        self._pos = interface.pos

        load = []
        for b in interface.events:
            if type(b) == str:
                b = b.split(" ")
            if b[0] == "load":
                load = b[1:]
                continue
            try:
                self._window.bind("<" + b[0] + ">", lambda e: self.run(b[1]))
            except tk._tkinter.TclError:
                raise InvalidEventError(f"Invalid event '{b[0]}'")

        self._window.title(self._title)
        try:
            self._window.iconbitmap(self._iconPath)
        except tk._tkinter.TclError:
            self._iconPath = os.path.join(sys.path[0], "./defaultIcon.ico")
            self._window.iconbitmap(self._iconPath)
        if self._pos != "center":
            self._window.geometry(
                f"{self._size[0]}x{self._size[1]}" + (f"+{self._pos[0]}+{self._pos[1]}" if self._pos else ""))
        else:
            self._window.geometry(
                f"{self._size[0]}x{self._size[1]}+{int(self._window.winfo_screenwidth() / 2 - self._size[0] / 2)}+{int((self._window.winfo_screenheight() - 20) / 2 - (self._size[1] + 10) / 2)}")

        self.widgets = []
        for mw in interface.widgets:
            self.widgets.append(_Widget(self, mw))

        self._widgets = []
        for w in self.widgets:
            try:
                if w.type == "text":
                    self._widgets.append(_TextWidget(self._window, **w.args))
                else:
                    self._widgets.append(tk.Widget(self._window, w.type, kw=w.args))
            except tk._tkinter.TclError as e:
                if e.args[0].startswith("invalid command name"):
                    raise InvalidWidgetError(f"Invalid widget with id {w.id}, type '{w.type}' not found")
                else:
                    raise InvalidWidgetError(
                        f"Invalid widget with id {w.id}, " + e.args[0].replace('"', "'").replace("'-", "'"))
            _w = self._widgets[-1]
            for b in w.binds:
                if type(b) == str:
                    b = b.split(" ")
                try:
                    self._widgets[-1].bind("<" + b[0] + ">", lambda _, w=w: self.cmd(b[1], w))
                except tk._tkinter.TclError:
                    raise InvalidEventError(f"Invalid event '{b[0]}'")
        for w, _w in zip(self.widgets, self._widgets):
            if w.pos[0] == "pack":
                _w.pack(side=w.pos[1])
            elif w.pos[0] == "place":
                _w.place(x=w.pos[1], y=w.pos[2])
            elif w.pos[0] == "grid":
                _w.grid(row=w.pos[1], column=w.pos[2])

        app.windows.append(self)

        self.run()

        for s in load:
            self.run(s)

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, title):
        self._title = self.lang.get(title)
        self._window.title(self._title)

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self, size):
        self._size = size
        self._window.geometry(f"{self._size[0]}x{self._size[1]}")

    @property
    def pos(self):
        return self._pos

    @pos.setter
    def pos(self, pos):
        if pos == "auto":
            pos = None
        self._pos = pos
        if self.pos:
            if self._pos != "center":
                self._window.geometry(
                    f"{self._size[0]}x{self._size[1]}" + (f"+{self._pos[0]}+{self._pos[1]}" if self._pos else ""))
            else:
                self._window.geometry(
                    f"{self._size[0]}x{self._size[1]}+{int(self._window.winfo_screenwidth() / 2 - self._size[0] / 2)}+{int((self._window.winfo_screenheight() - 20) / 2 - (self._size[1] + 10) / 2)}")

    @property
    def icon(self):
        return self._iconPath

    @icon.setter
    def icon(self, iconPath):
        if iconPath:
            iconPath = self.lang.get(iconPath)
        self._iconPath = (
            (self.app.path + "/" + iconPath) if not iconPath.startswith("c:/") and not iconPath.startswith(
                "/") else iconPath) if iconPath else self.app.path + "/icon.ico"
        try:
            self._window.iconbitmap(self._iconPath)
        except tk._tkinter.TclError:
            self._iconPath = os.path.join(sys.path[0], "./defaultIcon.ico")
            self._window.iconbitmap(self._iconPath)

    def set_lang(self, lang: _Lang = None, callback=None):
        self.interface = interface = _Interface(self.app, self.interface.path, lang)

        self.lang = interface.lang
        self._title = interface.title
        self._iconPath = ((self.app.path + "/" + interface.icon) if not interface.icon.startswith(
            "c:/") and not interface.icon.startswith(
            "/") else interface.icon) if interface.icon else self.app.path + "/icon.ico"

        self._window.title(self._title)
        try:
            self._window.iconbitmap(self._iconPath)
        except tk._tkinter.TclError:
            self._iconPath = os.path.join(sys.path[0], "./defaultIcon.ico")
            self._window.iconbitmap(self._iconPath)

        self.widgets = []
        for mw in interface.widgets:
            self.widgets.append(_Widget(self, mw))

        for _w in self._widgets:
            _w.destroy()

        self._widgets = []
        for w in self.widgets:
            try:
                if w.type == "text":
                    self._widgets.append(_TextWidget(self._window, **w.args))
                else:
                    self._widgets.append(tk.Widget(self._window, w.type, kw=w.args))
            except tk._tkinter.TclError as e:
                if e.args[0].startswith("invalid command name"):
                    raise InvalidWidgetError(f"Invalid widget with id {w.id}, type '{w.type}' not found")
                else:
                    raise InvalidWidgetError(f"Invalid widget with id {w.id}, " + e.args[0].replace('"', "'"))
            _w = self._widgets[-1]
            for b in w.binds:
                if type(b) == str:
                    b = b.split(" ")
                try:
                    self._widgets[-1].bind("<" + b[0] + ">", lambda e, w=w: self.cmd(b[1], w))
                except tk._tkinter.TclError:
                    raise InvalidEventError(f"Invalid event '{b[0]}'")
        for w, _w in zip(self.widgets, self._widgets):
            if w.pos[0] == "pack":
                _w.pack(side=w.pos[1])
            elif w.pos[0] == "place":
                _w.place(x=w.pos[1], y=w.pos[2])
            elif w.pos[0] == "grid":
                _w.grid(row=w.pos[1], column=w.pos[2])
        if callback: callback()

    def run(self, script: str = ...):
        if script == Ellipsis:
            self.app.get_script()(self)
        else:
            self.app.get_script(script)(self)

    def cmd(self, command: str, widget: _Widget):
        self.app.get_command(command)(self, widget)

    def create_widget(self, type: str, **kwargs):
        self.widgets.append(_Widget(self, _MetaWidget(self.app, type, **kwargs)))
        w = self.widgets[-1]
        self._widgets.append(tk.Widget(self._window, w.type, kw=w.args))
        if w.pos[0] == "pack":
            print(self.widgets[-1])
            self._widgets[-1].pack(side=w.pos[1])
        elif w.pos[0] == "place":
            self._widgets[-1].place(x=w.pos[1], y=w.pos[2])
        elif w.pos[0] == "grid":
            self._widgets[-1].grid(row=w.pos[1], column=w.pos[2])
        return w

    def _delete_widget(self, widget: _Widget):
        i = self.widgets.index(widget)
        del self.widgets[i]
        self._widgets[i].destroy()
        del self._widgets[i]

    def open(self):
        self._window.focus()
        self._window.mainloop()

    def close(self):
        del self.app.windows[self.app.windows.index(self)]
        self._window.destroy()

    def __getitem__(self, item):
        if type(item) == str:
            return self._tags[item]
        else:
            return self.widgets[item]


class App:
    def __init__(self, path: str):
        self.path = path
        self.windows = []
        self.run()

    @property
    def root(self):
        return self.windows[0] if len(self.windows) >= 1 else None

    def get_lang(self, name: str):
        return _Lang(self.path + "/lang/" + name + ".yaml")

    def get_interface(self, name: str, lang: _Lang = None):
        return _Interface(self, self.path + "/interface/" + name + ".yaml", lang)

    def create_window(self, interface: _Interface):
        return _Window(self, interface)

    def get_command(self, command: str):
        try:
            return getattr(self, "command_" + command)
        except AttributeError:
            raise CommandNotFoundError(f"Command '{command}' not found")

    def get_script(self, script: str = ...):
        if script == Ellipsis: return getattr(self, "script")
        try:
            return getattr(self, "script_" + script)
        except AttributeError:
            raise ScriptNotFoundError(f"Script '{script}' not found")

    def script(self, win: _Window):
        pass

    def run(self):
        pass

    def error(self, message: str, title: str = ...):
        if title == Ellipsis:
            title = self.path.split("/")[-1]
        return msgbox.showerror(title, message)

    def info(self, message: str, title: str = ...):
        if title == Ellipsis:
            title = self.path.split("/")[-1]
        return msgbox.showinfo(title, message)

    def warning(self, message: str, title: str = ...):
        if title == Ellipsis:
            title = self.path.split("/")[-1]
        return msgbox.showwarning(title, message)

    def yesno(self, question: str, title: str = ...):
        if title == Ellipsis:
            title = self.path.split("/")[-1]
        return msgbox.askyesno(title, question)

    def okcancel(self, message: str, title: str = ...):
        if title == Ellipsis:
            title = self.path.split("/")[-1]
        return msgbox.askokcancel(title, message)

    def retrycancel(self, message: str, title: str = ...):
        if title == Ellipsis:
            title = self.path.split("/")[-1]
        return msgbox.askretrycancel(title, message)

    def yesnocancel(self, question: str, title: str = ...):
        if title == Ellipsis:
            title = self.path.split("/")[-1]
        return msgbox.askyesnocancel(title, question)


if __name__ == "__main__":
    from importlib.machinery import SourceFileLoader

    if len(sys.argv) > 1:
        if sys.argv[1][-1] == "/":
            sys.argv[1] = sys.argv[1][0:-1]
        try:
            app = SourceFileLoader("main.App", sys.argv[1] + "/main.py").load_module()
        except FileNotFoundError:
            raise FileNotFoundError(f"No such file or directory: '{sys.argv[1] + '/main.py'}'")
        app.App(sys.argv[1])
    else:
        print("Usage: python pyWin.py <folderPath>")
