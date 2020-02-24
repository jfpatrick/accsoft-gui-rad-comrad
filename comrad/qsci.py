from PyQt5.Qsci import QsciScintilla  # qtpy does not support QScintilla yet. Track here: https://github.com/spyder-ide/qtpy/issues/134
from qtpy.QtGui import QColor


QSCI_INDENTATION = 4


def configure_common_qsci(editor: QsciScintilla):
    """
    Configures source code editor to have a common style everywhere across the application.

    Args:
        editor: :class:`PyQt5.Qsci.QsciScintilla` object.
    """
    editor.setIndentationsUseTabs(False)
    editor.setIndentationGuides(True)
    editor.setTabWidth(QSCI_INDENTATION)
    editor.setEolMode(QsciScintilla.EolUnix)
    editor.setCaretLineVisible(True)
    editor.setCaretLineBackgroundColor(QColor('#efefef'))
    editor.setMargins(1)
    editor.setMarginType(0, QsciScintilla.NumberMargin)
    editor.setMarginWidth(0, 40)
    editor.setUtf8(True)
