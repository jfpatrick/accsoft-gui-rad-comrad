import os
import pathlib
import pydm
import inspect
from typing import Optional, Dict, Union, cast
from qtpy import uic
from qtpy.QtWidgets import (QWidget, QLabel, QListWidget, QGroupBox, QTableWidget,
                            QTableWidgetItem, QFormLayout, QTabWidget)
from qtpy.QtCore import Qt
from qtpy.QtGui import QIcon
from pydm.tools import ExternalTool


class AboutDialog(QWidget):

    def __init__(self, parent: Optional[QWidget] = None, icon: Optional[QIcon] = None):
        """
        About dialog that shows information about ComRAD framework and its environment.

        Args:
            parent: Parent widget to own the dialog.
            icon: Custom icon to be placed instead of the standard one.
        """
        super().__init__(parent, Qt.Window)

        self.description: QLabel = None
        self.numpy_ver: QLabel = None
        self.pg_ver: QLabel = None
        self.pydm_ver: QLabel = None
        self.widget_ver: QLabel = None
        self.pyjapc_ver: QLabel = None
        self.cmmn_build_ver: QLabel = None
        self.accpy: QLabel = None
        self.accpy_pyqt: QLabel = None
        self.accpy_pyqt_ver: QLabel = None
        self.accpy_ver: QLabel = None
        self.version: QLabel = None
        self.support: QLabel = None
        self.tools_table: QTableWidget = None
        self.plugins_table: QTableWidget = None
        self.contrib_list: QListWidget = None
        self.environment: QGroupBox = None
        self.inca_enabled: QLabel = None
        self.ccda_endpoint: QLabel = None
        self.cmw_env: QLabel = None
        self.cmmn_build_list: QListWidget = None
        self.jvm_list: QListWidget = None
        self.tabs: QTabWidget = None
        self.icon_lbl: QLabel = None

        uic.loadUi(os.path.join(os.path.dirname(__file__), 'about.ui'), self)

        if icon is not None:
            self.icon_lbl.setPixmap(icon.pixmap(self.icon_lbl.maximumSize()))

        from comrad.info import COMRAD_DESCRIPTION, get_versions_info
        versions = get_versions_info()

        self.version.setText(str(self.version.text()).format(version=versions.comrad))
        self.numpy_ver.setText(versions.np)
        self.pydm_ver.setText(versions.pydm)
        self.pg_ver.setText(versions.pg)
        self.widget_ver.setText(versions.widgets)
        self.cmmn_build_ver.setText(versions.cmmn_build)
        self.pyjapc_ver.setText(versions.pyjapc)

        if versions.accpy:
            self.accpy_pyqt.setText('Acc-py PyQt')
            self.accpy.setText('Acc-py Python')
            self.accpy_pyqt_ver.setText(f'{versions.accpy.pyqt} (PyQt v{versions.pyqt}, Qt v{versions.qt})')
            self.accpy_ver.setText(f'{versions.accpy.py} (Python v{versions.python})')
        else:
            self.accpy_pyqt.setText('PyQt')
            self.accpy.setText('Qt')
            self.accpy_pyqt_ver.setText(versions.pyqt)
            self.accpy_ver.setText(versions.qt)
            layout: QFormLayout = self.environment.layout()
            layout.addRow('Python', QLabel(versions.python))

        self.description.setText(COMRAD_DESCRIPTION)
        import comrad
        import re
        author = re.sub(pattern=r'(.*)<([^>]*)>',
                        repl='\g<1>&lt;<a href="mailto:\g<2>">\g<2></a>&gt;',
                        string=comrad.__author__)
        self.support.setText(str(self.support.text()).format(author=author))

        from comrad.qt.application import CApplication
        self.app = cast(CApplication, CApplication.instance())

        self._populate_credits()

        if not isinstance(CApplication.instance(), CApplication):
            # Not a CApplication, must be running this about dialog from somewhere else, e.g. Examples browser
            self.tabs.removeTab(1)  # Remove JAPC tab
            self.tabs.removeTab(1)  # Remove Tools tab
            self.tabs.removeTab(1)  # Remove Data plugins tab
        else:
            self._add_tools_to_list(pydm.tools.ext_tools)
            self._populate_plugin_list()
            self._populate_japc()

    def _add_tools_to_list(self, tools: Union[ExternalTool, Dict[str, ExternalTool]]):
        for name, tool in tools.items():
            if isinstance(tool, dict):
                self._add_tools_to_list(tool)
            else:
                tool_info = tool.get_info()
                name_item = QTableWidgetItem(tool_info.get('name', '-'))
                group_item = QTableWidgetItem(tool_info.get('group', '-'))
                author_item = QTableWidgetItem(tool_info.get('author', '-'))
                file_item = QTableWidgetItem(tool_info.get('file', '-'))
                new_row = self.tools_table.rowCount()
                self.tools_table.insertRow(new_row)
                self.tools_table.setItem(new_row, 0, name_item)
                self.tools_table.setItem(new_row, 1, group_item)
                self.tools_table.setItem(new_row, 2, author_item)
                self.tools_table.setItem(new_row, 3, file_item)

    def _populate_plugin_list(self):
        pydm.data_plugins.initialize_plugins_if_needed()
        for protocol, plugin in pydm.data_plugins.plugin_modules.items():
            protocol_item = QTableWidgetItem(protocol)
            file_item = QTableWidgetItem(inspect.getfile(plugin.__class__))
            new_row = self.plugins_table.rowCount()
            self.plugins_table.insertRow(new_row)
            self.plugins_table.setItem(new_row, 0, protocol_item)
            self.plugins_table.setItem(new_row, 1, file_item)

    def _populate_credits(self):
        self.contrib_list.addItem('PyDM Contributors:')
        self.contrib_list.addItem('------------------')
        import pydm.about_pydm.about
        pydm_contrib = pathlib.Path(pydm.about_pydm.about.__file__).parent
        contrib_file = pathlib.Path(pydm_contrib, 'contributors.txt')
        with open(contrib_file) as f:
            for line in f:
                self.contrib_list.addItem(
                    str(line).strip().replace('@ivany4', 'Ivan Sinkarenko (@ivany4, ivan.sinkarenko@cern.ch)')
                )

    def _populate_japc(self):
        self.inca_enabled.setText('Yes' if self.app.use_inca else 'No')
        self.cmw_env.setText(self.app.cmw_env)
        self.ccda_endpoint.setText(self.app.ccda_endpoint)

        for key, val in self.app.jvm_flags.items():
            self.jvm_list.addItem(f'{key}={val}')

        import pyjapc
        for dep in pyjapc.__cmmnbuild_deps__:
            self.cmmn_build_list.addItem(dep)
