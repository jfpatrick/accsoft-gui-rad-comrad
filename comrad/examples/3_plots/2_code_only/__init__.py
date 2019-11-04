title = "Code only display with graphs displaying different plotting items"
description = \
    'This example shows how to create a display containing a Scrolling Graph and a Sliding Pointer Graph ' \
    'without the usage of Qt Designer UI files. ' \
    'These plots contain different types of data representations like line graphs, bar graphs, injection ' \
    'bar graphs and timestamp marker that are connected to different fields of a single device. The Device ' \
    'named "DemoDevice" has a single property "Acquisition" with four fields titled "RandomPoint", ' \
    '"RandomBar", "RandomInjectonBar" and "RandomTimestampMarker", which emit lists of different values ' \
    'representing a timestamp and other metrics that are then displayed by the connected item.'

entrypoint = "app.py"
japc_generator = "japc_device:create_device"
