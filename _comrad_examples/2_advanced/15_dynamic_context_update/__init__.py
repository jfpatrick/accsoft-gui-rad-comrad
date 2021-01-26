title = 'Update context of CContextFrame with custom GUI controls'
description = '<code>CContextFrame</code> is a generic component, that allows manipulating its context via ' \
              'Signals/Slots. It means that we can connect a custom GUI component, that would propagate the required ' \
              'information. In this example, custom <code>QComboBox</code> is used to drive the selector inside ' \
              '<code>CContexFrame</code>. Simulated device exposes data on 2 different timing users, therefore the ' \
              'connection is dynamically re-created with the correct timing user. You can observe active connections ' \
              'in "View"➔"Show connections..." menu.'

entrypoint = 'app.ui'
japc_generator = 'japc_device:create_device'
