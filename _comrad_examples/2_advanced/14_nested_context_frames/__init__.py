title = 'Example of nesting multiple CContextFrames inside each other'
description = 'CContextFrame is a way of encapsulating connection-related information for the group of widgets. ' \
              'It allows to either override or augment the global context with new bits of information. In this example, ' \
              'there are two groups. On the left, each CContextFrame overrides pre-set selector with its own value. In ' \
              'the right hand side, the parent CContextFrame propagates the selector defined by the window, while ' \
              'the child CContextFrame enforces "no selector".'

entrypoint = 'app.ui'
japc_generator = 'japc_device:create_device'
launch_arguments = ['--selector', 'PSB.USER.AD']
