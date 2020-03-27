from comrad import CDisplay
from qtpy.QtWidgets import QHBoxLayout, QLabel


class SecondaryDisplay(CDisplay):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QHBoxLayout()
        self.setLayout(layout)

        label = QLabel()
        label.setText('I am a secondary display!')

        self.layout().addWidget(label)
        layout.addWidget(label)
