from comrad import CDisplay


class DemoDisplay(CDisplay):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label.channel = 'japc:///DemoDevice/Acquisition#Demo'
        # Make sure it's more visible, so restyle
        self.label.setStyleSheet('background-color:yellow')

    def ui_filename(self):
        return 'app.ui'
