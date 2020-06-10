from comrad import CDisplay
from generated import Ui_Form


class DemoDisplay(CDisplay):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.setWindowTitle('CLabel example integrating Python code generated '
                            'from Qt Designer file using composition')
        self.ui.label.channel = 'DemoDevice/Acquisition#Demo'
        # Make sure it's more visible, so restyle
        self.ui.label.setStyleSheet('background-color:yellow')
