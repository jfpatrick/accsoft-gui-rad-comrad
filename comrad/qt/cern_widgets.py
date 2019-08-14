import pyqtgraph as pg
from .widgets import *
from accsoft_gui_pyqt_widgets import graph as accgraph
from pydm.widgets.base import PyDMPrimitiveWidget
from qtpy.QtWidgets import QWidget


# For the future, if we implement other types of Qt Designer extensions
# _PROPERTY_SHEET_EXTENSION_IID = 'org.qt-project.Qt.Designer.PropertySheet'
# _MEMBER_SHEET_EXTENSION_IID = 'org.qt-project.Qt.Designer.MemberSheet'
# _TASK_MENU_EXTENSION_IID = 'org.qt-project.Qt.Designer.TaskMenu'
# _CONTAINER_EXTENSION_IID = 'org.qt-project.Qt.Designer.Container'


class CAccPlot(accgraph.ExPlotWidget, PyDMPrimitiveWidget):

    def __init__(self,
                 parent: QWidget = None,
                 background: str = 'default',
                 config: accgraph.ExPlotWidgetConfig = accgraph.ExPlotWidgetConfig(),
                 axis_items: Optional[Dict[str, pg.AxisItem]] = {},
                 timing_source: Optional[accgraph.UpdateSource] = None,
                 **plotitem_kwargs):
        accgraph.ExPlotWidget.__init__(self,
                                       parent=parent,
                                       background=background,
                                       config=config,
                                       axis_items=axis_items,
                                       timing_source=timing_source,
                                       **plotitem_kwargs)
        PyDMPrimitiveWidget.__init__(self)