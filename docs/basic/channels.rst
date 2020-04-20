Channels
========

Channels (name originally comes from EPICS) are the bridge between UI widgets and communication handlers,
called Data Plugins.

- `Overview`_
- `Cycle selectors`_
- `Connecting widgets`_

  * `Using ComRAD Designer`_

- `Alternative channel formats`_


Overview
--------

Channels are specified in the following format:

.. code-block::

   <protocol>://<channel address>

Where ``<protocol>`` is a unique identifier for a given Data Plugin and ``<channel address>`` varies from
plugin to plugin.

Currently, ComRAD supports 5 protocols: JAPC, RDA3, RDA, TGM, NO. All of them are piped through the same
PyJAPC plugin, therefore ``<channel address>`` format remains the same and follows CERN device-property model
notation, making the following cases possible:

.. code-block::

   protocol:///device/property
   protocol:///device/property#field
   protocol://service/device/property#field

.. note:: While CERN device-property model notation allows omitting ``<protocol>://``, here it is required
          in order for the Data Plugins system to recognize the appropriate handler.


Cycle selectors
---------------

This part deviates from the CERN standard for device-property model notation. Optionally, you can embed
cycle selector (e.g. timing user) information in the same string. Simply, append ``@`` followed by the cycle
selector identifier, e.g.:

.. code-block::

   japc:///myDevice/myProperty#myField@LHC.USER.ALL

Cycle selector always takes 3 components, separated by dots.



Connecting widgets
------------------

Most of the control-system enabled widgets have a property called ``channel`` (or similar in exceptional cases).
In order for a widget to display data (or send data) to a concrete device field, you assign a string address
of that field, e.g.:

.. code-block:: python

   my_widget.channel = 'japc:///myDevice/myProperty#myField'



Using ComRAD Designer
^^^^^^^^^^^^^^^^^^^^^

To connect a widget in ComRAD Designer, locate the property with the same name in the "Property Editor". There,
you can either enter a string value into the field, or click "..." button to open a Device Property dialog,
that allows you to discover devices and their structure. In the same dialog, you can select the protocol and
optionally assign a cycle selector.

.. figure:: ../img/device_selector_from_prop.png
   :align: center
   :alt: Device Property Dialog

   Device Property Dialog


Alternative channel formats
---------------------------

While ComRAD ships with only PyJAPC plugin at the moment, the architecture allows arbitrary amount of
Data Plugins to handle various communication types, such as HTTP, RDB, etc. This is enabled by the
architecture of PyDM, the underlying framework of ComRAD.
`More information <https://slaclab.github.io/pydm-tutorial/intro/data_arch.html>`__.

.. figure:: https://slaclab.github.io/pydm-tutorial/_images/architecture.png
   :align: center
   :alt: Data flux architecture

   Data flux architecture

It is possible to create your own Data Plugin, as long as it is assigned to a protocol that is not yet
reserved. To discover how to write your own Data Plugin, have a look at
:doc:`../advanced/dataplugins`.
