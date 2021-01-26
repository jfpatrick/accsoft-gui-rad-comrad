title = 'Custom update source with CValueAggregator'
description = \
    'This example shows how to use <code>CValueAggregator</code> in order to fuse information from several property ' \
    'fields into a calculated product. While single line time series can be served by ' \
    '<code>CValueAggregator</code> directly via signal-slot connection, producing multiple lines with different ' \
    'calculated products requires more work with custom update sources. The plot will display 4 lines: ' \
    'raw data from both fields (configured in Designer), and 2 calculated products from the same channels fused by ' \
    '<code>CValueAggregator</code> (connected programmatically). <code>CValueAggregator</code> and its forwarding ' \
    'logic also reside in the Designer file. The device named "DemoDevice" has a single property "Acquisition" with ' \
    '2 fields titled "field1" and "field2". Performed computations will be <i>average</i> for one product, and ' \
    '<i>ratio</i> (<code>field1 / field2</code>) for another calculation product.'

entrypoint = 'app.py'
japc_generator = 'japc_device:create_device'
