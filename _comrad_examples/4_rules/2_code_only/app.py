from qtpy.QtWidgets import QHBoxLayout
from comrad import CLabel, CDisplay, CLed
from comrad.rules import CNumRangeRule


class DemoDisplay(CDisplay):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle('Rules example implemented fully in code')

        layout = QHBoxLayout()
        self.setLayout(layout)

        label = CLabel()
        label.displayFormat = CLabel.Decimal
        label.precision = 2
        label.channel = 'DemoDevice/Acquisition#Demo'
        label.rules = [
            CNumRangeRule(name='Demo colors',
                          prop=CNumRangeRule.Property.COLOR,
                          ranges=[CNumRangeRule.Range(min_val=0.5, max_val=1.01, prop_val='#FF0000')]),
        ]

        self.layout().addWidget(label)
        layout.addWidget(label)

        led = CLed()
        led.channel = label.channel
        led.rules = label.rules
        layout.addWidget(led)
