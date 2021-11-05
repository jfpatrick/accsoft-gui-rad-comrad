title = 'Client-side transformations with Python'
description = 'Many ComRAD widgets reuse logic available in <code>CValueAggregator</code> to let the user specify ' \
              'Python logic that should be applied to the incoming values. In contrast with ' \
              '<code>CValueAggregator</code>, this logic accepts only a single channel as an input - channel that ' \
              'the widget is bound to. In this example, we create a simple <code>CLabel</code> which decorates the ' \
              'incoming value by wrapping it between "&lt;&lt; &gt;&gt;" before displaying it.'

entrypoint = 'app.ui'
japc_generator = 'japc_device:create_device'
