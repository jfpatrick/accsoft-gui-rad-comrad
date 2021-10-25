import logging
import pytest
from pathlib import Path
from _comrad.package.import_scanning import (scan_py_imports, scan_ui_imports, ScannedImport, normalize_imports,
                                             scan_imports)
from _comrad_examples import examples


@pytest.fixture
def ensure_acc_py(monkeypatch):

    def wrapper(active: bool):
        if active:
            monkeypatch.setenv('ACC_PYTHON_ACTIVE', '1')
        else:
            monkeypatch.delenv('ACC_PYTHON_ACTIVE', raising=False)

    return wrapper


@pytest.mark.parametrize('relative_loc', [None, 'relative_dir', 'relative_dir', 'relative_dir/relative_subdir'])
@pytest.mark.parametrize('code,expected_imports', [
    ('', []),
    ('print("Nothing important")', []),
    ('import pytest', ['pytest']),
    ('import comrad', ['comrad']),
    ('import numpy as np', ['numpy']),
    ('import _comrad', ['_comrad']),
    ('from . import sibling', []),
    ('from .. import cousin', []),
    ('from .sibling import anything', []),
    ('from comrad import CDisplay', ['comrad']),
    ('from comrad import CDisplay as ComradDisplay', ['comrad']),
    ('from comrad.widgets import CDisplay', ['comrad.widgets']),
    ("""from comrad.widgets import CDisplay
import logging
from pytest import mark""", ['comrad.widgets', 'logging', 'pytest']),
    ("""from comrad import CDisplay

class MyDisplay(CDisplay):
    pass
""", ['comrad']),
    ("""from comrad import CDisplay

class MyDisplay(CDisplay):
    import pytest
""", ['comrad', 'pytest']),
    ("""from comrad import CDisplay

class MyDisplay(CDisplay):
    from .sibling import anything""", ['comrad']),
    ("""import logging
# import anything_else
""", ['logging']),
])
def test_scan_py_imports_succeed(tmp_path: Path, code, expected_imports, relative_loc):
    code_file = tmp_path / 'test_file.py'
    code_file.write_text(code)
    expected_pkgs = {ScannedImport.create(pkg=i, relative_loc=relative_loc) for i in expected_imports}
    assert scan_py_imports(code_file, relative_loc=relative_loc) == expected_pkgs


@pytest.mark.parametrize('relative_loc', [None, '', 'relative_dir', 'relative_dir/relative_subdir'])
@pytest.mark.parametrize('code', [
    'import',
    'import .sibling.stuff',
    'from import stuff',
    """from comrad import CDisplay

class MyDisplay(CDisplay):""",
])
def test_scan_py_imports_fails(tmp_path: Path, code, relative_loc):
    code_file = tmp_path / 'test_file.py'
    code_file.write_text(code)
    with pytest.raises(SyntaxError):
        scan_py_imports(code_file, relative_loc=relative_loc)


@pytest.mark.parametrize('relative_loc', [None, '', 'relative_dir', 'relative_dir/relative_subdir'])
@pytest.mark.parametrize('xml,expected_imports', [
    ("""<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <widget class="QWidget" name="Form" />
</ui>""", []),
    ("""<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <widget class="QWidget" name="Form" />
 <customwidgets>
  <customwidget>
   <class>MyLabel</class>
   <extends>QLabel</extends>
   <header>custom_widget</header>
  </customwidget>
  <customwidget>
   <class>AnotherLabel</class>
   <extends>QLabel</extends>
   <header>subdir/another_widget.h</header>
  </customwidget>
  <customwidget>
   <class>ThirdLabel</class>
   <extends>QLabel</extends>
   <header>subdir.another_widget</header>
  </customwidget>
  <customwidget>
   <class>ForthLabel</class>
   <extends>QLabel</extends>
   <header>subdir/subdir2/another_widget.h</header>
  </customwidget>
  <customwidget>
   <class>FifthLabel</class>
   <extends>QLabel</extends>
   <header>subdir/subdir2/another_widget</header>
  </customwidget>
  <customwidget>
   <class>SixthLabel</class>
   <extends>QLabel</extends>
   <header>subdir.subdir2.another_widget</header>
  </customwidget>
 </customwidgets>
</ui>""", ['custom_widget', 'subdir.another_widget', 'subdir.subdir2.another_widget']),
    ("""<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>Form</class>
 <widget class="QWidget" name="Form">
  <property name="geometry">
   <rect>
    <x>0</x>
    <y>0</y>
    <width>294</width>
    <height>87</height>
   </rect>
  </property>
  <property name="windowTitle">
   <string>Client-side transformations with Python</string>
  </property>
  <layout class="QHBoxLayout" name="horizontalLayout">
   <item>
    <widget class="CLabel" name="CLabel">
     <property name="channel" stdset="0">
      <string notr="true">DemoDevice/Acquisition#Demo</string>
     </property>
     <property name="valueTransformation">
      <string notr="true">output(f'&lt;&lt;{new_val}&gt;&gt; - from {__file__}')</string>
     </property>
    </widget>
   </item>
  </layout>
 </widget>
 <customwidgets>
  <customwidget>
   <class>PyDMLabel</class>
   <extends>QLabel</extends>
   <header>pydm.widgets.label</header>
  </customwidget>
  <customwidget>
   <class>CLabel</class>
   <extends>PyDMLabel</extends>
   <header>comrad.widgets.indicators</header>
  </customwidget>
 </customwidgets>
 <resources/>
 <connections/>
</ui>""", ['pydm.widgets.label', 'comrad.widgets.indicators']),
    ("""<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <widget class="CLabel" name="CLabel_3">
  <property name="valueTransformation">
   <string notr="true">from imported import decorate
output(decorate(new_val))</string>
  </property>
 </widget>
 <customwidgets>
  <customwidget>
   <class>PyDMLabel</class>
   <extends>QLabel</extends>
   <header>pydm.widgets.label</header>
  </customwidget>
  <customwidget>
   <class>CLabel</class>
   <extends>PyDMLabel</extends>
   <header>comrad.widgets.indicators</header>
  </customwidget>
 </customwidgets>
 <resources/>
 <connections/>
</ui>""", ['imported', 'comrad.widgets.indicators', 'pydm.widgets.label']),
    ("""<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <widget class="CLabel" name="CLabel_3">
  <property name="valueTransformation">
   <string notr="true">import numpy as np</string>
  </property>
 </widget>
 <customwidgets>
  <customwidget>
   <class>PyDMLabel</class>
   <extends>QLabel</extends>
   <header>pydm.widgets.label</header>
  </customwidget>
  <customwidget>
   <class>CLabel</class>
   <extends>PyDMLabel</extends>
   <header>comrad.widgets.indicators</header>
  </customwidget>
 </customwidgets>
 <resources/>
 <connections/>
</ui>""", ['numpy', 'comrad.widgets.indicators', 'pydm.widgets.label']),
    ("""<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>Form</class>
 <widget class="QWidget" name="Form">
  <property name="geometry">
   <rect>
    <x>0</x>
    <y>0</y>
    <width>294</width>
    <height>87</height>
   </rect>
  </property>
  <property name="windowTitle">
   <string>Client-side transformations with Python</string>
  </property>
  <layout class="QHBoxLayout" name="horizontalLayout">
   <item>
    <widget class="CLabel" name="CLabel">
     <property name="channel" stdset="0">
      <string notr="true">DemoDevice/Acquisition#Demo</string>
     </property>
     <property name="valueTransformation">
      <string notr="true">import numpy as np</string>
     </property>
    </widget>
   </item>
  </layout>
 </widget>
 <customwidgets>
  <customwidget>
   <class>PyDMLabel</class>
   <extends>QLabel</extends>
   <header>pydm.widgets.label</header>
  </customwidget>
  <customwidget>
   <class>CLabel</class>
   <extends>PyDMLabel</extends>
   <header>comrad.widgets.indicators</header>
  </customwidget>
 </customwidgets>
 <resources/>
 <connections/>
</ui>""", ['numpy', 'pydm.widgets.label', 'comrad.widgets.indicators']),
])
def test_scan_ui_imports_succeeds(tmp_path: Path, xml, expected_imports, relative_loc):
    ui_file = tmp_path / 'test_file.ui'
    ui_file.write_text(xml)
    expected_pkgs = {ScannedImport.create(pkg=i, relative_loc=relative_loc) for i in expected_imports}
    assert scan_ui_imports(ui_file, relative_loc=relative_loc) == expected_pkgs


@pytest.mark.parametrize('relative_loc,filename,code,expected_imports', [
    (None, 'external.py', '', []),
    ('', 'external.py', '', []),
    ('relative_dir', 'external.py', '', []),
    ('relative_dir/relative_subdir', 'external.py', '', []),
    (None, 'rel1/external.py', '', []),
    ('', 'rel1/external.py', '', []),
    ('relative_dir', 'rel1/external.py', '', []),
    ('relative_dir/relative_subdir', 'rel1/external.py', '', []),
    (None, 'external.py', 'print("Nothing important")', []),
    ('', 'external.py', 'print("Nothing important")', []),
    ('relative_dir', 'external.py', 'print("Nothing important")', []),
    ('relative_dir/relative_subdir', 'external.py', 'print("Nothing important")', []),
    (None, 'rel1/external.py', 'print("Nothing important")', []),
    ('', 'rel1/external.py', 'print("Nothing important")', []),
    ('relative_dir', 'rel1/external.py', 'print("Nothing important")', []),
    ('relative_dir/relative_subdir', 'rel1/external.py', 'print("Nothing important")', []),
    (None, 'external.py', 'import pytest', [('pytest', None)]),
    ('', 'external.py', 'import pytest', [('pytest', None)]),
    ('relative_dir', 'external.py', 'import pytest', [('pytest', 'relative_dir')]),
    ('relative_dir/relative_subdir', 'external.py', 'import pytest', [('pytest', 'relative_dir.relative_subdir')]),
    (None, 'rel1/external.py', 'import pytest', [('pytest', 'rel1')]),
    ('', 'rel1/external.py', 'import pytest', [('pytest', 'rel1')]),
    ('relative_dir', 'rel1/external.py', 'import pytest', [('pytest', 'relative_dir.rel1')]),
    ('relative_dir/relative_subdir', 'rel1/external.py', 'import pytest', [('pytest', 'relative_dir.relative_subdir.rel1')]),
    (None, 'external.py', 'import _comrad', [('_comrad', None)]),
    ('', 'external.py', 'import _comrad', [('_comrad', None)]),
    ('relative_dir', 'external.py', 'import _comrad', [('_comrad', 'relative_dir')]),
    ('relative_dir/relative_subdir', 'external.py', 'import _comrad', [('_comrad', 'relative_dir.relative_subdir')]),
    (None, 'rel1/external.py', 'import _comrad', [('_comrad', 'rel1')]),
    ('', 'rel1/external.py', 'import _comrad', [('_comrad', 'rel1')]),
    ('relative_dir', 'rel1/external.py', 'import _comrad', [('_comrad', 'relative_dir.rel1')]),
    ('relative_dir/relative_subdir', 'rel1/external.py', 'import _comrad', [('_comrad', 'relative_dir.relative_subdir.rel1')]),
    (None, 'external.py', 'from . import sibling', []),
    ('', 'external.py', 'from . import sibling', []),
    ('relative_dir', 'external.py', 'from . import sibling', []),
    ('relative_dir/relative_subdir', 'external.py', 'from . import sibling', []),
    (None, 'rel1/external.py', 'from . import sibling', []),
    ('', 'rel1/external.py', 'from . import sibling', []),
    ('relative_dir', 'rel1/external.py', 'from . import sibling', []),
    ('relative_dir/relative_subdir', 'rel1/external.py', 'from . import sibling', []),
    (None, 'external.py', 'from .. import cousin', []),
    ('', 'external.py', 'from .. import cousin', []),
    ('relative_dir', 'external.py', 'from .. import cousin', []),
    ('relative_dir/relative_subdir', 'external.py', 'from .. import cousin', []),
    (None, 'rel1/external.py', 'from .. import cousin', []),
    ('', 'rel1/external.py', 'from .. import cousin', []),
    ('relative_dir', 'rel1/external.py', 'from .. import cousin', []),
    ('relative_dir/relative_subdir', 'rel1/external.py', 'from .. import cousin', []),
    (None, 'external.py', 'from .sibling import anything', []),
    ('', 'external.py', 'from .sibling import anything', []),
    ('relative_dir', 'external.py', 'from .sibling import anything', []),
    ('relative_dir/relative_subdir', 'external.py', 'from .sibling import anything', []),
    (None, 'rel1/external.py', 'from .sibling import anything', []),
    ('', 'rel1/external.py', 'from .sibling import anything', []),
    ('relative_dir', 'rel1/external.py', 'from .sibling import anything', []),
    ('relative_dir/relative_subdir', 'rel1/external.py', 'from .sibling import anything', []),
    (None, 'external.py', 'from comrad import CDisplay', [('comrad', None)]),
    ('', 'external.py', 'from comrad import CDisplay', [('comrad', None)]),
    ('relative_dir', 'external.py', 'from comrad import CDisplay', [('comrad', 'relative_dir')]),
    ('relative_dir/relative_subdir', 'external.py', 'from comrad import CDisplay', [('comrad', 'relative_dir.relative_subdir')]),
    (None, 'rel1/external.py', 'from comrad import CDisplay', [('comrad', 'rel1')]),
    ('', 'rel1/external.py', 'from comrad import CDisplay', [('comrad', 'rel1')]),
    ('relative_dir', 'rel1/external.py', 'from comrad import CDisplay', [('comrad', 'relative_dir.rel1')]),
    ('relative_dir/relative_subdir', 'rel1/external.py', 'from comrad import CDisplay', [('comrad', 'relative_dir.relative_subdir.rel1')]),
    (None, 'external.py', 'from comrad.widgets import CDisplay', [('comrad.widgets', None)]),
    ('', 'external.py', 'from comrad.widgets import CDisplay', [('comrad.widgets', None)]),
    ('relative_dir', 'external.py', 'from comrad.widgets import CDisplay', [('comrad.widgets', 'relative_dir')]),
    ('relative_dir/relative_subdir', 'external.py', 'from comrad.widgets import CDisplay', [('comrad.widgets', 'relative_dir.relative_subdir')]),
    (None, 'rel1/external.py', 'from comrad.widgets import CDisplay', [('comrad.widgets', 'rel1')]),
    ('', 'rel1/external.py', 'from comrad.widgets import CDisplay', [('comrad.widgets', 'rel1')]),
    ('relative_dir', 'rel1/external.py', 'from comrad.widgets import CDisplay', [('comrad.widgets', 'relative_dir.rel1')]),
    ('relative_dir/relative_subdir', 'rel1/external.py', 'from comrad.widgets import CDisplay', [('comrad.widgets', 'relative_dir.relative_subdir.rel1')]),
    (None, 'external.py', """from comrad.widgets import CDisplay
import logging
from pytest import mark""", [('comrad.widgets', None), ('logging', None), ('pytest', None)]),
    ('', 'external.py', """from comrad.widgets import CDisplay
import logging
from pytest import mark""", [('comrad.widgets', None), ('logging', None), ('pytest', None)]),
    ('relative_dir', 'external.py', """from comrad.widgets import CDisplay
import logging
from pytest import mark""", [('comrad.widgets', 'relative_dir'), ('logging', 'relative_dir'), ('pytest', 'relative_dir')]),
    ('relative_dir/relative_subdir', 'external.py', """from comrad.widgets import CDisplay
import logging
from pytest import mark""", [('comrad.widgets', 'relative_dir.relative_subdir'), ('logging', 'relative_dir.relative_subdir'), ('pytest', 'relative_dir.relative_subdir')]),
    (None, 'rel1/external.py', """from comrad.widgets import CDisplay
import logging
from pytest import mark""", [('comrad.widgets', 'rel1'), ('logging', 'rel1'), ('pytest', 'rel1')]),
    ('', 'rel1/external.py', """from comrad.widgets import CDisplay
import logging
from pytest import mark""", [('comrad.widgets', 'rel1'), ('logging', 'rel1'), ('pytest', 'rel1')]),
    ('relative_dir', 'rel1/external.py', """from comrad.widgets import CDisplay
import logging
from pytest import mark""", [('comrad.widgets', 'relative_dir.rel1'), ('logging', 'relative_dir.rel1'), ('pytest', 'relative_dir.rel1')]),
    ('relative_dir/relative_subdir', 'rel1/external.py', """from comrad.widgets import CDisplay
import logging
from pytest import mark""", [('comrad.widgets', 'relative_dir.relative_subdir.rel1'), ('logging', 'relative_dir.relative_subdir.rel1'), ('pytest', 'relative_dir.relative_subdir.rel1')]),
])
def test_scan_ui_imports_succeeds_with_external_referenced_file(tmp_path: Path, relative_loc, code,
                                                                expected_imports, filename):
    ui_file = tmp_path / 'test_file.ui'
    ui_file.write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <widget class="CLabel" name="CLabel">
  <property name="snippetFilename" stdset="0">
   <string>{filename}</string>
  </property>
 </widget>
</ui>""")
    filename_path = Path(filename)
    py_file = tmp_path / filename_path
    py_file.parent.mkdir(parents=True, exist_ok=True)
    py_file.write_text(code)
    expected_pkgs = {ScannedImport.create(pkg=i, relative_loc=l) for i, l in expected_imports}
    actual_pkgs = scan_ui_imports(ui_file, relative_loc=relative_loc)
    assert actual_pkgs == expected_pkgs


@pytest.mark.parametrize('relative_loc', [None, '', 'relative_dir', 'relative_dir/relative_subdir'])
def test_scan_ui_imports_with_external_referenced_file_warns_if_does_not_exist(tmp_path: Path, relative_loc,
                                                                               log_capture):
    referenced_file_name = 'test_file.py'
    ui_file = tmp_path / 'test_file.ui'
    ui_file.write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <widget class="CLabel" name="CLabel">
  <property name="snippetFilename" stdset="0">
   <string>{referenced_file_name}</string>
  </property>
 </widget>
</ui>""")
    assert not (tmp_path / referenced_file_name).exists()
    assert log_capture(logging.WARNING, '_comrad.package.import_scanning') == []
    actual_pkgs = scan_ui_imports(ui_file, relative_loc=relative_loc)
    assert log_capture(logging.WARNING, '_comrad.package.import_scanning') == [f'Indicated file {referenced_file_name} inside '
                                                                               f"{ui_file!s}'s snippetFilename cannot be opened"]
    assert actual_pkgs == set()


@pytest.mark.parametrize('relative_loc', [None, '', 'relative_dir', 'relative_dir/relative_subdir'])
def test_scan_ui_imports_with_external_referenced_file_warns_if_is_dir(tmp_path: Path, relative_loc,
                                                                       log_capture):
    referenced_file_name = 'test_file.py'
    ui_file = tmp_path / 'test_file.ui'
    ui_file.write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <widget class="CLabel" name="CLabel">
  <property name="snippetFilename" stdset="0">
   <string>{referenced_file_name}</string>
  </property>
 </widget>
</ui>""")
    (tmp_path / referenced_file_name).mkdir(parents=True)
    assert log_capture(logging.WARNING, '_comrad.package.import_scanning') == []
    actual_pkgs = scan_ui_imports(ui_file, relative_loc=relative_loc)
    assert log_capture(logging.WARNING, '_comrad.package.import_scanning') == [f'Indicated file {referenced_file_name} inside '
                                                                               f"{ui_file!s}'s snippetFilename cannot be opened"]
    assert actual_pkgs == set()


@pytest.mark.parametrize('relative_loc', [None, '', 'relative_dir', 'relative_dir/relative_subdir'])
@pytest.mark.parametrize('referenced_file_name,code,expected_warning', [
    ('test_file.py', 'import', "Indicated file test_file.py inside {ui_file}'s snippetFilename contains invalid Python syntax:"),
    ('test_file.py', 'import .sibling.stuff', "Indicated file test_file.py inside {ui_file}'s snippetFilename contains invalid Python syntax:"),
    ('test_file.py', 'from import stuff', "Indicated file test_file.py inside {ui_file}'s snippetFilename contains invalid Python syntax:"),
    ('test_file.py', """from comrad import CDisplay

class MyDisplay(CDisplay):""", "Indicated file test_file.py inside {ui_file}'s snippetFilename contains invalid Python syntax:"),
])
def test_scan_ui_imports_with_external_referenced_file_warns_if_cant_be_parsed(tmp_path: Path, relative_loc,
                                                                               referenced_file_name, expected_warning,
                                                                               log_capture, code):
    ui_file = tmp_path / 'test_file.ui'
    ui_file.write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <widget class="CLabel" name="CLabel">
  <property name="snippetFilename" stdset="0">
   <string>{referenced_file_name}</string>
  </property>
 </widget>
</ui>""")
    (tmp_path / referenced_file_name).write_text(code)
    assert log_capture(logging.WARNING, '_comrad.package.import_scanning') == []
    actual_pkgs = scan_ui_imports(ui_file, relative_loc=relative_loc)
    logs = log_capture(logging.WARNING, '_comrad.package.import_scanning')
    assert len(logs) == 1
    assert expected_warning.format(ui_file=str(ui_file)) in logs[0]
    assert actual_pkgs == set()


@pytest.mark.parametrize('relative_loc', [None, '', 'relative_dir', 'relative_dir/relative_subdir'])
@pytest.mark.parametrize('xml,expected_error', [
    ('', '{ui_file} cannot be parsed as XML: no element found: line 1, column 0'),
    ('<ui version="4.0">', '{ui_file} cannot be parsed as XML: no element found: line 1, column 18'),
    ("""<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <widget class="CLabel" name="CLabel">
  <property name="snippetFilename" stdset="0">
   <string>test</string>
 </widget>
</ui>""", '{ui_file} cannot be parsed as XML: mismatched tag: line 6, column 3'),
    ("""<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <widget class="CLabel" name="CLabel">
  <property name="valueTransformation" stdset="0">
   <string>import; import numpy</string>
  </property>
 </widget>
</ui>""", 'valueTransformation "import; import numpy" inside {ui_file} contains invalid Python syntax: invalid syntax (<unknown>, line 1)'),
])
def test_scan_ui_imports_fails(tmp_path: Path, xml, relative_loc, log_capture, expected_error):
    ui_file = tmp_path / 'test_file.ui'
    ui_file.write_text(xml)

    assert log_capture(logging.WARNING, '_comrad.package.import_scanning') == []
    actual_pkgs = scan_ui_imports(ui_file, relative_loc=relative_loc)
    assert log_capture(logging.WARNING, '_comrad.package.import_scanning') == [expected_error.format(ui_file=str(ui_file))]
    assert actual_pkgs == set()


@pytest.mark.parametrize('acc_py_active,relative_loc,found_imports,local_modules,expected_results', [
    (True, None, set(), set(), set()),
    (True, None, {'one', 'one.two.three'}, set(), {'one'}),
    (True, None, {'one', 'one.two.three', 'logging'}, set(), {'one'}),
    (True, None, {'one', 'one.two.three', 'PyQt5.QtWidgets'}, set(), {'one'}),
    (True, None, {'one', 'one.two.three', 'qtpy.QtWidgets'}, set(), {'one', 'qtpy'}),
    (True, None, {'one', 'one.two.three', 'numpy'}, set(), {'one', 'numpy'}),
    (True, None, {'one', 'one.two.three', 'pytest'}, set(), {'one', 'pytest'}),
    (True, None, {'one', 'one.two.three', 'logging', 'pytest'}, set(), {'one', 'pytest'}),
    (True, None, {'one', 'one.two.three', 'logging', 'pytest', 'PyQt5'}, set(), {'one', 'pytest'}),
    (True, None, {'one', 'one.two.three', 'logging', 'pytest', 'numpy'}, set(), {'one', 'pytest', 'numpy'}),
    (True, None, {'one'}, {'one'}, set()),
    (True, None, {'one', 'logging'}, {'one'}, set()),
    (True, None, {'one', 'PyQt5.QtWidgets'}, {'one'}, set()),
    (True, None, {'one', 'qtpy.QtWidgets'}, {'one'}, {'qtpy'}),
    (True, None, {'one', 'numpy'}, {'one'}, {'numpy'}),
    (True, None, {'one', 'pytest'}, {'one'}, {'pytest'}),
    (True, None, {'one', 'logging', 'pytest'}, {'one'}, {'pytest'}),
    (True, None, {'mypkg'}, {'mypkg_metadata'}, {'mypkg'}),
    (True, None, {'mypkg'}, {'mypkg.metadata'}, set()),
    (True, None, {'one', 'one.two.three'}, {'one.two.three'}, set()),
    (True, None, {'one', 'one.two.three', 'logging'}, {'one.two.three'}, set()),
    (True, None, {'one', 'one.two.three', 'PyQt5.QtWidgets'}, {'one.two.three'}, set()),
    (True, None, {'one', 'one.two.three', 'qtpy.QtWidgets'}, {'one.two.three'}, {'qtpy'}),
    (True, None, {'one', 'one.two.three', 'numpy'}, {'one.two.three'}, {'numpy'}),
    (True, None, {'one', 'one.two.three', 'pytest'}, {'one.two.three'}, {'pytest'}),
    (True, None, {'one', 'one.two.three', 'logging', 'pytest'}, {'one.two.three'}, {'pytest'}),
    (True, None, {'one.two.three'}, {'one.two.three'}, set()),
    (True, None, {'one.two.three', 'logging'}, {'one.two.three'}, set()),
    (True, None, {'one.two.three', 'PyQt5.QtWidgets'}, {'one.two.three'}, set()),
    (True, None, {'one.two.three', 'qtpy.QtWidgets'}, {'one.two.three'}, {'qtpy'}),
    (True, None, {'one.two.three', 'numpy'}, {'one.two.three'}, {'numpy'}),
    (True, None, {'one.two.three', 'pytest'}, {'one.two.three'}, {'pytest'}),
    (True, None, {'one.two.three', 'logging', 'pytest'}, {'one.two.three'}, {'pytest'}),
    (True, '', set(), set(), set()),
    (True, '', {'one', 'one.two.three'}, set(), {'one'}),
    (True, '', {'one', 'one.two.three', 'logging'}, set(), {'one'}),
    (True, '', {'one', 'one.two.three', 'PyQt5.QtWidgets'}, set(), {'one'}),
    (True, '', {'one', 'one.two.three', 'qtpy.QtWidgets'}, set(), {'one', 'qtpy'}),
    (True, '', {'one', 'one.two.three', 'pytest'}, set(), {'one', 'pytest'}),
    (True, '', {'one', 'one.two.three', 'numpy'}, set(), {'one', 'numpy'}),
    (True, '', {'one', 'one.two.three', 'logging', 'pytest'}, set(), {'one', 'pytest'}),
    (True, '', {'one', 'one.two.three', 'logging', 'pytest', 'numpy'}, set(), {'one', 'pytest', 'numpy'}),
    (True, '', {'one'}, {'one'}, set()),
    (True, '', {'one', 'logging'}, {'one'}, set()),
    (True, '', {'one', 'PyQt5.QtWidgets'}, {'one'}, set()),
    (True, '', {'one', 'qtpy.QtWidgets'}, {'one'}, {'qtpy'}),
    (True, '', {'one', 'numpy'}, {'one'}, {'numpy'}),
    (True, '', {'one', 'pytest'}, {'one'}, {'pytest'}),
    (True, '', {'one', 'logging', 'pytest'}, {'one'}, {'pytest'}),
    (True, '', {'one', 'logging', 'pytest', 'numpy'}, {'one'}, {'pytest', 'numpy'}),
    (True, '', {'mypkg'}, {'mypkg_metadata'}, {'mypkg'}),
    (True, '', {'mypkg'}, {'mypkg.metadata'}, set()),
    (True, '', {'one', 'one.two.three'}, {'one.two.three'}, set()),
    (True, '', {'one', 'one.two.three', 'PyQt5.QtWidgets'}, {'one.two.three'}, set()),
    (True, '', {'one', 'one.two.three', 'logging'}, {'one.two.three'}, set()),
    (True, '', {'one', 'one.two.three', 'qtpy.QtWidgets'}, {'one.two.three'}, {'qtpy'}),
    (True, '', {'one', 'one.two.three', 'numpy'}, {'one.two.three'}, {'numpy'}),
    (True, '', {'one', 'one.two.three', 'pytest'}, {'one.two.three'}, {'pytest'}),
    (True, '', {'one', 'one.two.three', 'logging', 'pytest'}, {'one.two.three'}, {'pytest'}),
    (True, '', {'one', 'one.two.three', 'logging', 'pytest', 'numpy'}, {'one.two.three'}, {'pytest', 'numpy'}),
    (True, '', {'one.two.three'}, {'one.two.three'}, set()),
    (True, '', {'one.two.three', 'logging'}, {'one.two.three'}, set()),
    (True, '', {'one.two.three', 'PyQt5.QtWidgets'}, {'one.two.three'}, set()),
    (True, '', {'one.two.three', 'qtpy.QtWidgets'}, {'one.two.three'}, {'qtpy'}),
    (True, '', {'one.two.three', 'pytest'}, {'one.two.three'}, {'pytest'}),
    (True, '', {'one.two.three', 'numpy'}, {'one.two.three'}, {'numpy'}),
    (True, '', {'one.two.three', 'logging', 'pytest'}, {'one.two.three'}, {'pytest'}),
    (True, '', {'one.two.three', 'logging', 'pytest', 'numpy'}, {'one.two.three'}, {'pytest', 'numpy'}),
    (True, 'relative_dir', set(), set(), set()),
    (True, 'relative_dir', {'one', 'one.two.three'}, set(), {'one'}),
    (True, 'relative_dir', {'one', 'one.two.three', 'logging'}, set(), {'one'}),
    (True, 'relative_dir', {'one', 'one.two.three', 'PyQt5.QtWidgets'}, set(), {'one'}),
    (True, 'relative_dir', {'one', 'one.two.three', 'qtpy.QtWidgets'}, set(), {'one', 'qtpy'}),
    (True, 'relative_dir', {'one', 'one.two.three', 'pytest'}, set(), {'one', 'pytest'}),
    (True, 'relative_dir', {'one', 'one.two.three', 'logging', 'pytest'}, set(), {'one', 'pytest'}),
    (True, 'relative_dir', {'one'}, {'relative_dir.one'}, set()),
    (True, 'relative_dir', {'one', 'logging'}, {'relative_dir.one'}, set()),
    (True, 'relative_dir', {'one', 'PyQt5.QtWidgets'}, {'relative_dir.one'}, set()),
    (True, 'relative_dir', {'one', 'qtpy.QtWidgets'}, {'relative_dir.one'}, {'qtpy'}),
    (True, 'relative_dir', {'one', 'pytest'}, {'relative_dir.one'}, {'pytest'}),
    (True, 'relative_dir', {'one', 'numpy'}, {'relative_dir.one'}, {'numpy'}),
    (True, 'relative_dir', {'one', 'logging', 'pytest'}, {'relative_dir.one'}, {'pytest'}),
    (True, 'relative_dir', {'one', 'logging', 'pytest', 'numpy'}, {'relative_dir.one'}, {'pytest', 'numpy'}),
    (True, 'relative_dir', {'mypkg'}, {'relative_dir.mypkg_metadata'}, {'mypkg'}),
    (True, 'relative_dir', {'mypkg'}, {'relative_dir.mypkg.metadata'}, set()),
    (True, 'relative_dir', {'one', 'one.two.three'}, {'relative_dir.one.two.three'}, set()),
    (True, 'relative_dir', {'one', 'one.two.three', 'logging'}, {'relative_dir.one.two.three'}, set()),
    (True, 'relative_dir', {'one', 'one.two.three', 'PyQt5.QtWidgets'}, {'relative_dir.one.two.three'}, set()),
    (True, 'relative_dir', {'one', 'one.two.three', 'qtpy.QtWidgets'}, {'relative_dir.one.two.three'}, {'qtpy'}),
    (True, 'relative_dir', {'one', 'one.two.three', 'pytest'}, {'relative_dir.one.two.three'}, {'pytest'}),
    (True, 'relative_dir', {'one', 'one.two.three', 'numpy'}, {'relative_dir.one.two.three'}, {'numpy'}),
    (True, 'relative_dir', {'one', 'one.two.three', 'logging', 'pytest'}, {'relative_dir.one.two.three'}, {'pytest'}),
    (True, 'relative_dir', {'one', 'one.two.three', 'logging', 'pytest', 'numpy'}, {'relative_dir.one.two.three'}, {'pytest', 'numpy'}),
    (True, 'relative_dir', {'one.two.three'}, {'relative_dir.one.two.three'}, set()),
    (True, 'relative_dir', {'one.two.three', 'logging'}, {'relative_dir.one.two.three'}, set()),
    (True, 'relative_dir', {'one.two.three', 'PyQt5.QtWidgets'}, {'relative_dir.one.two.three'}, set()),
    (True, 'relative_dir', {'one.two.three', 'qtpy.QtWidgets'}, {'relative_dir.one.two.three'}, {'qtpy'}),
    (True, 'relative_dir', {'one.two.three', 'pytest'}, {'relative_dir.one.two.three'}, {'pytest'}),
    (True, 'relative_dir', {'one.two.three', 'numpy'}, {'relative_dir.one.two.three'}, {'numpy'}),
    (True, 'relative_dir', {'one.two.three', 'logging', 'pytest'}, {'relative_dir.one.two.three'}, {'pytest'}),
    (True, 'relative_dir', {'one.two.three', 'logging', 'pytest', 'numpy'}, {'relative_dir.one.two.three'}, {'pytest', 'numpy'}),
    (True, 'relative_dir/relative_subdir', set(), set(), set()),
    (True, 'relative_dir/relative_subdir', {'one', 'one.two.three'}, set(), {'one'}),
    (True, 'relative_dir/relative_subdir', {'one', 'one.two.three', 'logging'}, set(), {'one'}),
    (True, 'relative_dir/relative_subdir', {'one', 'one.two.three', 'PyQt5.QtWidgets'}, set(), {'one'}),
    (True, 'relative_dir/relative_subdir', {'one', 'one.two.three', 'qtpy.QtWidgets'}, set(), {'one', 'qtpy'}),
    (True, 'relative_dir/relative_subdir', {'one', 'one.two.three', 'pytest'}, set(), {'one', 'pytest'}),
    (True, 'relative_dir/relative_subdir', {'one', 'one.two.three', 'numpy'}, set(), {'one', 'numpy'}),
    (True, 'relative_dir/relative_subdir', {'one', 'one.two.three', 'logging', 'pytest'}, set(), {'one', 'pytest'}),
    (True, 'relative_dir/relative_subdir', {'one', 'one.two.three', 'logging', 'pytest', 'numpy'}, set(), {'one', 'pytest', 'numpy'}),
    (True, 'relative_dir/relative_subdir', {'one'}, {'relative_dir.relative_subdir.one'}, set()),
    (True, 'relative_dir/relative_subdir', {'one', 'logging'}, {'relative_dir.relative_subdir.one'}, set()),
    (True, 'relative_dir/relative_subdir', {'one', 'PyQt5.QtWidgets'}, {'relative_dir.relative_subdir.one'}, set()),
    (True, 'relative_dir/relative_subdir', {'one', 'qtpy.QtWidgets'}, {'relative_dir.relative_subdir.one'}, {'qtpy'}),
    (True, 'relative_dir/relative_subdir', {'one', 'pytest'}, {'relative_dir.relative_subdir.one'}, {'pytest'}),
    (True, 'relative_dir/relative_subdir', {'one', 'numpy'}, {'relative_dir.relative_subdir.one'}, {'numpy'}),
    (True, 'relative_dir/relative_subdir', {'one', 'logging', 'pytest'}, {'relative_dir.relative_subdir.one'}, {'pytest'}),
    (True, 'relative_dir/relative_subdir', {'one', 'logging', 'pytest', 'numpy'}, {'relative_dir.relative_subdir.one'}, {'pytest', 'numpy'}),
    (True, 'relative_dir/relative_subdir', {'mypkg'}, {'relative_dir.relative_subdir.mypkg_metadata'}, {'mypkg'}),
    (True, 'relative_dir/relative_subdir', {'mypkg'}, {'relative_dir.relative_subdir.mypkg.metadata'}, set()),
    (True, 'relative_dir/relative_subdir', {'one', 'one.two.three'}, {'relative_dir.relative_subdir.one.two.three'}, set()),
    (True, 'relative_dir/relative_subdir', {'one', 'one.two.three', 'logging'}, {'relative_dir.relative_subdir.one.two.three'}, set()),
    (True, 'relative_dir/relative_subdir', {'one', 'one.two.three', 'PyQt5.QtWidgets'}, {'relative_dir.relative_subdir.one.two.three'}, set()),
    (True, 'relative_dir/relative_subdir', {'one', 'one.two.three', 'qtpy.QtWidgets'}, {'relative_dir.relative_subdir.one.two.three'}, {'qtpy'}),
    (True, 'relative_dir/relative_subdir', {'one', 'one.two.three', 'pytest'}, {'relative_dir.relative_subdir.one.two.three'}, {'pytest'}),
    (True, 'relative_dir/relative_subdir', {'one', 'one.two.three', 'numpy'}, {'relative_dir.relative_subdir.one.two.three'}, {'numpy'}),
    (True, 'relative_dir/relative_subdir', {'one', 'one.two.three', 'logging', 'pytest'}, {'relative_dir.relative_subdir.one.two.three'}, {'pytest'}),
    (True, 'relative_dir/relative_subdir', {'one', 'one.two.three', 'logging', 'pytest', 'numpy'}, {'relative_dir.relative_subdir.one.two.three'}, {'pytest', 'numpy'}),
    (True, 'relative_dir/relative_subdir', {'one.two.three'}, {'relative_dir.relative_subdir.one.two.three'}, set()),
    (True, 'relative_dir/relative_subdir', {'one.two.three', 'logging'}, {'relative_dir.relative_subdir.one.two.three'}, set()),
    (True, 'relative_dir/relative_subdir', {'one.two.three', 'PyQt5.QtWidgets'}, {'relative_dir.relative_subdir.one.two.three'}, set()),
    (True, 'relative_dir/relative_subdir', {'one.two.three', 'qtpy.QtWidgets'}, {'relative_dir.relative_subdir.one.two.three'}, {'qtpy'}),
    (True, 'relative_dir/relative_subdir', {'one.two.three', 'pytest'}, {'relative_dir.relative_subdir.one.two.three'}, {'pytest'}),
    (True, 'relative_dir/relative_subdir', {'one.two.three', 'numpy'}, {'relative_dir.relative_subdir.one.two.three'}, {'numpy'}),
    (True, 'relative_dir/relative_subdir', {'one.two.three', 'logging', 'pytest'}, {'relative_dir.relative_subdir.one.two.three'}, {'pytest'}),
    (True, 'relative_dir/relative_subdir', {'one.two.three', 'logging', 'pytest', 'numpy'}, {'relative_dir.relative_subdir.one.two.three'}, {'pytest', 'numpy'}),
    (False, None, set(), set(), set()),
    (False, None, {'one', 'one.two.three'}, set(), {'one'}),
    (False, None, {'one', 'one.two.three', 'logging'}, set(), {'one'}),
    (False, None, {'one', 'one.two.three', 'PyQt5.QtWidgets'}, set(), {'PyQt5', 'one'}),
    (False, None, {'one', 'one.two.three', 'qtpy.QtWidgets'}, set(), {'one', 'qtpy'}),
    (False, None, {'one', 'one.two.three', 'numpy'}, set(), {'one', 'numpy'}),
    (False, None, {'one', 'one.two.three', 'pytest'}, set(), {'one', 'pytest'}),
    (False, None, {'one', 'one.two.three', 'logging', 'pytest'}, set(), {'one', 'pytest'}),
    (False, None, {'one', 'one.two.three', 'logging', 'pytest', 'PyQt5'}, set(), {'PyQt5', 'one', 'pytest'}),
    (False, None, {'one', 'one.two.three', 'logging', 'pytest', 'numpy'}, set(), {'one', 'pytest', 'numpy'}),
    (False, None, {'one'}, {'one'}, set()),
    (False, None, {'one', 'logging'}, {'one'}, set()),
    (False, None, {'one', 'PyQt5.QtWidgets'}, {'one'}, {'PyQt5'}),
    (False, None, {'one', 'qtpy.QtWidgets'}, {'one'}, {'qtpy'}),
    (False, None, {'one', 'numpy'}, {'one'}, {'numpy'}),
    (False, None, {'one', 'pytest'}, {'one'}, {'pytest'}),
    (False, None, {'one', 'logging', 'pytest'}, {'one'}, {'pytest'}),
    (False, None, {'mypkg'}, {'mypkg_metadata'}, {'mypkg'}),
    (False, None, {'mypkg'}, {'mypkg.metadata'}, set()),
    (False, None, {'one', 'one.two.three'}, {'one.two.three'}, set()),
    (False, None, {'one', 'one.two.three', 'logging'}, {'one.two.three'}, set()),
    (False, None, {'one', 'one.two.three', 'PyQt5.QtWidgets'}, {'one.two.three'}, {'PyQt5'}),
    (False, None, {'one', 'one.two.three', 'qtpy.QtWidgets'}, {'one.two.three'}, {'qtpy'}),
    (False, None, {'one', 'one.two.three', 'numpy'}, {'one.two.three'}, {'numpy'}),
    (False, None, {'one', 'one.two.three', 'pytest'}, {'one.two.three'}, {'pytest'}),
    (False, None, {'one', 'one.two.three', 'logging', 'pytest'}, {'one.two.three'}, {'pytest'}),
    (False, None, {'one.two.three'}, {'one.two.three'}, set()),
    (False, None, {'one.two.three', 'logging'}, {'one.two.three'}, set()),
    (False, None, {'one.two.three', 'PyQt5.QtWidgets'}, {'one.two.three'}, {'PyQt5'}),
    (False, None, {'one.two.three', 'qtpy.QtWidgets'}, {'one.two.three'}, {'qtpy'}),
    (False, None, {'one.two.three', 'numpy'}, {'one.two.three'}, {'numpy'}),
    (False, None, {'one.two.three', 'pytest'}, {'one.two.three'}, {'pytest'}),
    (False, None, {'one.two.three', 'logging', 'pytest'}, {'one.two.three'}, {'pytest'}),
    (False, '', set(), set(), set()),
    (False, '', {'one', 'one.two.three'}, set(), {'one'}),
    (False, '', {'one', 'one.two.three', 'logging'}, set(), {'one'}),
    (False, '', {'one', 'one.two.three', 'PyQt5.QtWidgets'}, set(), {'PyQt5', 'one'}),
    (False, '', {'one', 'one.two.three', 'qtpy.QtWidgets'}, set(), {'one', 'qtpy'}),
    (False, '', {'one', 'one.two.three', 'pytest'}, set(), {'one', 'pytest'}),
    (False, '', {'one', 'one.two.three', 'numpy'}, set(), {'one', 'numpy'}),
    (False, '', {'one', 'one.two.three', 'logging', 'pytest'}, set(), {'one', 'pytest'}),
    (False, '', {'one', 'one.two.three', 'logging', 'pytest', 'numpy'}, set(), {'one', 'pytest', 'numpy'}),
    (False, '', {'one'}, {'one'}, set()),
    (False, '', {'one', 'logging'}, {'one'}, set()),
    (False, '', {'one', 'PyQt5.QtWidgets'}, {'one'}, {'PyQt5'}),
    (False, '', {'one', 'qtpy.QtWidgets'}, {'one'}, {'qtpy'}),
    (False, '', {'one', 'numpy'}, {'one'}, {'numpy'}),
    (False, '', {'one', 'pytest'}, {'one'}, {'pytest'}),
    (False, '', {'one', 'logging', 'pytest'}, {'one'}, {'pytest'}),
    (False, '', {'one', 'logging', 'pytest', 'numpy'}, {'one'}, {'pytest', 'numpy'}),
    (False, '', {'mypkg'}, {'mypkg_metadata'}, {'mypkg'}),
    (False, '', {'mypkg'}, {'mypkg.metadata'}, set()),
    (False, '', {'one', 'one.two.three'}, {'one.two.three'}, set()),
    (False, '', {'one', 'one.two.three', 'PyQt5.QtWidgets'}, {'one.two.three'}, {'PyQt5'}),
    (False, '', {'one', 'one.two.three', 'logging'}, {'one.two.three'}, set()),
    (False, '', {'one', 'one.two.three', 'qtpy.QtWidgets'}, {'one.two.three'}, {'qtpy'}),
    (False, '', {'one', 'one.two.three', 'numpy'}, {'one.two.three'}, {'numpy'}),
    (False, '', {'one', 'one.two.three', 'pytest'}, {'one.two.three'}, {'pytest'}),
    (False, '', {'one', 'one.two.three', 'logging', 'pytest'}, {'one.two.three'}, {'pytest'}),
    (False, '', {'one', 'one.two.three', 'logging', 'pytest', 'numpy'}, {'one.two.three'}, {'pytest', 'numpy'}),
    (False, '', {'one.two.three'}, {'one.two.three'}, set()),
    (False, '', {'one.two.three', 'logging'}, {'one.two.three'}, set()),
    (False, '', {'one.two.three', 'PyQt5.QtWidgets'}, {'one.two.three'}, {'PyQt5'}),
    (False, '', {'one.two.three', 'qtpy.QtWidgets'}, {'one.two.three'}, {'qtpy'}),
    (False, '', {'one.two.three', 'pytest'}, {'one.two.three'}, {'pytest'}),
    (False, '', {'one.two.three', 'numpy'}, {'one.two.three'}, {'numpy'}),
    (False, '', {'one.two.three', 'logging', 'pytest'}, {'one.two.three'}, {'pytest'}),
    (False, '', {'one.two.three', 'logging', 'pytest', 'numpy'}, {'one.two.three'}, {'pytest', 'numpy'}),
    (False, 'relative_dir', set(), set(), set()),
    (False, 'relative_dir', {'one', 'one.two.three'}, set(), {'one'}),
    (False, 'relative_dir', {'one', 'one.two.three', 'logging'}, set(), {'one'}),
    (False, 'relative_dir', {'one', 'one.two.three', 'PyQt5.QtWidgets'}, set(), {'PyQt5', 'one'}),
    (False, 'relative_dir', {'one', 'one.two.three', 'qtpy.QtWidgets'}, set(), {'one', 'qtpy'}),
    (False, 'relative_dir', {'one', 'one.two.three', 'pytest'}, set(), {'one', 'pytest'}),
    (False, 'relative_dir', {'one', 'one.two.three', 'logging', 'pytest'}, set(), {'one', 'pytest'}),
    (False, 'relative_dir', {'one'}, {'relative_dir.one'}, set()),
    (False, 'relative_dir', {'one', 'logging'}, {'relative_dir.one'}, set()),
    (False, 'relative_dir', {'one', 'PyQt5.QtWidgets'}, {'relative_dir.one'}, {'PyQt5'}),
    (False, 'relative_dir', {'one', 'qtpy.QtWidgets'}, {'relative_dir.one'}, {'qtpy'}),
    (False, 'relative_dir', {'one', 'pytest'}, {'relative_dir.one'}, {'pytest'}),
    (False, 'relative_dir', {'one', 'numpy'}, {'relative_dir.one'}, {'numpy'}),
    (False, 'relative_dir', {'one', 'logging', 'pytest'}, {'relative_dir.one'}, {'pytest'}),
    (False, 'relative_dir', {'one', 'logging', 'pytest', 'numpy'}, {'relative_dir.one'}, {'pytest', 'numpy'}),
    (False, 'relative_dir', {'mypkg'}, {'relative_dir.mypkg_metadata'}, {'mypkg'}),
    (False, 'relative_dir', {'mypkg'}, {'relative_dir.mypkg.metadata'}, set()),
    (False, 'relative_dir', {'one', 'one.two.three'}, {'relative_dir.one.two.three'}, set()),
    (False, 'relative_dir', {'one', 'one.two.three', 'logging'}, {'relative_dir.one.two.three'}, set()),
    (False, 'relative_dir', {'one', 'one.two.three', 'PyQt5.QtWidgets'}, {'relative_dir.one.two.three'}, {'PyQt5'}),
    (False, 'relative_dir', {'one', 'one.two.three', 'qtpy.QtWidgets'}, {'relative_dir.one.two.three'}, {'qtpy'}),
    (False, 'relative_dir', {'one', 'one.two.three', 'pytest'}, {'relative_dir.one.two.three'}, {'pytest'}),
    (False, 'relative_dir', {'one', 'one.two.three', 'numpy'}, {'relative_dir.one.two.three'}, {'numpy'}),
    (False, 'relative_dir', {'one', 'one.two.three', 'logging', 'pytest'}, {'relative_dir.one.two.three'}, {'pytest'}),
    (False, 'relative_dir', {'one', 'one.two.three', 'logging', 'pytest', 'numpy'}, {'relative_dir.one.two.three'}, {'pytest', 'numpy'}),
    (False, 'relative_dir', {'one.two.three'}, {'relative_dir.one.two.three'}, set()),
    (False, 'relative_dir', {'one.two.three', 'logging'}, {'relative_dir.one.two.three'}, set()),
    (False, 'relative_dir', {'one.two.three', 'PyQt5.QtWidgets'}, {'relative_dir.one.two.three'}, {'PyQt5'}),
    (False, 'relative_dir', {'one.two.three', 'qtpy.QtWidgets'}, {'relative_dir.one.two.three'}, {'qtpy'}),
    (False, 'relative_dir', {'one.two.three', 'pytest'}, {'relative_dir.one.two.three'}, {'pytest'}),
    (False, 'relative_dir', {'one.two.three', 'numpy'}, {'relative_dir.one.two.three'}, {'numpy'}),
    (False, 'relative_dir', {'one.two.three', 'logging', 'pytest'}, {'relative_dir.one.two.three'}, {'pytest'}),
    (False, 'relative_dir', {'one.two.three', 'logging', 'pytest', 'numpy'}, {'relative_dir.one.two.three'}, {'pytest', 'numpy'}),
    (False, 'relative_dir/relative_subdir', set(), set(), set()),
    (False, 'relative_dir/relative_subdir', {'one', 'one.two.three'}, set(), {'one'}),
    (False, 'relative_dir/relative_subdir', {'one', 'one.two.three', 'logging'}, set(), {'one'}),
    (False, 'relative_dir/relative_subdir', {'one', 'one.two.three', 'PyQt5.QtWidgets'}, set(), {'PyQt5', 'one'}),
    (False, 'relative_dir/relative_subdir', {'one', 'one.two.three', 'qtpy.QtWidgets'}, set(), {'one', 'qtpy'}),
    (False, 'relative_dir/relative_subdir', {'one', 'one.two.three', 'pytest'}, set(), {'one', 'pytest'}),
    (False, 'relative_dir/relative_subdir', {'one', 'one.two.three', 'numpy'}, set(), {'one', 'numpy'}),
    (False, 'relative_dir/relative_subdir', {'one', 'one.two.three', 'logging', 'pytest'}, set(), {'one', 'pytest'}),
    (False, 'relative_dir/relative_subdir', {'one', 'one.two.three', 'logging', 'pytest', 'numpy'}, set(), {'one', 'pytest', 'numpy'}),
    (False, 'relative_dir/relative_subdir', {'one'}, {'relative_dir.relative_subdir.one'}, set()),
    (False, 'relative_dir/relative_subdir', {'one', 'logging'}, {'relative_dir.relative_subdir.one'}, set()),
    (False, 'relative_dir/relative_subdir', {'one', 'PyQt5.QtWidgets'}, {'relative_dir.relative_subdir.one'}, {'PyQt5'}),
    (False, 'relative_dir/relative_subdir', {'one', 'qtpy.QtWidgets'}, {'relative_dir.relative_subdir.one'}, {'qtpy'}),
    (False, 'relative_dir/relative_subdir', {'one', 'pytest'}, {'relative_dir.relative_subdir.one'}, {'pytest'}),
    (False, 'relative_dir/relative_subdir', {'one', 'numpy'}, {'relative_dir.relative_subdir.one'}, {'numpy'}),
    (False, 'relative_dir/relative_subdir', {'one', 'logging', 'pytest'}, {'relative_dir.relative_subdir.one'}, {'pytest'}),
    (False, 'relative_dir/relative_subdir', {'one', 'logging', 'pytest', 'numpy'}, {'relative_dir.relative_subdir.one'}, {'pytest', 'numpy'}),
    (False, 'relative_dir/relative_subdir', {'mypkg'}, {'relative_dir.relative_subdir.mypkg_metadata'}, {'mypkg'}),
    (False, 'relative_dir/relative_subdir', {'mypkg'}, {'relative_dir.relative_subdir.mypkg.metadata'}, set()),
    (False, 'relative_dir/relative_subdir', {'one', 'one.two.three'}, {'relative_dir.relative_subdir.one.two.three'}, set()),
    (False, 'relative_dir/relative_subdir', {'one', 'one.two.three', 'logging'}, {'relative_dir.relative_subdir.one.two.three'}, set()),
    (False, 'relative_dir/relative_subdir', {'one', 'one.two.three', 'PyQt5.QtWidgets'}, {'relative_dir.relative_subdir.one.two.three'}, {'PyQt5'}),
    (False, 'relative_dir/relative_subdir', {'one', 'one.two.three', 'qtpy.QtWidgets'}, {'relative_dir.relative_subdir.one.two.three'}, {'qtpy'}),
    (False, 'relative_dir/relative_subdir', {'one', 'one.two.three', 'pytest'}, {'relative_dir.relative_subdir.one.two.three'}, {'pytest'}),
    (False, 'relative_dir/relative_subdir', {'one', 'one.two.three', 'numpy'}, {'relative_dir.relative_subdir.one.two.three'}, {'numpy'}),
    (False, 'relative_dir/relative_subdir', {'one', 'one.two.three', 'logging', 'pytest'}, {'relative_dir.relative_subdir.one.two.three'}, {'pytest'}),
    (False, 'relative_dir/relative_subdir', {'one', 'one.two.three', 'logging', 'pytest', 'numpy'}, {'relative_dir.relative_subdir.one.two.three'}, {'pytest', 'numpy'}),
    (False, 'relative_dir/relative_subdir', {'one.two.three'}, {'relative_dir.relative_subdir.one.two.three'}, set()),
    (False, 'relative_dir/relative_subdir', {'one.two.three', 'logging'}, {'relative_dir.relative_subdir.one.two.three'}, set()),
    (False, 'relative_dir/relative_subdir', {'one.two.three', 'PyQt5.QtWidgets'}, {'relative_dir.relative_subdir.one.two.three'}, {'PyQt5'}),
    (False, 'relative_dir/relative_subdir', {'one.two.three', 'qtpy.QtWidgets'}, {'relative_dir.relative_subdir.one.two.three'}, {'qtpy'}),
    (False, 'relative_dir/relative_subdir', {'one.two.three', 'pytest'}, {'relative_dir.relative_subdir.one.two.three'}, {'pytest'}),
    (False, 'relative_dir/relative_subdir', {'one.two.three', 'numpy'}, {'relative_dir.relative_subdir.one.two.three'}, {'numpy'}),
    (False, 'relative_dir/relative_subdir', {'one.two.three', 'logging', 'pytest'}, {'relative_dir.relative_subdir.one.two.three'}, {'pytest'}),
    (False, 'relative_dir/relative_subdir', {'one.two.three', 'logging', 'pytest', 'numpy'}, {'relative_dir.relative_subdir.one.two.three'}, {'pytest', 'numpy'}),
])
def test_normalize_imports(found_imports, local_modules, expected_results, relative_loc, acc_py_active, ensure_acc_py):
    ensure_acc_py(acc_py_active)
    used_imports = {ScannedImport.create(pkg=i, relative_loc=relative_loc) for i in found_imports}
    assert normalize_imports(used_imports, local_modules) == expected_results


@pytest.mark.parametrize('acc_py_active,file_contents,expected_imports', [
    (True, [], set()),
    (False, [], set()),
    (True, [('example.py', '')], set()),
    (False, [('example.py', '')], set()),
    (True, [('example.ui', """<ui version="4.0">
 <widget class="QLabel" name="CLabel">
  <property name="text" stdset="0">
   <string>test</string>
  </property>
 </widget>
</ui>""")], set()),
    (False, [('example.ui', """<ui version="4.0">
 <widget class="QLabel" name="CLabel">
  <property name="text" stdset="0">
   <string>test</string>
  </property>
 </widget>
</ui>""")], set()),
    (True, [('example.py', 'import logging')], set()),
    (False, [('example.py', 'import logging')], set()),
    (True, [('example.py', 'from accwidgets.lsa_selector import LsaSelector')], {'accwidgets'}),
    (False, [('example.py', 'from accwidgets.lsa_selector import LsaSelector')], {'accwidgets'}),
    (True, [('logs.py', 'import logging'), ('example.py', 'from accwidgets.lsa_selector import LsaSelector')], {'accwidgets'}),
    (False, [('logs.py', 'import logging'), ('example.py', 'from accwidgets.lsa_selector import LsaSelector')], {'accwidgets'}),
    (True, [('example.ui', """<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>Form</class>
 <widget class="CLabel" name="CLabel">
  <property name="snippetFilename" stdset="0">
   <string>logs.py</string>
  </property>
 </widget>
</ui>"""), ('logs.py', 'import logging')], set()),
    (False, [('example.ui', """<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>Form</class>
 <widget class="CLabel" name="CLabel">
  <property name="snippetFilename" stdset="0">
   <string>logs.py</string>
  </property>
 </widget>
</ui>"""), ('logs.py', 'import logging')], set()),
    (True, [('example.ui', """<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <widget class="CLabel" name="CLabel">
  <property name="snippetFilename" stdset="0">
   <string>example.py</string>
  </property>
 </widget>
</ui>"""), ('example.py', 'from accwidgets.lsa_selector import LsaSelector')], {'accwidgets'}),
    (False, [('example.ui', """<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <widget class="CLabel" name="CLabel">
  <property name="snippetFilename" stdset="0">
   <string>example.py</string>
  </property>
 </widget>
</ui>"""), ('example.py', 'from accwidgets.lsa_selector import LsaSelector')], {'accwidgets'}),
    (True, [('app.py', """from comrad import CDisplay

class MyDisplay(CDisplay):

    def ui_filename(self):
        return 'app.ui'
"""), ('app.ui', """<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>Form</class>
 <widget class="QWidget" name="Form">
  <layout class="QHBoxLayout" name="horizontalLayout">
   <item>
    <widget class="CLabel" name="CLabel">
     <property name="channel" stdset="0">
      <string notr="true">DemoDevice/Acquisition#Demo</string>
     </property>
     <property name="valueTransformation">
      <string notr="true">import numpy as np; from PyQt5.QtCore import QObject; output(np.array([1, 2]))</string>
     </property>
    </widget>
   </item>
  </layout>
 </widget>
 <customwidgets>
  <customwidget>
   <class>PyDMLabel</class>
   <extends>QLabel</extends>
   <header>pydm.widgets.label</header>
  </customwidget>
  <customwidget>
   <class>CLabel</class>
   <extends>PyDMLabel</extends>
   <header>comrad.widgets.indicators</header>
  </customwidget>
 </customwidgets>
 <resources/>
 <connections/>
</ui>""")], {'comrad', 'numpy', 'pydm'}),
    (False, [('app.py', """from comrad import CDisplay

class MyDisplay(CDisplay):

    def ui_filename(self):
        return 'app.ui'
"""), ('app.ui', """<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>Form</class>
 <widget class="QWidget" name="Form">
  <layout class="QHBoxLayout" name="horizontalLayout">
   <item>
    <widget class="CLabel" name="CLabel">
     <property name="channel" stdset="0">
      <string notr="true">DemoDevice/Acquisition#Demo</string>
     </property>
     <property name="valueTransformation">
      <string notr="true">import numpy as np; from PyQt5.QtCore import QObject; output(np.array([1, 2]))</string>
     </property>
    </widget>
   </item>
  </layout>
 </widget>
 <customwidgets>
  <customwidget>
   <class>PyDMLabel</class>
   <extends>QLabel</extends>
   <header>pydm.widgets.label</header>
  </customwidget>
  <customwidget>
   <class>CLabel</class>
   <extends>PyDMLabel</extends>
   <header>comrad.widgets.indicators</header>
  </customwidget>
 </customwidgets>
 <resources/>
 <connections/>
</ui>""")], {'comrad', 'numpy', 'pydm', 'PyQt5'}),
])
def test_scan_imports_succeeds(tmp_path: Path, expected_imports, file_contents, acc_py_active, ensure_acc_py):
    ensure_acc_py(acc_py_active)
    for filename, content in file_contents:
        (tmp_path / filename).write_text(content)
    actual_results = scan_imports(directory=tmp_path)
    assert actual_results == expected_imports


@pytest.mark.parametrize('file_contents,expected_imports,expected_warnings', [
    ([('example.py', 'import')], set(), {'{dir}/example.py contains invalid Python syntax: invalid syntax (<unknown>, line 1)'}),
    ([('example.ui', """<ui version="4.0">
 <widget class="QLabel" name="CLabel">
  <property name="text" stdset="0">
   <string>test</string>
</ui>""")], set(), {'{dir}/example.ui cannot be parsed as XML: mismatched tag: line 5, column 2'}),
    ([('example.py', 'import logging'), ('example2.py', 'import')], set(), {'{dir}/example2.py contains invalid Python syntax: invalid syntax (<unknown>, line 1)'}),
    ([('example.py', 'from accwidgets.lsa_selector import LsaSelector'), ('example2.py', 'import')], {'accwidgets'}, {'{dir}/example2.py contains invalid Python syntax: invalid syntax (<unknown>, line 1)'}),
    ([('example.py', 'import'), ('example2.py', 'import')], set(), {'{dir}/example.py contains invalid Python syntax: invalid syntax (<unknown>, line 1)',
                                                                    '{dir}/example2.py contains invalid Python syntax: invalid syntax (<unknown>, line 1)'}),
    ([('example.ui', """<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>Form</class>
 <widget class="CLabel" name="CLabel">
  <property name="snippetFilename" stdset="0">
   <string>example.py</string>
  </property>
 </widget>
</ui>"""), ('example.py', 'import; import numpy')], set(), {'{dir}/example.py contains invalid Python syntax: invalid syntax (<unknown>, line 1)',
                                                            "Indicated file example.py inside {dir}/example.ui's snippetFilename contains invalid Python syntax: invalid syntax (<unknown>, line 1)"}),
    ([('example.ui', """<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>Form</class>
 <widget class="CLabel" name="CLabel">
  <property name="snippetFilename" stdset="0">
   <string>example.py</string>
  </property>
 </widget>
</ui>""")], set(), {"Indicated file example.py inside {dir}/example.ui's snippetFilename cannot be opened"}),
    ([('app.py', """from comrad import CDisplay

class MyDisplay(CDisplay):

    def ui_filename(self):
        return 'app.ui'
"""), ('app.ui', """<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>Form</class>
 <widget class="QWidget" name="Form">
  <layout class="QHBoxLayout" name="horizontalLayout">
   <item>
    <widget class="CLabel" name="CLabel">
     <property name="channel" stdset="0">
      <string notr="true">DemoDevice/Acquisition#Demo</string>
     </property>
     <property name="valueTransformation">
      <string notr="true">import; import numpy</string>
     </property>
    </widget>
   </item>
  </layout>
 </widget>
 <customwidgets>
  <customwidget>
   <class>PyDMLabel</class>
   <extends>QLabel</extends>
   <header>pydm.widgets.label</header>
  </customwidget>
  <customwidget>
   <class>CLabel</class>
   <extends>PyDMLabel</extends>
   <header>comrad.widgets.indicators</header>
  </customwidget>
 </customwidgets>
 <resources/>
 <connections/>
</ui>""")], {'comrad', 'pydm'}, {'valueTransformation "import; import numpy" inside {dir}/app.ui contains invalid Python syntax: invalid syntax (<unknown>, line 1)'}),
])
def test_scan_imports_fails(tmp_path: Path, expected_imports, expected_warnings, file_contents, log_capture):
    for filename, content in file_contents:
        (tmp_path / filename).write_text(content)
    assert log_capture(logging.WARNING, '_comrad.package.import_scanning') == []
    actual_results = scan_imports(directory=tmp_path)
    assert actual_results == expected_imports
    assert set(log_capture(logging.WARNING, '_comrad.package.import_scanning')) == {w.format(dir=str(tmp_path)) for w in expected_warnings}


all_examples = examples.find_runnable()


@pytest.mark.parametrize('example_path', all_examples, ids=list(map(str, all_examples)))
def test_scan_imports_smoke_test(example_path, log_capture):
    # This test verifies that all existing comrad examples can be parsed without warnings (skipping imports)
    assert log_capture(logging.WARNING, '_comrad.package.import_scanning') == []
    scan_imports(directory=example_path)
    assert log_capture(logging.WARNING, '_comrad.package.import_scanning') == []
