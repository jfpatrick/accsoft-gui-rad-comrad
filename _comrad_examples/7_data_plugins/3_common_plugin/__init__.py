title = 'Common data plugin'
description = 'So called common data plugins are the ones that rely on operations, familiar to most control ' \
              'systems, namely GET, SET, SUBSCRIBE. GET operation can retrieve a single value on request, while ' \
              'SUBSCRIBE pushes them repeatedly. SET is used to write the data entered by the user into the ' \
              'control system. Base class for common plugins defines a skeleton to implement these operations. In ' \
              'addition, it does several assumptions. For instance, GET operation must be asynchronous to not block ' \
              'the UI. Also, GET and SUBSCRIBE are expected to have the same signature of the callback, as the data ' \
              'is processed by the same piece of logic. Most widgets will utilize SUBSCRIBE operations to regularly ' \
              'update their values. However, common plugins implement "request" logic, that issue a GET on user\'s ' \
              'request, e.g. when hitting a "Get" button in CPropertyEdit widget. This example implements a custom ' \
              'data plugin, that has a counter and on every GET or on every SUBSCRIBE event will increment the ' \
              'counter and return its value. Initial counter value is defined by the channel address, e.g. ' \
              '"count://3" will set counter to 3. SET operation can reset the counter to a desired value. SUBSCRIBE ' \
              'notification fires every second. Each operation is reflected in a dedicated CPropertyEdit, which we ' \
              'are using in this example because of its "Get" capability. To keep data representation uniform, we ' \
              'reuse the same widget for other operations and return value in a dictionary, that would normally ' \
              'correspond to the "device property" representation in JAPC/RDA.'

entrypoint = 'app.ui'

launch_arguments = [
    '--extra-data-plugin-path', '~example',
]
