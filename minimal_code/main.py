from pyWin import App


class App(App):
    def run(self):
        enLang = self.get_lang("en")
        mainInterface = self.get_interface("main", enLang)
        mainWindow = self.create_window(mainInterface)

        mainWindow.open()
