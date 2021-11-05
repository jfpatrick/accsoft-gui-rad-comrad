title = 'Custom update source with CScrollingPlot'
description = \
    'This example shows how to split several values incoming from a single device property fields as an array ' \
    'into separate curves, creating custom update sources to serve individual curves. The plot will have a ' \
    'dynamic amount of curves (5 max, the capacity of the array), based on what values are incoming. This ' \
    'example is similar to the real life LINAC3 injection event graph. The Device named "DemoDevice" has a ' \
    'single property "Acquisition" with a single field titled "injection", that emits an array of floating point ' \
    'values, where zeros are disregarded. On the GUI side, custom <code>UpdateSource</code> class, called ' \
    '<code>GateDataSource</code> is created. Its job is to receive the array and split it into output sources ' \
    "that are created dynamically and are bound with the plot's curves."

entrypoint = 'app.py'
japc_generator = 'japc_device:create_device'
