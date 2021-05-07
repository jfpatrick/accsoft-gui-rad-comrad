from typing import Optional
from qtpy.QtWidgets import QWidget
from qtpy.QtDesigner import QDesignerFormWindowCursorInterface, QDesignerFormWindowInterface


def get_designer_cursor(widget: QWidget) -> Optional[QDesignerFormWindowCursorInterface]:
    """
    Retrieve the pointer to the form interface.

    Args:
        widget: Widget to probe.
    """
    form = QDesignerFormWindowInterface.findFormWindow(widget)
    return form.cursor() if form else None


def is_inside_designer_canvas(widget: QWidget) -> bool:
    """
    Verify that the widget is not only launched inside designer, but that it actually is rendered on the canvas
    and not e.g. in the Form Preview.

    Args:
        widget: Widget to verify.

    Returns:
        :obj:`True` if it only is rendered in the canvas and not the Designer Form Preview, or outside Designer completely.
    """
    return get_designer_cursor(widget) is not None
