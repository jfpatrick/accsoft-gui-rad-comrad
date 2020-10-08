title = 'Custom update source with CValueAggregator'
description = \
    'This example shows how to use CValueAggregator in order to fuse information from several property ' \
    'fields into a calculated product. While single line time series can be served by ' \
    'CValueAggregator directly via signal-slot connection, producing multiple lines with different ' \
    'calculated products requires more work with custom update sources. The plot will display 4 lines: ' \
    'raw data from both fields (configured in Designer), and 2 calculated products from the same channels fused by ' \
    'CValueAggregator (connected programmatically). CValueAggregator and its forwarding logic also reside in the ' \
    'Designer file. The Device named "DemoDevice" has a single property "Acquisition" with 2 fields titled ' \
    '"field1" and "field2", performed computations will be "average" for one product, and ratio (field1/field2) ' \
    'for another calculation product.'

entrypoint = 'app.py'
japc_generator = 'japc_device:create_device'
