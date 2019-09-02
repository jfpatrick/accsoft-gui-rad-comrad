from pydm import Display
from qtpy.QtWidgets import QHBoxLayout, QLabel


class SecondaryDisplay(Display):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QHBoxLayout()
        self.setLayout(layout)

        label = QLabel()
        label.setText('I am a secondary display!')

        self.layout().addWidget(label)
        layout.addWidget(label)

    def ui_filename(self):
        return None

    def ui_filepath(self):
        return None
