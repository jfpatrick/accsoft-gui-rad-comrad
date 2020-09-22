title = 'Custom update source with CScrollingPlot'
description = \
    'This example shows how to split several values incoming from a single device property fields as an array' \
    'into separate curves, creating custom update sources to serve individual curves. The plot will have a ' \
    'dynamic amount of curves (5 max, the capacity of the array), based on what values are incoming. This ' \
    'example is similar to the real life Linac 3 injection event graph. The Device named "DemoDevice" has a ' \
    'single property "Acquisition" with a single field titled "injection", that emits an array of floats,' \
    'where zeros are disregarded as not active curves. On the GUI side, custom update source class, called ' \
    '"GateDataSource" is created. Its job is to receive the array and split it into output sources, that are ' \
    "created dynamically and are bound with the plot's curves."

entrypoint = 'app.py'
japc_generator = 'japc_device:create_device'
