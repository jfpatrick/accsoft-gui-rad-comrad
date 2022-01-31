.. rst_epilog sometimes fails, so we need to include this explicitly, for colors
.. include:: <s5defs.txt>

.. _cscaleindicator:

CScaleIndicator
=====================

- `Description`_

  * `Supported data types`_
  * `Inheritance diagram`_

- `API reference`_

Description
-----------

.. image:: ../../img/widget_cscaleindicator.png

:class:`~comrad.CScaleIndicator` is a bar-shaped indicator for numerical values  in perspective with pre-configured
range. It is a non-interactive (read-only) widget. If you are looking for a bar or slider for setting values, refer
to :ref:`cslider`.

You can display a value from the control system inside :class:`~comrad.CScaleIndicator` by setting its
:attr:`~comrad.CScaleIndicator.channel` value to the address of your device-property's field.

.. seealso:: :ref:`What is a channel? <basic/controls:Channels>`

When using the widget for decimal values it is important to note the :attr:`~comrad.CScaleIndicator.precision` property
that limits the amount of digits after decimal point. Note that by default it's set to 0, thus hiding fractional part
of the number.

:class:`~comrad.CScaleIndicator` supports client-side data transformations via
:attr:`~comrad.CScaleIndicator.valueTransformation` that lets you modify displayed value with a piece of Python code.

.. seealso:: :doc:`What is client-side data transformations? <../../basic/transform>`

Supported data types
^^^^^^^^^^^^^^^^^^^^

============  ============  ============  ============  ============  =========  =========  =========  =========  ==========  =========  =========  ==========  ===========  ===========  ============  ============  ============  ============  =============  =============  ==============
short         int           long          float         double        string     boolean    enum       enumSet    shortArray  intArray   longArray  floatArray  doubleArray  stringArray  booleanArray  intArray2D    longArray2D   floatArray2D  doubleArray2D  stringArray2D  booleanArray2D
------------  ------------  ------------  ------------  ------------  ---------  ---------  ---------  ---------  ----------  ---------  ---------  ----------  -----------  -----------  ------------  ------------  ------------  ------------  -------------  -------------  --------------
:green:`Yes`  :green:`Yes`  :green:`Yes`  :green:`Yes`  :green:`Yes`  :red:`No`  :red:`No`  :red:`No`  :red:`No`  :red:`No`   :red:`No`  :red:`No`  :red:`No`   :red:`No`    :red:`No`    :red:`No`     :red:`No`     :red:`No`     :red:`No`     :red:`No`      :red:`No`      :red:`No`
============  ============  ============  ============  ============  =========  =========  =========  =========  ==========  =========  =========  ==========  ===========  ===========  ============  ============  ============  ============  =============  =============  ==============


Inheritance diagram
^^^^^^^^^^^^^^^^^^^

.. inheritance-diagram:: comrad.CScaleIndicator
    :parts: 1
    :top-classes: PyQt5.QtWidgets.QFrame


API reference
-------------

.. autoclass:: comrad.CScaleIndicator
    :members:
    :inherited-members:
