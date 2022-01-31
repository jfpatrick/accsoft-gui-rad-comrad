.. rst_epilog sometimes fails, so we need to include this explicitly, for colors
.. include:: <s5defs.txt>


.. _cspinbox:


CSpinBox
=====================

- `Description`_

  * `Supported data types`_
  * `Inheritance diagram`_

- `API reference`_

Description
-----------

.. image:: ../../img/widget_cspinbox.png

:class:`~comrad.CSpinBox` allows altering a numeric value with a certain step between adjacent values. The changes
are submitted when the user presses “Enter”.

.. note:: While Qt framework has different classes (:class:`QSpinBox` and :class:`QDoubleSpinBox` for integer and
          floating-point values respectively), :class:`~comrad.CSpinBox` defaults to floating-point enabled parent.

You can connect it to the control system by setting its :attr:`~comrad.CSpinBox.channel` value to the address of
your device-property's field.

.. seealso:: :ref:`What is a channel? <basic/controls:Channels>`

For floating point values it is also important to note the :attr:`~comrad.CSpinBox.precision` property that limits
the amount of digits after decimal point. Note that by default it's set to 0, thus hiding fractional part of the number.

:class:`~comrad.CSpinBox` supports client-side data transformations via
:attr:`~comrad.CSpinBox.valueTransformation` that lets you modify displayed value with a piece of Python code.

.. seealso:: :doc:`What is client-side data transformations? <../../basic/transform>`

Supported data types
^^^^^^^^^^^^^^^^^^^^

============  ============  ============  ============  ============  =========  =========  =========  =========  ==========  =========  =========  ==========  ===========  ===========  ============  ==========  ===========  ============  =============  =============  ==============
short         int           long          float         double        string     boolean    enum       enumSet    shortArray  intArray   longArray  floatArray  doubleArray  stringArray  booleanArray  intArray2D  longArray2D  floatArray2D  doubleArray2D  stringArray2D  booleanArray2D
------------  ------------  ------------  ------------  ------------  ---------  ---------  ---------  ---------  ----------  ---------  ---------  ----------  -----------  -----------  ------------  ----------  -----------  ------------  -------------  -------------  --------------
:green:`Yes`  :green:`Yes`  :green:`Yes`  :green:`Yes`  :green:`Yes`  :red:`No`  :red:`No`  :red:`No`  :red:`No`  :red:`No`   :red:`No`  :red:`No`  :red:`No`   :red:`No`    :red:`No`    :red:`No`     :red:`No`   :red:`No`    :red:`No`     :red:`No`      :red:`No`      :red:`No`
============  ============  ============  ============  ============  =========  =========  =========  =========  ==========  =========  =========  ==========  ===========  ===========  ============  ==========  ===========  ============  =============  =============  ==============


Inheritance diagram
^^^^^^^^^^^^^^^^^^^

.. inheritance-diagram:: comrad.CSpinBox
    :parts: 1
    :top-classes: PyQt5.QtWidgets.QDoubleSpinBox


API reference
-------------

.. autoclass:: comrad.CSpinBox
    :members:
    :inherited-members:
