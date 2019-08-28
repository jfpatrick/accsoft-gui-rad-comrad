title = 'Basic CByteIndicator example'
description = 'This example shows how to create a display that indicates bit enum values as well as integer' \
              'values from the control system. Byte indicator can display individual bits of an integer value ' \
              'as boolean values (0 or 1), as well as receive a list of enum values from JAPC "enum item sets". ' \
              'In this example, values are incremented by one like if it would be an integer value, so that it is ' \
              'easy to track the progression and ensure that individual bits are set to expected values. For ' \
              'convenience, labels show binary and decimal representations of the same values.'

entrypoint = 'app.ui'
japc_generator = 'japc_device:create_device'