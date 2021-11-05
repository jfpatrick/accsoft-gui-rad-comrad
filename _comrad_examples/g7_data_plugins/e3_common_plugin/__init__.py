title = 'Common data plugin'
description = 'So called "common data plugins" are the ones that rely on operations, familiar to most control ' \
              'systems, namely <i>GET</i>, <i>SET</i>, <i>SUBSCRIBE</i>. <i>GET</i> operation can retrieve a ' \
              'single value on request, while <i>SUBSCRIBE</i> pushes them repeatedly. <i>SET</i> is used to ' \
              'write the data entered by the user into the control system. Base class for common plugins defines a skeleton to implement these operations. In ' \
              'addition, it does several assumptions. For instance, <i>GET</i> operation must be asynchronous ' \
              'to not block the UI. Also, <i>GET</i> and <i>SUBSCRIBE</i> are expected to have the same signature ' \
              'of the callback, as the data is processed by the same piece of logic. Most widgets will utilize ' \
              '<i>SUBSCRIBE</i> operations to regularly update their values. However, common plugins implement ' \
              '"request" logic, that issue a <i>GET</i> on user\'s request, e.g. when hitting a "Get" button in ' \
              'a <code>CPropertyEdit</code> widget.<br/>' \
              '<br/>' \
              'This example implements a custom data plugin that has a counter, and on every <i>GET</i> or on ' \
              'every <i>SUBSCRIBE</i> event it will increment the counter and return its value. Initial counter ' \
              'value is defined by the channel address, e.g. "<code>count://3</code>" will set counter to ' \
              '<code>3</code>. <i>SET</i> operation can reset the counter to a desired value. <i>SUBSCRIBE</i> ' \
              'notification fires every second. Each operation is reflected in a dedicated <code>CPropertyEdit</code>, ' \
              'which we are using in this example because of its "Get" capability. To keep data representation ' \
              'uniform, we reuse the same widget for other operations and return value in a dictionary, that ' \
              'would normally correspond to the "device property" representation in JAPC/RDA.'

entrypoint = 'app.ui'

launch_arguments = [
    '--extra-data-plugin-path', '~example',
]
