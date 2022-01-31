CChannel
=====================

Monkey-patched verion of :class:`PyDMChannel` that allows proactive request for data from the control system.
It adds ``requested_slot`` and ``requested_signal`` properties and also allows to transmit context information
by attaching :class:`~comrad.data.context.CContext` objects.

.. autoclass:: comrad.data.channel.CChannel
   :members: context
