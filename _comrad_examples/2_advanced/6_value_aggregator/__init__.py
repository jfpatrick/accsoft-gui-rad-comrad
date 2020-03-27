title = 'Basic CValueAggregator example'
description = 'CValueAggregator is a special widget that is hidden at the runtime, but can be added via Designer ' \
              'at design time to embed custom Python logic and connect signals/slots to related widgets. This widget ' \
              'allows receiving data from multiple channels and produce a single output. In this example we will ' \
              'connect CValueAggregator to 2 channels emitting numerical value and produce a mathematical sum as an ' \
              'output.'

entrypoint = 'app.ui'
japc_generator = 'japc_device:create_device'
