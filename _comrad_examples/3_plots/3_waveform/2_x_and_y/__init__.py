title = 'Plot Widget displaying a waveform curve with x and y values.'
description = \
    'This example shows how to create a display containing a <code>CStaticPlot</code>, ' \
    'which displays a waveform curve using only Qt Designer. ' \
    'The shown curve is connected to a field "Curve" of a Device ' \
    '"DemoDevice", which emits a 2-dimensional array containing the ' \
    'X- and Y-values of a sinus curve. Over time this sinus curve will scale ' \
    'smaller and bigger to provide a changing appearance.'

entrypoint = 'app.ui'
japc_generator = 'japc_device:create_device'
