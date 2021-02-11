from pyWin import App

class App(App):
    def run(self):
        mainInterface = self.get_interface("main")
        win = self.get_window(mainInterface)
        
        win.open()
    def command_test(self, window, widget):
        widget.set("text", "abc")