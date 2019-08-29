title = 'Client-side transformations with Python'
description = 'Many ComRAD widgets reuse logic available in CValueAggregator to let the user specify Python ' \
              'logic that should be applied to the incoming value. In contrast with CValueAggregator, this logic ' \
              'accepts only single channel as an input - channel that the widget is bound to. In this example we ' \
              'create a simple CLabel which decorates incoming value by wrapping it between "&lt;&lt; &gt;&gt;" before ' \
              'displaying it.'

entrypoint = 'app.ui'
japc_generator = 'japc_device:create_device'