
``values`` is a dictionary, where keys are addresses of the respective channels. Similarly, ``headers`` dictionary will
contain the very same keys, but with meta-information stored in there. This allows you to produce a single output value
from multiple input values. For instance, consider a device property "device/property" that has fields "voltage" and
"current". If we want to display the power in a label, we can make a :class:`~comrad.CValueAggregator` widget and
connect it to 2 channels: ``device/property#votlage``, ``device/property#current``. Now, we create a transformation
with the code below:

.. code-block:: python

   V = values['device/property#votlage']
   I = values['device/property#current']
   output(V * I)

and connect :meth:`CValueAggregator.updateTriggered(double) <comrad.CValueAggregator.updateTriggered>` signal to
:meth:`QLabel.setNum` slot.

In case when you have only one channel connected to the :class:`~comrad.CValueAggregator` and you don't
want to be bound to its name, the easy way to extract the value from the dictionary is using iterators:

.. code-block:: python

   try:
       val = next(iter(values.values()))
   except StopIteration:
       val = None  # Handle the case on startup, when no value has arrived from the control system yet.
   output(val)
