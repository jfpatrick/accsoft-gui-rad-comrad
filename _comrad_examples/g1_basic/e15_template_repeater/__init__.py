title = 'Basic CTemplateRepeater example'
description = 'This example shows how to create a composite UI, which reuses parts of the interface defined ' \
              'in different files, similar to <code>CEmbeddedDisplay</code>. The only difference is that this ' \
              'component allows creating repetitive components of the UI, which comes especially useful with macros ' \
              'functionality (see <strong>2. Advanced</strong> examples). You can, for instance, create a file that ' \
              'displays details of a device, and multiply UI for several devices through template repeater. In this ' \
              'example, we are creating a template to be used with 2 devices, that emit "Acquisition#IntVal" ' \
              'numeric field once a second.'

entrypoint = 'app.ui'
japc_generator = 'japc_device:create_device'
