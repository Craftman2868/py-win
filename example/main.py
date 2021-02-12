from pyWin import App

class App(App):
    def run(self):
        mainInterface = self.get_interface("main")
        window = self.create_window(mainInterface)

        window.open()
    def command_valid(self, window, widget):
        command = widget.get_value()
        window["result"].set("fg", "black")
        widget.clear()
        if command != "":
            if command == "exit":
                window.close()
            elif command == "test":
                window["result"].set_value("Test")
            else:
                window["result"].set("fg", "red")
                window["result"].set_value("Command not found")
        else:
            window["result"].clear()