from comrad import CScrollingPlot, CSlidingPlot, CDisplay
from qtpy.QtCore import Qt
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QGridLayout


class PlotDisplay(CDisplay):

    """
    Example window containing a scrolling and a sliding pointer graph
    containing different plotting items, f.e. curves, bar graphs etc.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Prepare window and layout
        main_layout = QGridLayout()
        self.setLayout(main_layout)
        self.resize(900, 600)
        # Create scrolling and sliding plot
        self.scrolling_plot: CScrollingPlot = CScrollingPlot()
        self.sliding_plot: CSlidingPlot = CSlidingPlot()
        # Add created plots to the windows layout
        main_layout.addWidget(self.scrolling_plot)
        main_layout.addWidget(self.sliding_plot)
        # Configure plots and add curves
        self._configure_scrolling_plot()
        self._configure_sliding_plot()
        self._add_curves_to_scrolling_plot()
        self._add_curves_to_sliding_plot()

    def ui_filename(self):
        return None

    def ui_filepath(self):
        return None

    def _configure_scrolling_plot(self):
        """
        Configure different visual aspects of the scrolling plot.
        API for the axis labels and setting the range for additional
        layers will soon be changed as soon as the new API is available.
        """
        # Set scrolling specific properties
        self.scrolling_plot.fixedXRange = True
        self.scrolling_plot.showTimeProgressLine = False
        self.scrolling_plot.timeSpan = 60.0
        # Set standard plot properties
        self.scrolling_plot.showGridX = True
        self.scrolling_plot.showGridY = True
        self.scrolling_plot.showTopAxis = False
        self.scrolling_plot.showRightAxis = False
        # Add two new layers, give them names and set axis labels
        self.scrolling_plot.add_layer(
            identifier="layer_0",
            axis_label_kwargs={
                "text": "Curve"
            }
        )
        self.scrolling_plot.add_layer(
            identifier="layer_1",
            axis_label_kwargs={
                "text": "Injection Bars"
            }
        )
        self.scrolling_plot.setLabels(left="Bar Graph")
        # Give each layer a separate view range along the y axis
        self.scrolling_plot.setYRange(min=0, max=3)
        self.scrolling_plot.plotItem.get_layer_by_identifier("layer_0").view_box.setYRange(min=-1, max=2)
        self.scrolling_plot.plotItem.get_layer_by_identifier("layer_1").view_box.setYRange(min=-4.5, max=1.5)

    def _configure_sliding_plot(self):
        """
        Configure different visual aspects of the sliding plot.
        API for the axis labels and setting the range for additional
        layers will soon be changed as soon as the new API is available.
        """
        self.sliding_plot.timeSpan = 10.0
        self.sliding_plot.add_layer(
            identifier="layer_0",
            axis_label_kwargs={
                "text": "Triangle Scatter"
            }
        )
        self.sliding_plot.setLabels(left="Dotted Curve")

    def _add_curves_to_scrolling_plot(self):
        """
        Add different data representations to the scrolling plot and
        configure their visual parameters.
        """
        # Add yellow bargraph to default layer
        bars = self.scrolling_plot.addBarGraph(
            data_source="japc://DemoDevice/Acquisition#RandomBar",
            color=QColor("yellow")
        )
        bars.line_width = 1
        # Add red curve in layer_0
        self.scrolling_plot.addCurve(
            data_source="japc://DemoDevice/Acquisition#RandomPoint",
            layer_identifier="layer_0",
            color=QColor("red"),
            line_width=2,
            line_style=Qt.SolidLine,
            symbol=None,
        )
        # Add blue injection bar graph into layer_1
        self.scrolling_plot.addInjectionBar(
            data_source="japc://DemoDevice/Acquisition#RandomInjectionBar",
            layer_identifier="layer_1",
            color=QColor("dodgerblue"),
            line_width=2
        )
        # Add timestamp markers
        self.scrolling_plot.addTimestampMarker(
            data_source="japc://DemoDevice/Acquisition#RandomTimestampMarker",
            line_width=3
        )

    def _add_curves_to_sliding_plot(self):
        """
        Add different data representations to the sliding plot and
        configure their visual parameters.
        """
        # Add yellow dash line
        self.sliding_plot.addCurve(
            data_source="japc://DemoDevice/Acquisition#RandomPoint",
            color=QColor("yellow"),
            line_width=2,
            line_style=Qt.DashLine,
            symbol=None
        )
        # Add red triangles without a line attached to the same field
        self.sliding_plot.addCurve(
            data_source="japc://DemoDevice/Acquisition#RandomPoint",
            layer_identifier="layer_0",
            color=QColor("red"),
            line_style=Qt.NoPen,
            symbol="t",
            symbol_size=10
        )
