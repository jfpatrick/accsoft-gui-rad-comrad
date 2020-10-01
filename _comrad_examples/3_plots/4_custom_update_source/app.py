from qtpy.QtGui import QColor
from comrad import CDisplay, CScrollingCurve, PyDMChannelDataSource, UpdateSource, CChannelData, PointData


class DemoDisplay(CDisplay):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._src = GateDataSource(channel_address='DemoDevice/Acquisition#injection',
                                   data_type_to_emit=PointData,
                                   parent=self.plot)

    def ui_filename(self):
        return 'app.ui'


class GateDataSource(PyDMChannelDataSource):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._output_sources = None

    def value_updated(self, packet):
        if not isinstance(packet, CChannelData):
            return
        if len(packet.value) != 2:
            return
        values = packet.value[0]
        timestamp = packet.value[1]

        # Create output data sources (one per curve), do this dynamically, so that we know what should be
        # the exact amount.
        if self._output_sources is None:
            self.initialize_sources(len(values))

        for val, source in zip(values, self._output_sources):
            if val == 0.0:
                continue
            data = PointData(x=timestamp, y=val)
            source.send_data(data)

    def initialize_sources(self, count: int):
        plot = self.parent()
        self._output_sources = []

        symbols = ['o', 's', 't', 'd', '+']
        colors = ['red', 'yellow', 'green', 'blue', 'white', 'purple']
        color_objects = [QColor(c) for c in colors]

        for idx in range(count):
            source = UpdateSource(parent=plot)
            curve = CScrollingCurve(plot_item=plot.plotItem,
                                    data_model=source,
                                    color=color_objects[idx % len(color_objects)],
                                    symbol=symbols[idx % len(symbols)])
            plot.addItem(curve)
            self._output_sources.append(source)
