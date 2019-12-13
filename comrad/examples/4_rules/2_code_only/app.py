from pydm import Display
from qtpy.QtWidgets import QVBoxLayout
from comrad import CLabel
from comrad.rules import CNumRangeRule


class DemoDisplay(Display):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QVBoxLayout()
        self.setLayout(layout)

        label = CLabel()
        label.displayFormat = CLabel.Decimal
        label.precision = 2
        label.channel = 'japc:///DemoDevice/Acquisition#Demo'
        label.rules = [
            CNumRangeRule(name='Demo colors',
                          prop=CNumRangeRule.Property.COLOR,
                          ranges=[CNumRangeRule.Range(min_val=0.5, max_val=1.01, prop_val='#FF0000')])
        ]

        self.layout().addWidget(label)
        layout.addWidget(label)

    def ui_filename(self):
        return None

    def ui_filepath(self):
        return None
