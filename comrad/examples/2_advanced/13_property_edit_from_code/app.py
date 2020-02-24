from comrad import CDisplay, CPropertyEdit, CPropertyEditField, CLabel
from qtpy.QtWidgets import QVBoxLayout


class DemoDisplay(CDisplay):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QVBoxLayout()
        self.setLayout(layout)

        property_edit = CPropertyEdit(init_channel='japc:///DemoDevice/Settings')
        property_edit.decoration = CPropertyEdit.Decoration.FRAME
        property_edit.buttons = CPropertyEdit.Buttons.SET | CPropertyEdit.Buttons.GET
        property_edit.fields = [
            CPropertyEditField(field='IntVal', editable=True, type=CPropertyEdit.ValueType.INTEGER),
            CPropertyEditField(field='FloatVal', editable=True, type=CPropertyEdit.ValueType.REAL),
            CPropertyEditField(field='StrVal', editable=True, type=CPropertyEdit.ValueType.STRING),
            CPropertyEditField(field='BoolVal', editable=True, type=CPropertyEdit.ValueType.BOOLEAN),
            CPropertyEditField(field='EnumVal',
                               editable=True,
                               type=CPropertyEdit.ValueType.ENUM,
                               user_data=CPropertyEdit.ValueType.enum_user_data([
                                   ('ON', 1),
                                   ('OFF', 2),
                                   ('UNKNOWN', 3),
                               ])),
        ]
        self.property_edit = property_edit

        layout.addWidget(self.property_edit)
        layout.addStretch()

        self.label = CLabel(init_channel='japc:///DemoDevice/SettingsRepr#str')
        layout.addWidget(self.label)
