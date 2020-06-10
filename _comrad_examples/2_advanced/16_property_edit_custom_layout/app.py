from comrad import CDisplay, CPropertyEdit, CPropertyEditField, CLabel, CAbstractPropertyEditLayoutDelegate
from qtpy.QtWidgets import QHBoxLayout, QVBoxLayout


class CustomLayoutDelegate(CAbstractPropertyEditLayoutDelegate[QHBoxLayout]):
    """
    Custom delegate that creates horizontal layout, as opposed to default "Form-like" layout.
    """

    def create_layout(self) -> QHBoxLayout:
        return QHBoxLayout()

    def layout_widgets(self, layout, widget_config, create_widget, parent=None):
        # Add new widgets
        for conf in widget_config:
            widget = create_widget(conf, parent)
            layout.addWidget(widget)


class DemoDisplay(CDisplay):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle('Custom layout in CPropertyEdit')

        layout = QVBoxLayout()
        self.setLayout(layout)

        property_edit = CPropertyEdit(init_channel='DemoDevice/Settings')
        property_edit.decoration = CPropertyEdit.Decoration.FRAME
        property_edit.sendOnlyUpdatedValues = False
        property_edit.buttons = CPropertyEdit.Buttons.SET | CPropertyEdit.Buttons.GET
        property_edit.fields = [
            CPropertyEditField(field='IntVal', editable=True, type=CPropertyEdit.ValueType.INTEGER),
            CPropertyEditField(field='FloatVal', editable=True, type=CPropertyEdit.ValueType.REAL),
            CPropertyEditField(field='StrVal', editable=True, type=CPropertyEdit.ValueType.STRING),
            CPropertyEditField(field='EnumVal',
                               editable=True,
                               type=CPropertyEdit.ValueType.ENUM,
                               user_data=CPropertyEdit.ValueType.enum_user_data([
                                   ('ON', 1),
                                   ('OFF', 2),
                                   ('UNKNOWN', 3),
                               ])),
        ]
        property_edit.layout_delegate = CustomLayoutDelegate()  # Here is the magic
        self.property_edit = property_edit

        layout.addWidget(self.property_edit)
        layout.addStretch()

        self.label = CLabel(init_channel='DemoDevice/SettingsRepr#str')
        layout.addWidget(self.label)
