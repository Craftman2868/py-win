from pyWin import App

class App(App):
    def run(self):
        mainInterface = self.get_interface("main")
        window = self.create_window(mainInterface)

        window.open()
    def command_valid(self, window, widget):
        command = widget.get_value()
        if command == "exit":
            window.close()
        elif command == "test":
            print(window["result"].type)
            window["result"].set_value("Ca marche !!!")