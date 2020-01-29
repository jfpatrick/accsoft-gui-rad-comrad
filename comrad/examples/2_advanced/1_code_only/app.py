from qtpy.QtWidgets import QVBoxLayout
from comrad import CLabel, CDisplay


class DemoDisplay(CDisplay):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QVBoxLayout()
        self.setLayout(layout)

        label = CLabel()
        label.channel = 'japc:///DemoDevice/Acquisition#Demo'

        self.layout().addWidget(label)
        layout.addWidget(label)
