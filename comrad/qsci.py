from PyQt5.Qsci import QsciScintilla
from qtpy.QtGui import QColor


QSCI_INDENTATION = 4


def configure_common_qsci(editor: QsciScintilla):
    """
    Configures source code editor to have a common style everywhere across the application.

    Args:
        editor: QScintilla object
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
