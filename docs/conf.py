from typing import List
from datetime import datetime
from comrad import __version__, __author__

# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# http://www.sphinx-doc.org/en/master/config

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))


# -- Project information -----------------------------------------------------

author_name = __author__.split('<')[0].strip()

project = 'ComRAD'
copyright = f'{datetime.now().year}, CERN'
author = author_name

# The full version, including alpha/beta/rc tags
release = __version__
version = __version__


# -- General configuration ---------------------------------------------------

primary_domain = 'py'
highlight_language = 'py'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx_rtd_theme',  # Read-the-docs theme
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.autosectionlabel',  # To allow cross-referencing sections between documents
    'sphinx.ext.intersphinx',  # To connect external docs, e.g. PyQt5
    'sphinx.ext.napoleon',  # This needs to be before typehints
    'sphinx_autodoc_typehints',
    'sphinx.ext.inheritance_diagram',  # Draw inheritance diagrams
    'sphinx.ext.graphviz',  # Needed to draw diagrams produced by plugin above
    'sphinx.ext.todo',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns: List[str] = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

html_short_title = f'{project} v{__version__}'
html_title = f'{html_short_title} docs'

html_logo = '../comrad/icons/app.ico'
html_favicon = html_logo
html_css_files = [
    'fix_tables.css',
    'fix_bullets.css',
]

# Both the class’ and the __init__ method’s docstring are concatenated and inserted.
autoclass_content = 'both'
# This value controls the docstrings inheritance. If set to True the docstring for classes or methods,
# if not explicitly set, is inherited form parents.
autodoc_inherit_docstrings = True
# The default options for autodoc directives. They are applied to all autodoc directives automatically.
autodoc_default_options = {
    'show-inheritance': True,
    'member-order': 'bysource',
    'exclude-members': '__init__,'
                       '__str__,'
                       '__sizeof__,'
                       '__setattr__,'
                       '__repr__,'
                       '__reduce_ex__,'
                       '__reduce__,'
                       '__new__,'
                       '__ne__,'
                       '__lt__,'
                       '__le__,'
                       '__init_subclass__,'
                       '__hash__,'
                       '__gt__,'
                       '__getattribute__,'
                       '__getattr__,'
                       '__ge__,'
                       '__format__,'
                       '__eq__,'
                       '__dir__,'
                       '__delattr__,'
                       'PaintDeviceMetric,'
                       'RenderFlag,'
                       'RenderFlags,'
                       'Shadow,'
                       'Shape,'
                       'StyleMask,'
                       '__weakref__,'
                       '__subclasshook__,'
                       'acceptDrops,'
                       'accessibleDescription,'
                       'accessibleName,'
                       'actionEvent,'
                       'actions,'
                       'activateWindow,'
                       'addAction,'
                       'addActions,'
                       'adjustSize,'
                       'alarmSeverityChanged,'
                       'alarm_severity_changed,'
                       'alignment,'
                       'autoFillBackground,'
                       'baseSize,'
                       'backgroundRole,'
                       'blockSignals,'
                       'buddy,'
                       'changeEvent,'
                       'childAt,'
                       'childEvent,'
                       'children,'
                       'childrenRect,'
                       'childrenRegion,'
                       'clear,'
                       'clearFocus,'
                       'clearMask,'
                       'close,'
                       'closeEvent,'
                       'colorCount,'
                       'connectNotify,'
                       'contentsMargins,'
                       'contentsRect,'
                       'contextMenuEvent,'
                       'contextMenuPolicy,'
                       'create,'
                       'createWindowContainer,'
                       'ctrl_limit_changed,'
                       'cursor,'
                       'customContextMenuRequested,'
                       'customEvent,'
                       'deleteLater,'
                       'depth,'
                       'destroy,'
                       'destroyed,'
                       'devType,'
                       'devicePixelRatio,'
                       'devicePixelRatioF,'
                       'devicePixelRatioFScale,'
                       'disconnect,'
                       'disconnectNotify,'
                       'dragEnterEvent,'
                       'dragLeaveEvent,'
                       'dragMoveEvent,'
                       'drawFrame,'
                       'dropEvent,'
                       'dumpObjectTree,'
                       'dumpObjectInfo,'
                       'dynamicPropertyNames,'
                       'effectiveWinId,'
                       'ensurePolished,'
                       'enterEvent,'
                       'event,'
                       'eventFilter,'
                       'find,'
                       'findChild,'
                       'findChildren,'
                       'focusInEvent,'
                       'focusNextChild,'
                       'focusNextPrevChild,'
                       'focusOutEvent,'
                       'focusPolicy,'
                       'focusPreviousChild,'
                       'focusProxy,'
                       'focusWidget,'
                       'font,'
                       'fontInfo,'
                       'fontMetrics,'
                       'foregroundRole,'
                       'frameGeometry,'
                       'frameRect,'
                       'frameShadow,'
                       'frameShape,'
                       'frameSize,'
                       'frameStyle,'
                       'frameWidth,'
                       'geometry,'
                       'getContentsMargins,'
                       'get_ctrl_limits,'
                       'grab,'
                       'grabGesture,'
                       'grabKeyboard,'
                       'grabMouse,'
                       'grabShortcut,'
                       'graphicsEffect,'
                       'graphicsProxyWidget,'
                       'hasFocus,'
                       'hasHeightForWidth,'
                       'hasMouseTracking,'
                       'hasScaledContents,'
                       'hasSelectedText,'
                       'hasTabletTracking,'
                       'height,'
                       'heightForWidth,'
                       'heightMM,'
                       'hide,'
                       'hideEvent,'
                       'indent,'
                       'inherits,'
                       'initPainter,'
                       'initStyleOption,'
                       'inputMethodEvent,'
                       'inputMethodHints,'
                       'inputMethodQuery,'
                       'insertAction,'
                       'insertActions,'
                       'installEventFilter,'
                       'isActiveWindow,'
                       'isAncestorOf,'
                       'isEnabled,'
                       'isEnabledTo,'
                       'isFullScreen,'
                       'isHidden,'
                       'isLeftToRight,'
                       'isMaximized,'
                       'isMinimized,'
                       'isModal,'
                       'isRightToLeft,'
                       'isSignalConnected,'
                       'isVisible,'
                       'isVisibleTo,'
                       'isWidgetType,'
                       'isWindow,'
                       'isWindowModified,'
                       'isWindowType,'
                       'keyPressEvent,'
                       'keyReleaseEvent,'
                       'keyboardGrabber,'
                       'killTimer,'
                       'layout,'
                       'layoutDirection,'
                       'leaveEvent,'
                       'lineWidth,'
                       'linkActivated,'
                       'linkHovered,'
                       'locale,'
                       'logicalDpiX,'
                       'logicalDpiY,'
                       'lower,'
                       'lowerCtrlLimitChanged,'
                       'mapFrom,'
                       'mapFromGlobal,'
                       'mapFromParent,'
                       'mapTo,'
                       'mapToGlobal,'
                       'mapToParent,'
                       'margin,'
                       'mask,'
                       'maximumHeight,'
                       'maximumSize,'
                       'maximumWidth,'
                       'metaObject,'
                       'metric,'
                       'midLineWidth,'
                       'minimumHeight,'
                       'minimumSize,'
                       'minimumSizeHint,'
                       'minimumWidth,'
                       'mouseDoubleClickEvent,'
                       'mouseGrabber,'
                       'mouseMoveEvent,'
                       'mousePressEvent,'
                       'mouseReleaseEvent,'
                       'move,'
                       'moveEvent,'
                       'moveToThread,'
                       'movie,'
                       'nativeEvent,'
                       'nativeParentWidget,'
                       'nextInFocusChain,'
                       'normalGeometry,'
                       'objectName,'
                       'objectNameChanged,'
                       'openExternalLinks,'
                       'overrideWindowFlags,'
                       'overrideWindowState,'
                       'paintEngine,'
                       'paintEvent,'
                       'paintingActive,'
                       'palette,'
                       'parent,'
                       'parentWidget,'
                       'physicalDpiX,'
                       'physicalDpiY,'
                       'picture,'
                       'pixmap,'
                       'pos,'
                       'precisionChanged,'
                       'precision_changed,'
                       'previousInFocusChain,'
                       'property,'
                       'pyqtConfigure,'
                       'raise_,'
                       'receivers,'
                       'rect,'
                       'releaseKeyboard,'
                       'releaseMouse,'
                       'releaseShortcut,'
                       'removeAction,'
                       'removeEventFilter,'
                       'render,'
                       'repaint,'
                       'resize,'
                       'resizeEvent,'
                       'restoreGeometry,'
                       'saveGeometry,'
                       'scroll,'
                       'selectedText,'
                       'selectionStart,'
                       'sender,'
                       'senderSignalIndex,'
                       'setAcceptDrops,'
                       'setAccessibleDescription,'
                       'setAccessibleName,'
                       'setAlignment,'
                       'setAttribute,'
                       'setAutoFillBackground,'
                       'setBackgroundRole,'
                       'setBaseSize,'
                       'setBuddy,'
                       'setContentsMargins,'
                       'setContextMenuPolicy,'
                       'setCursor,'
                       'setDisabled,'
                       'setEnabled,'
                       'setFixedHeight,'
                       'setFixedSize,'
                       'setFixedWidth,'
                       'setFocus,'
                       'setFocusPolicy,'
                       'setFocusProxy,'
                       'setFont,'
                       'setForegroundRole,'
                       'setFrameRect,'
                       'setFrameShadow,'
                       'setFrameShape,'
                       'setFrameStyle,'
                       'setGeometry,'
                       'setGraphicsEffect,'
                       'setHidden,'
                       'setIndent,'
                       'setInputMethodHints,'
                       'setLayout,'
                       'setLayoutDirection,'
                       'setLineWidth,'
                       'setLocale,'
                       'setMargin,'
                       'setMask,'
                       'setMaximumHeight,'
                       'setMaximumSize,'
                       'setMaximumWidth,'
                       'setMidLineWidth,'
                       'setMinimumHeight,'
                       'setMinimumSize,'
                       'setMinimumWidth,'
                       'setMouseTracking,'
                       'setMovie,'
                       'setObjectName,'
                       'setOpenExternalLinks,'
                       'setPalette,'
                       'setParent,'
                       'setPicture,'
                       'setPixmap,'
                       'setProperty,'
                       'setScaledContents,'
                       'setSelection,'
                       'setShortcutAutoRepeat,'
                       'setShortcutEnabled,'
                       'setSizeIncrement,'
                       'setSizePolicy,'
                       'setStatusTip,'
                       'setStyle,'
                       'setStyleSheet,'
                       'setTabOrder,'
                       'setTabletTracking,'
                       'setText,'
                       'setTextFormat,'
                       'setTextInteractionFlags,'
                       'setToolTip,'
                       'setToolTipDuration,'
                       'setUpdatesEnabled,'
                       'setVisible,'
                       'setWhatsThis,'
                       'setWindowFilePath,'
                       'setWindowFlag,'
                       'setWindowFlags,'
                       'setWindowIcon,'
                       'setWindowIconText,'
                       'setWindowModality,'
                       'setWindowModified,'
                       'setWindowOpacity,'
                       'setWindowRole,'
                       'setWindowState,'
                       'setWindowTitle,'
                       'setWordWrap,'
                       'setX,'
                       'setY,'
                       'sharedPainter,'
                       'show,'
                       'showEvent,'
                       'showFullScreen,'
                       'showMaximized,'
                       'showMinimized,'
                       'showNormal,'
                       'signalsBlocked,'
                       'size,'
                       'sizeHint,'
                       'sizeIncrement,'
                       'sizePolicy,'
                       'stackUnder,'
                       'startTimer,'
                       'statusTip,'
                       'style,'
                       'styleSheet,'
                       'tabletEvent,'
                       'testAttribute,'
                       'text,'
                       'textFormat,'
                       'textInteractionFlags,'
                       'thread,'
                       'timerEvent,'
                       'toolTip,'
                       'toolTipDuration,'
                       'tr,'
                       'underMouse,'
                       'ungrabGesture,'
                       'unitChanged,'
                       'unit_changed,'
                       'unsetCursor,'
                       'unsetLayoutDirection,'
                       'unsetLocale,'
                       'update,'
                       'updateGeometry,'
                       'updateMicroFocus,'
                       'updatesEnabled,'
                       'upperCtrlLimitChanged,'
                       'visibleRegion,'
                       'whatsThis,'
                       'wheelEvent,'
                       'width,'
                       'widthMM,'
                       'winId,'
                       'window,'
                       'windowFilePath,'
                       'windowFlags,'
                       'windowHandle,'
                       'windowIcon,'
                       'windowIconChanged,'
                       'windowIconText,'
                       'windowIconTextChanged,'
                       'windowModality,'
                       'windowOpacity,'
                       'windowRole,'
                       'windowState,'
                       'windowTitle,'
                       'windowTitleChanged,'
                       'windowType,'
                       'wordWrap,'
                       'x,'
                       'y,'
                       'ActionPosition,'
                       'EchoMode,'
                       'backspace,'
                       'completer,'
                       'copy,'
                       'createStandardContextMenu,'
                       'cursorBackward,'
                       'cursorForward,'
                       'cursorMoveStyle,'
                       'cursorPosition,'
                       'cursorPositionAt,'
                       'cursorPositionChanged,'
                       'cursorRect,'
                       'cursorWordBackward,'
                       'cursorWordForward,'
                       'cut,'
                       'del_,'
                       'deselect,'
                       'displayText,'
                       'dragEnabled,'
                       'echoMode,'
                       'editingFinished,'
                       'end,'
                       'getTextMargins,'
                       'hasAcceptableInput,'
                       'hasFrame,'
                       'home,'
                       'inputMask,'
                       'isClearButtonEnabled,'
                       'isModified,'
                       'isReadOnly,'
                       'isRedoAvailable,'
                       'isUndoAvailable,'
                       'maxLength,'
                       'paste,'
                       'placeholderText,'
                       'redo,'
                       'returnPressed,'
                       'selectAll,'
                       'selectionChanged,'
                       'selectionEnd,'
                       'selectionLength,'
                       'setClearButtonEnabled,'
                       'setCompleter,'
                       'setCursorMoveStyle,'
                       'setCursorPosition,'
                       'setDragEnabled,'
                       'setEchoMode,'
                       'setFrame,'
                       'setInputMask,'
                       'setMaxLength,'
                       'setModified,'
                       'setPlaceholderText,'
                       'setReadOnly,'
                       'setTextMargins,'
                       'setValidator,'
                       'textChanged,'
                       'textEdited,'
                       'textMargins,'
                       'undo,'
                       'validator,'
                       'ColorSpec,'
                       'aboutQt,'
                       'aboutToQuit,'
                       'activeModalWidget,'
                       'activePopupWidget,'
                       'activeWindow,'
                       'addLibraryPath,'
                       'alert,'
                       'allWidgets,'
                       'allWindows',
}
# Scan all found documents for autosummary directives, and generate stub pages for each.
autosummary_generate = True
# Document classes and functions imported in modules
autosummary_imported_members = True
# if True, set typing.TYPE_CHECKING to True to enable “expensive” typing imports
set_type_checking_flag = True


# Enable Markdown source files along with reStructuredText
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

intersphinx_mapping = {
    'python': ('https://docs.python.org/3.6', None),
    'Qt': ('https://doc.qt.io/qt-5/', './qt.inv'),
    'PyQt5': ('https://www.riverbankcomputing.com/static/Docs/PyQt5/', None),
    'QScintilla': ('https://www.riverbankcomputing.com/static/Docs/QScintilla/', './qsci.inv'),
    'pydm': ('http://slaclab.github.io/pydm/', './pydm.inv'),
    'numpy': ('http://docs.scipy.org/doc/numpy/', None),
    'pyqtgraph': ('http://www.pyqtgraph.org/documentation/', None),
    'pyjapc': ('http://bewww.cern.ch/~bdisoft/pyjapc/', None),
    # 'accwidgets': ('https://acc-py.web.cern.ch/gitlab/acc-co/accsoft/gui/pyqt/accsoft-gui-pyqt-widgets/docs/master/', None),
}


inheritance_graph_attrs = {
    'fontsize': 14,
    'size': '"60, 30"',
}


todo_include_todos = True


autosectionlabel_prefix_document = True


# Support for text colors, proposed here: https://stackoverflow.com/a/60991308
rst_epilog = """
.. include:: <s5defs.txt>
"""
html_css_files.append('s5defs-roles.css')
