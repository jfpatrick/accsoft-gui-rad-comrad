.. rst_epilog sometimes fails, so we need to include this explicitly, for colors
.. include:: <s5defs.txt>

.. _clogdisplay:


CLogDisplay
=====================

- `Description`_

  * `Supported data types`_
  * `Inheritance diagram`_

- `API reference`_

Description
-----------

.. image:: ../../img/widget_clogdisplay.png

:class:`~comrad.CLogDisplay` simply captures conventional Python :class:`logging.Logger` output to display messages
in the UI, when console output cannot be seen, e.g. when launched form CCM. These loggers are the same ones that are
usually used to print console messages (do not confuse with :func:`print` function), so you can capture ``stdout`` and
``stderr`` output here.

.. note:: This component is not related to the logs archive systems, such as Timber / CALS / NXCALS.

The level of the log can be changed from inside the widget itself, allowing users to select from any of the levels
specified by the widget.

.. note:: This widget suffers from a design problem, where it can actually override the log level of the parent
          :class:`~logging.Logger`, effectively altering console output of the application. It will likely be replaced
          with another implementation in the future.


Supported data types
^^^^^^^^^^^^^^^^^^^^

.. note:: This widget does not connect to the control system.

Inheritance diagram
^^^^^^^^^^^^^^^^^^^

.. inheritance-diagram:: comrad.CLogDisplay
    :parts: 1
    :top-classes: PyQt5.QtWidgets.QWidget


API reference
-------------

.. autoclass:: comrad.CLogDisplay
    :members:
    :inherited-members: