from pyWin import App

class MyApp(App):
    def script(self, window):
        pass

app = MyApp()
mainInterface = app.get_interface("main")