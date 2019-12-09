from pydm import Display
from qtpy.QtWidgets import QVBoxLayout
from comrad import CLabel


class DemoDisplay(Display):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QVBoxLayout()
        self.setLayout(layout)

        label = CLabel()
        label.displayFormat = CLabel.Decimal
        label.precisionFromPV = False
        label.precision = 2
        label.channel = 'japc:///DemoDevice/Acquisition#Demo'

        self.layout().addWidget(label)
        layout.addWidget(label)

    def ui_filename(self):
        return None

    def ui_filepath(self):
        return None
