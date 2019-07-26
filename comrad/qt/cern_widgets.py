from pydm.widgets.qtplugin_base import qtplugin_factory
from pydm.widgets import qtplugin_extensions
from PyQt5 import QtGui, QtDesigner, QtCore, QtWidgets
#from accsoft_gui_pyqt_widgets import *


_BASE_EXTENSIONS = [qtplugin_extensions.RulesExtension]


_PROPERTY_SHEET_EXTENSION_IID = 'org.qt-project.Qt.Designer.PropertySheet'
_MEMBER_SHEET_EXTENSION_IID = 'org.qt-project.Qt.Designer.MemberSheet'
_TASK_MENU_EXTENSION_IID = 'org.qt-project.Qt.Designer.TaskMenu'
_CONTAINER_EXTENSION_IID = 'org.qt-project.Qt.Designer.Container'




# TODO: Add new widget plugin wrappers and plugins here