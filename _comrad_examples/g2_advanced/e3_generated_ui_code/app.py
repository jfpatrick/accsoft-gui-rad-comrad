from comrad import CDisplay
from generated import Ui_Form


class DemoDisplay(CDisplay, Ui_Form):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.setWindowTitle('CLabel example integrating Python code generated '
                            'from Qt Designer file using multiple inheritance')
        self.label.channel = 'DemoDevice/Acquisition#Demo'
        # Make sure it's more visible, so restyle
        self.label.setStyleSheet('background-color:yellow')
