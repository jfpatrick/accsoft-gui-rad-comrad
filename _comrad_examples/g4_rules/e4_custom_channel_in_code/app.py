from qtpy.QtWidgets import QFormLayout, QGridLayout, QSizePolicy
from comrad import CLabel, CDisplay, CLed, CContextFrame
from comrad.rules import CNumRangeRule


class DemoDisplay(CDisplay):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle('Simple color rules with custom channels in code example')

        layout = QGridLayout()
        self.setLayout(layout)

        label = CLabel(init_channel='DemoDevice/Acquisition#Demo')
        label.displayFormat = CLabel.Decimal
        label.precision = 2
        label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
        label.rules = [
            CNumRangeRule(name='Demo colors',
                          prop=CNumRangeRule.Property.COLOR,
                          channel='DemoDevice/Color#Demo',
                          ranges=[CNumRangeRule.Range(min_val=0.5, max_val=1.01, prop_val='#FF0000')]),
        ]

        layout.addWidget(label, 0, 0)

        led = CLed()
        led.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
        led.rules = [
            CNumRangeRule(name='Demo colors',
                          prop=CNumRangeRule.Property.COLOR,
                          channel='DemoDevice/ColorMultiplexed#Demo',
                          selector='SAMPLE.USER.MD1',
                          ranges=[CNumRangeRule.Range(min_val=0.5, max_val=1.01, prop_val='#FF0000')]),
        ]
        layout.addWidget(led, 0, 1)

        left_bottom = QFormLayout()
        label = CLabel(init_channel='DemoDevice/Color#Demo')
        label.displayFormat = CLabel.Decimal
        label.precision = 2
        left_bottom.addRow('DemoDevice/Color#Demo:', label)
        layout.addLayout(left_bottom, 1, 0)

        right_bottom = CContextFrame()
        right_bottom.selector = 'SAMPLE.USER.MD1'
        right_bottom_form = QFormLayout()
        right_bottom.setLayout(right_bottom_form)
        label = CLabel(init_channel='DemoDevice/ColorMultiplexed#Demo')
        label.displayFormat = CLabel.Decimal
        label.precision = 2
        right_bottom_form.addRow('DemoDevice/ColorMultiplexed#Demo:\n[SAMPLE.USER.MD1]', label)
        layout.addWidget(right_bottom, 1, 1)
