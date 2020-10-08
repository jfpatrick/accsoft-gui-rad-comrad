from qtpy.QtGui import QColor
from comrad import CDisplay, CScrollingCurve, UpdateSource, PointData


class DemoDisplay(CDisplay):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.avg_src = AverageSource(parent=self.plot)
        avg_curve = CScrollingCurve(plot_item=self.plot.plotItem,
                                    data_model=self.avg_src,
                                    color=QColor('red'),
                                    symbol='o')
        self.plot.addItem(avg_curve)

        self.rat_src = RatioSource(parent=self.plot)
        rat_curve = CScrollingCurve(plot_item=self.plot.plotItem,
                                    data_model=self.rat_src,
                                    color=QColor('yellow'),
                                    symbol='s')
        self.plot.addItem(rat_curve)
        self.plot.plotItem.legend.addItem(avg_curve, name='Average')
        self.plot.plotItem.legend.addItem(rat_curve, name='Ratio')
        self.fusion.updateTriggered[tuple].connect(self.avg_src.calc)
        self.fusion.updateTriggered[tuple].connect(self.rat_src.calc)

    def ui_filename(self):
        return 'app.ui'


class AverageSource(UpdateSource):

    def calc(self, values):
        f1, f2, timestamp = values
        avg = (f1 + f2) / 2.0
        data = PointData(x=timestamp, y=avg)
        self.send_data(data)


class RatioSource(UpdateSource):

    def calc(self, values):
        f1, f2, timestamp = values
        rat = 0 if f2 == 0 else (f1 / f2)
        data = PointData(x=timestamp, y=rat)
        self.send_data(data)
