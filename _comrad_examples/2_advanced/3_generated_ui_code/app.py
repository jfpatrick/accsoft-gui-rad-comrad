from comrad import CDisplay
from generated import Ui_Form


class DemoDisplay(CDisplay, Ui_Form):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.label.channel = 'japc:///DemoDevice/Acquisition#Demo'
        # Make sure it's more visible, so restyle
        self.label.setStyleSheet('background-color:yellow')
