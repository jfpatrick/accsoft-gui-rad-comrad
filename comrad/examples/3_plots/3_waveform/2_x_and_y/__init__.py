title = 'Plot Widget displaying a waveform curve with x and y values.'
description = \
    'This example shows how to create a display containing a static plot ' \
    'which displays a waveform curve using only Qt Designer UI files. ' \
    'The shown curve is connected to a field "Curve" of a Device ' \
    '"DemoDevice", which is emitting an 2 dimensional array containing the ' \
    'x and y values of a sinus curve. Over time this sinus curve will scale ' \
    'smaller and bigger to provide a changing appearance.'

entrypoint = 'app.ui'
japc_generator = 'japc_device:create_device'
