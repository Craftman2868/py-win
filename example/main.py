from pyWin import App

class App(App):
    def run(self):
        fr = self.get_lang("fr")
        mainInterface = self.get_interface("main", fr)
        window = self.create_window(mainInterface)
        window["command"].focus()

        window.open()
    def command_valid(self, window, widget):
        command = window["command"].get_value()
        window["result"].set("bg", "SystemButtonFace")
        window["result"].set("fg", "black")
        window["command"].clear()
        if command != "":
            if command == "exit":
                window.close()
            elif command == "test":
                window["result"].set_value("Test")
            elif command == "lang":
                window.set_lang()
            elif command.startswith("lang "):
                window.set_lang(self.get_lang(command[5:] or None)) 
            else:
                window["result"].set("bg", "red")
                window["result"].set("fg", "white")
                window["result"].set_value("Command not found")
        else:
            window["result"].clear()