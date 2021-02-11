from pyWin import App

class App(App):
    def run(self):
        mainInterface = self.get_interface("main")
        window = self.create_window(mainInterface)

        window.open()

        print(self.root)