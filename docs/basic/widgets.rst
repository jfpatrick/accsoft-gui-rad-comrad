Widget overview
===============

ComRAD widgets in many cases are direct counterparts of the standard Qt Widgets
(e.g. :ref:`CLabel <clabellocal>` is merely a fancier :class:`QLabel`).
They can also be compound - constructed of several primitive Qt Widgets (e.g. :ref:`CLogConsole <clogconsolelocal>`),
or completely custom - PyQtGraph descendants are :class:`QGraphicsView` descendants.

All ComRAD widgets are C-prefixed, and follow the Q-prefix notation of Qt.

.. note:: The primary reason for C-prefixed names was the way Qt Designer displays custom widgets - it only
          can use class name as a widget display name. Thus, to differentiate ComRAD widget from regular Qt
          Widgets, e.g. "ComRAD Label" from "Label", we introduced C-prefix.

**Page contents:**

- `Widget categories`_
- `Index of widgets`_


Widget categories
-----------------

In ComRAD Designer they are placed in the sections that correspond to the standard Qt Designer widget organization:

- *Display widgets*
- *Buttons*
- *Input widgets*
- *Containers*

There are also new additional sections:

- *Charts*: for plotting widgets
- *Invisible widgets*: for widgets that are visible in Designer but hidden at runtime



Index of widgets
----------------

.. table::
   :widths: 50, 50

   ===================  ==================================================================
   **Display widgets**
   =======================================================================================
   CLabel |clabelwiki|
   ---------------------------------------------------------------------------------------
   |clabel|             .. _clabellocal:

                        Label that can display values in the read-only manner.
                        Normally, strings or numbers are expected from the control
                        system.
   CByteIndicator |cbyteindicatorwiki|
   ---------------------------------------------------------------------------------------
   |cbyteindicator|     Array of bits that can display binary values ("ON" / "OFF").
                        Bits can be named individually. You can adjust the number of
                        bits displayed, but no gaps are intended, i.e. if you wish to
                        display only 1st, 3rd and 5th bit, consider converting them to
                        individual boolean fields. This widget can work with **booleans**
                        for a single bit, **integers** representing the array of bits in
                        binary notation, or **BitEnums**.
   CLogConsole |clogconsolewiki|
   ---------------------------------------------------------------------------------------
   |clogconsole|        .. _clogconsolelocal:

                        | **Note! This component is not related to the logs**
                          **control system, such as Timber / CALS / NXCALS.**
                        |

                        Log console simply captures conventional Python
                        :class:`logging.Logger` output to display messages in the UI, when
                        console output cannot be seen, e.g. when launched form CCM. These
                        loggers are the same ones that are usually used to print console
                        messages (do not confuse with :func:`print` function), so you can
                        capture stdout and stderr output here.
   CScaleIndicator |cscaleindicatorwiki|
   ---------------------------------------------------------------------------------------
   |cscaleindicator|    Scale Indicator is a read-only slider that displays the numeric
                        value in perspective with pre-configured range.
   CLed |cledwiki|
   ---------------------------------------------------------------------------------------
   |cled|               Basic LED that displays a circle with certain fill color. It can
                        display a color based on incoming boolean value, but altering
                        between :attr:`~comrad.CLed.onColor` and
                        :attr:`~comrad.CLed.offColor`, or the Enum value, by comparing its
                        "meaning" field with the predefined status options:
                        :obj:`~comrad.data.japc_enum.CEnumValue.Meaning.ON`,
                        :obj:`~comrad.data.japc_enum.CEnumValue.Meaning.OFF`,
                        :obj:`~comrad.data.japc_enum.CEnumValue.Meaning.WARNING`,
                        :obj:`~comrad.data.japc_enum.CEnumValue.Meaning.ERROR` or
                        :obj:`~comrad.data.japc_enum.CEnumValue.Meaning.NONE`.
   ===================  ==================================================================


.. table::
   :widths: 35, 65

   ===================  ==================================================================
   **Buttons**
   =======================================================================================
   CCheckBox |ccheckboxwiki|
   ---------------------------------------------------------------------------------------
   |ccheckbox|          Checkbox allows you setting **boolean** or **integer** (0 or 1)
                        value in the control system.
   CEnumButton |cenumbuttonwiki|
   ---------------------------------------------------------------------------------------
   |cenumbutton|        This button creates a button group (similar to radio button
                        group). It is similar to combobox but has possible options at
                        hand. Each button can send a predetermined value to the control
                        system.
   CCommandButton |ccommandbuttonwiki|
   ---------------------------------------------------------------------------------------
   |ccommandbutton|     Command button is meant to issue commands. In contrast with other
                        buttons, it can operate on the property level, not field. Because
                        commands are properties with no fields inside them, this button
                        issues a SET instruction to a property without any value.
   CPushButton |cpushbuttonwiki|
   ---------------------------------------------------------------------------------------
   |cpushbutton|        Push button can send a predefined value to the control system.
   CRelatedDisplayButton |crelateddisplaywiki|
   ---------------------------------------------------------------------------------------
   |crelateddisplay|    Related display is a navigation button, which is not related to
                        the control system. It can either open a new ComRAD window with
                        another dashboard (e. g. details screen of a particular device),
                        or replace the current window with a new dashboard.
   CShellCommand |cshellcommandwiki|
   ---------------------------------------------------------------------------------------
   |cshellcommand|      Shell command button can issue a local Linux command, such as
                        launching external scripts, processes or applications.
   ===================  ==================================================================


.. table::
   :widths: 40, 60

   ===================  ==================================================================
   **Input widgets**
   =======================================================================================
   CEnumComboBox |cenumcomboboxwiki|
   ---------------------------------------------------------------------------------------
   |cenumcombobox|      This combobox is similar to CEnumButton but displays options in
                        the drop-down menu.
   CLineEdit |clineeditwiki|
   ---------------------------------------------------------------------------------------
   |clineedit|          Single-line string editor that allows propagating a string or
                        numeric value into the control system. The changes are submitted
                        when the user presses "Enter".
   CSlider |csliderwiki|
   ---------------------------------------------------------------------------------------
   |cslider|            Slider allows adjusting a numeric value in the control system,
                        given the possible range.
   CSpinBox |cspinboxwiki|
   ---------------------------------------------------------------------------------------
   |cspinbox|           Spinbox allows altering a numeric value with a certain step
                        between adjacent values. The changes are submitted when the user
                        presses "Enter".
   CPropertyEdit |cpropertyeditwiki|
   ---------------------------------------------------------------------------------------
   |cpropertyedit|      Property edit allows interacting with multiple fields of the same
                        property. Its main advantage is that it allows writing (or
                        getting) fields in an atomic way with a single button click. By
                        default it will layout widgets in a form, picking the best
                        matching widget for each of the field types. However, it is
                        possible to customize both layout and rendered widgets via the
                        delegate system. **Note! CPropertyEdit is not and should not be
                        treated as a convenience that removes the need placing several
                        widgets (one per field). It will not support all the features that
                        individual widgets offer (e.g.** :doc:`widget rules <rules>` **for
                        individual fields).**
   ===================  ==================================================================


.. table::
   :widths: 35, 65

   ===================  ==================================================================
   **Containers**
   =======================================================================================
   CEmbeddedDisplay |cembeddeddisplaywiki|
   ---------------------------------------------------------------------------------------
   |cembeddeddisplay|   Embedded Display renders another file (either \*.ui or Python file
                        with CDisplay subclass defined) inside a frame. It allows nesting
                        displays inside each other. Embedded file can receive customized
                        variables via the :doc:`macros <macros>` system.
   CTemplateRepeater |ctemplaterepeaterwiki|
   ---------------------------------------------------------------------------------------
   |ctemplaterepeater|  Template repeater is a special kind of Embedded Display that
                        allows creating multiple instances of the same display,
                        customizing each of them via the :doc:`macros <macros>` system.
                        For instance, you can display information about multiple devices
                        side by side without duplicating UI during development.
   CContextFrame |ccontextframewiki|
   ---------------------------------------------------------------------------------------
   |ccontextframe|      This container allows to update its child widgets with a new
                        control-system context by redefining context-related properties,
                        such as cycle selector or data filters. This allows a group of
                        widgets to connect in a different way than the rest of the
                        application (application-level cycle selector is chosen via
                        PLS toolbar button, and data filters are undefined by default).
   ===================  ==================================================================


.. table::
   :widths: 60, 40

   ===================  ==================================================================
   **Charts**
   =======================================================================================
   CScrollingPlot |cscrollingplotwiki|
   ---------------------------------------------------------------------------------------
   |cscrollingplot|     Scrolling plot displays live data that is arriving from the
                        control system in real time. This data can be represented in
                        multiple ways, e.g. as lines, bar graph, injection marks, etc.
                        Data can either contain a timestamp to be precise about timing, or
                        such timestamp will be created whenever the widget receives the
                        data.
   CCyclicPlot |ccyclicplotwiki|
   ---------------------------------------------------------------------------------------
   |ccyclicplot|        Cyclic plot is meant to scroll through the same cycle updating the
                        previous display, similar to how heart monitors do it. It is
                        useful for displaying data in the context of a cycle of the
                        injector / accelerator.
   CStaticPlot |cstaticplotwiki|
   ---------------------------------------------------------------------------------------
   |cstaticplot|        Static plot is not moving with time and allows replacing the
                        entire contents of the graph, rather than appending points to the
                        existing data set. This makes it perfect for displaying waveforms,
                        frequencies, or simply graphs that are recalculated on every tick.
   ===================  ==================================================================


.. table::
   :widths: 20, 80

   =====================  ==================================================================
   **Invisible widgets**
   =========================================================================================
   CValueAggregator |cvalueaggregatorwiki|
   -----------------------------------------------------------------------------------------
   |cvalueaggregator|     Hidden widget that allows combine data from multiple sources to
                          produce a single output using Python code to describe logic. See
                          :doc:`transform` for more information.
   =====================  ==================================================================


.. |clabel| image:: ../img/widget_clabel.png
.. |cbyteindicator| image:: ../img/widget_cbyteindicator.png
.. |clogconsole| image:: ../img/widget_clogconsole.png
.. |cscaleindicator| image:: ../img/widget_cscaleindicator.png
.. |ccheckbox| image:: ../img/widget_ccheckbox.png
.. |cled| image:: ../img/widget_cled.png
.. |cenumbutton| image:: ../img/widget_cenumbutton.png
.. |ccommandbutton| image:: ../img/widget_ccommandbutton.png
.. |cpushbutton| image:: ../img/widget_cpushbutton.png
.. |crelateddisplay| image:: ../img/widget_crelateddisplay.png
.. |cshellcommand| image:: ../img/widget_cshellcommand.png
.. |cenumcombobox| image:: ../img/widget_ccombobox.png
.. |clineedit| image:: ../img/widget_clineedit.png
.. |cslider| image:: ../img/widget_cslider.png
.. |cspinbox| image:: ../img/widget_cspinbox.png
.. |cpropertyedit| image:: ../img/widget_cpropertyedit.png
.. |cembeddeddisplay| image:: ../img/widget_cembeddeddisplay.png
.. |ctemplaterepeater| image:: ../img/widget_ctemplaterepeater.png
.. |ccontextframe| image:: ../img/widget_ccontextframe.png
.. |cscrollingplot| image:: ../img/widget_cscrollingplot.png
.. |ccyclicplot| image:: ../img/widget_ccyclicplot.png
.. |cstaticplot| image:: ../img/widget_cstaticplot.png
.. |cvalueaggregator| image:: ../img/widget_cvalueaggregator.png

.. |clabelwiki| raw:: html

    <a href="../api/widgets/clabel.html" class="apibutton">More details...</a>

.. |cbyteindicatorwiki| raw:: html

    <a href="../api/widgets/cbyteindicator.html" class="apibutton">More details...</a>

.. |cvalueaggregatorwiki| raw:: html

    <a href="../api/widgets/cvalueaggregator.html" class="apibutton">More details...</a>

.. |cstaticplotwiki| raw:: html

    <a href="../api/widgets/graphs/cstaticplot.html" class="apibutton">More details...</a>

.. |ccyclicplotwiki| raw:: html

    <a href="../api/widgets/graphs/ccyclicplot.html" class="apibutton">More details...</a>

.. |cscrollingplotwiki| raw:: html

    <a href="../api/widgets/graphs/cscrollingplot.html" class="apibutton">More details...</a>

.. |ccontextframewiki| raw:: html

    <a href="../api/widgets/ccontextframe.html" class="apibutton">More details...</a>

.. |ctemplaterepeaterwiki| raw:: html

    <a href="../api/widgets/ctemplaterepeater.html" class="apibutton">More details...</a>

.. |cembeddeddisplaywiki| raw:: html

    <a href="../api/widgets/cembeddeddisplay.html" class="apibutton">More details...</a>

.. |cpropertyeditwiki| raw:: html

    <a href="../api/widgets/cpropertyedit.html" class="apibutton">More details...</a>

.. |cspinboxwiki| raw:: html

    <a href="../api/widgets/cspinbox.html" class="apibutton">More details...</a>

.. |csliderwiki| raw:: html

    <a href="../api/widgets/cslider.html" class="apibutton">More details...</a>

.. |cenumcomboboxwiki| raw:: html

    <a href="../api/widgets/cenumcombobox.html" class="apibutton">More details...</a>

.. |ccommandbuttonwiki| raw:: html

    <a href="../api/widgets/ccommandbutton.html" class="apibutton">More details...</a>

.. |cpushbuttonwiki| raw:: html

    <a href="../api/widgets/cpushbutton.html" class="apibutton">More details...</a>

.. |clineeditwiki| raw:: html

    <a href="../api/widgets/clineedit.html" class="apibutton">More details...</a>

.. |cshellcommandwiki| raw:: html

    <a href="../api/widgets/cshellcommand.html" class="apibutton">More details...</a>

.. |cenumbuttonwiki| raw:: html

    <a href="../api/widgets/cenumbutton.html" class="apibutton">More details...</a>

.. |crelateddisplaywiki| raw:: html

    <a href="../api/widgets/crelateddisplaybutton.html" class="apibutton">More details...</a>

.. |ccheckboxwiki| raw:: html

    <a href="../api/widgets/ccheckbox.html" class="apibutton">More details...</a>

.. |clogconsolewiki| raw:: html

    <a href="../api/widgets/clogconsole.html" class="apibutton">More details...</a>

.. |cscaleindicatorwiki| raw:: html

    <a href="../api/widgets/cscaleindicator.html" class="apibutton">More details...</a>

.. |cledwiki| raw:: html

    <a href="../api/widgets/cled.html" class="apibutton">More details...</a>