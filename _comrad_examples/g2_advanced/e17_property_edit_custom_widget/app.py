from comrad import CDisplay, CPropertyEdit, CPropertyEditField, CAbstractPropertyEditWidgetDelegate
from qtpy.QtWidgets import QVBoxLayout, QLCDNumber


class CustomWidgetDelegate(CAbstractPropertyEditWidgetDelegate):
    """
    Custom delegate that creates LCD widgets for numerical fields.
    """

    def create_widget(self, field_id, item_type, editable, user_data, parent=None):
        widget = QLCDNumber(parent)
        widget.setFrameShape(QLCDNumber.NoFrame)
        widget.setSegmentStyle(QLCDNumber.Flat)
        return widget

    def display_data(self, field_id, value, user_data, item_type, widget: QLCDNumber):
        widget.display(value)

    def send_data(self, field_id, user_data, item_type, widget: QLCDNumber):
        if item_type == CPropertyEdit.ValueType.INTEGER:
            return widget.intValue()
        else:
            return widget.value()


class DemoDisplay(CDisplay):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle('Custom widget in CPropertyEdit')

        layout = QVBoxLayout()
        self.setLayout(layout)

        property_edit = CPropertyEdit(init_channel='DemoDevice/Acquisition')
        property_edit.decoration = CPropertyEdit.Decoration.FRAME
        property_edit.fields = [
            CPropertyEditField(field='IntVal', editable=False, type=CPropertyEdit.ValueType.INTEGER),
            CPropertyEditField(field='FloatVal', editable=False, type=CPropertyEdit.ValueType.REAL),
        ]
        property_edit.widget_delegate = CustomWidgetDelegate()  # Here is the magic
        self.property_edit = property_edit
        layout.addWidget(self.property_edit)
