title = 'Plot Widget displaying a waveform curve built with Qt Designer.'
description = \
    'This example shows how to create a display containing a <code>CStaticPlot</code>, ' \
    'which displays a waveform curve using only Qt Designer. The shown curve is connected to a field "Curve" of ' \
    'a Device "DemoDevice" that is emits an array containing the Y-values of a sinus curve. Over time this sinus ' \
    'curve will scale smaller and bigger to provide a changing appearance.'

entrypoint = 'app.ui'
japc_generator = 'japc_device:create_device'
