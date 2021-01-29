title = 'Min/max limits and units in CPropertyEdit'
description = '<code>CPropertyEdit</code> is capable recognizing FESA-level limits and units that are encoded ' \
              'with special fields, ending with <i>_min</i>, <i>_max</i>, <i>_units</i> suffixes. When a retrieved ' \
              'property contains such fields, they are automatically employed into editable numeric fields displayed ' \
              'by <code>CPropertyEdit</code> (considering standard <code>widget_delegate</code> is used). These ' \
              'special fields do not even need to be configured for display.<br/>' \
              '<br/>' \
              'In this example, the widget is configured to display two fields, "readOnlyField" and "writableField". ' \
              'Whilst the simulated JAPC device contains additional fields in the property: "readOnlyField_min", ' \
              '"readOnlyField_max", "readOnlyField_units", "writableField_min", "writableField_max", ' \
              '"writableField_units". This information will be implicitly applied to <code>CPropertyEdit</code> ' \
              'inner widgets, corresponding to the configured fields. It only does so on numeric field types ' \
              '(<code>INTEGER</code> and <code>REAL</code>).'

entrypoint = 'app.ui'
japc_generator = 'japc_device:create_device'
