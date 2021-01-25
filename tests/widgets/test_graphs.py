import pytest
import json
import logging
import numpy as np
from typing import List, cast
from logging import LogRecord
from freezegun import freeze_time
from datetime import datetime
from dateutil.tz import tzoffset
from pytestqt.qtbot import QtBot
from _pytest.logging import LogCaptureFixture
from unittest import mock
from qtpy.QtCore import QObject, Qt
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QWidget, QVBoxLayout
from comrad import CCyclicPlot, CScrollingPlot, CStaticPlot, PointData, CContextFrame, CChannelData
from comrad.data.context import find_context_provider
from comrad.widgets.graphs import (PyDMChannelDataSource, CPlotWidgetBase, CItemPropertiesBase, UpdateSource,
                                   AbstractBasePlotCurve, PlottingItemTypes, DEFAULT_BUFFER_SIZE,
                                   CScrollingCurve, CScrollingBarGraph, CScrollingTimestampMarker,
                                   CScrollingInjectionBarGraph, CCyclicCurve, CStaticTimestampMarker,
                                   CStaticInjectionBarGraph, CStaticBarGraph, CStaticCurve)


TZ = tzoffset('UTC+0', 0)
STATIC_TIME = datetime(year=2020, day=1, month=1, tzinfo=TZ)


def fake_data_source():
    class FakeDataSource(UpdateSource):
        pass
    return FakeDataSource()


@pytest.mark.parametrize('is_context_tracker,should_install_on_parent', [
    (True, True),
    (False, False),
])
@pytest.mark.parametrize('widget_type', [
    CScrollingPlot,
    CCyclicPlot,
    CStaticPlot,
])
def test_pydmchanneldatasource_installs_filter_on_parent_widget(qtbot: QtBot, widget_type, is_context_tracker, should_install_on_parent):
    widget = widget_type()
    qtbot.add_widget(widget)
    with mock.patch('accwidgets.graph.UpdateSource.installEventFilter') as data_source_call:
        data_source = PyDMChannelDataSource(parent=widget, channel_address='dev/prop#field', data_type_to_emit=PointData)
        filter = data_source._context_tracker if is_context_tracker else QObject()
        with mock.patch.object(widget, 'installEventFilter') as widget_call:
            data_source.installEventFilter(filter)
            if should_install_on_parent:
                widget_call.assert_called_once()
                data_source_call.assert_not_called()
            else:
                widget_call.assert_not_called()
                data_source_call.assert_called_once()


@pytest.mark.parametrize('init_ch,new_ch,expected_ch', [
    ('dev/prop/#field', 'dev2/prop#field', 'dev2/prop#field'),
    ('dev/prop/#field', 'dev/prop#field', 'dev/prop#field'),
])
def test_pydmchanneldatasource_address(init_ch, new_ch, expected_ch):
    data_source = PyDMChannelDataSource(channel_address=init_ch, data_type_to_emit=PointData)
    assert data_source.address == init_ch
    assert data_source._channel == init_ch
    data_source.address = new_ch
    assert data_source.address == expected_ch
    assert data_source._channel == expected_ch


@pytest.mark.parametrize('widget_type', [
    CScrollingPlot,
    CCyclicPlot,
    CStaticPlot,
])
@mock.patch('pydm.widgets.channel.PyDMChannel.connect')
@mock.patch('comrad.CContextFrame.context_ready', return_value=True)
def test_pydmchanneldatasource_connects_on_show(_, connect, qtbot: QtBot, widget_type):
    ctx_provider = CContextFrame()
    qtbot.add_widget(ctx_provider)
    ctx_provider.setLayout(QVBoxLayout())
    widget = widget_type()
    ctx_provider.layout().addWidget(widget)
    data_source = PyDMChannelDataSource(parent=widget, channel_address='dev/prop#field', data_type_to_emit=PointData)
    assert len(data_source._channels) == 0
    assert data_source._channel_ids == ['dev/prop#field']
    connect.assert_not_called()
    ctx_provider.show()
    assert len(data_source._channels) == 1
    assert data_source._channel_ids == ['dev/prop#field']
    connect.assert_called_once()


@pytest.mark.parametrize('widget_type', [
    CScrollingPlot,
    CCyclicPlot,
    CStaticPlot,
])
@mock.patch('comrad.widgets.graphs.PyDMChannelDataSource.installEventFilter')
def test_pydmchanneldatasource_can_locate_parent_context_provider(_, qtbot: QtBot, widget_type):
    ctx_provider = CContextFrame()
    qtbot.add_widget(ctx_provider)
    ctx_provider.setLayout(QVBoxLayout())
    container = QWidget()
    container.setLayout(QVBoxLayout())
    ctx_provider.layout().addWidget(container)
    widget = widget_type()
    container.layout().addWidget(widget)
    data_source = PyDMChannelDataSource(parent=widget, channel_address='dev/prop#field', data_type_to_emit=PointData)
    received_ctx_provider = find_context_provider(data_source)
    assert received_ctx_provider == ctx_provider


@freeze_time(STATIC_TIME)
@pytest.mark.parametrize('input,last_val,output,should_send', [
    (None, None, None, False),
    ([], None, None, False),
    ((), None, None, False),
    ({}, None, None, False),
    (np.array([]), None, None, False),
    (np.array([1]), None, PointData(x=STATIC_TIME.timestamp(), y=1), True),
    (np.array([1]), np.array([1]), None, False),
    (np.array([2]), np.array([1]), PointData(x=STATIC_TIME.timestamp(), y=2), True),
    ([], None, None, False),
    ([1], None, PointData(x=STATIC_TIME.timestamp(), y=1), True),
    ([1], [1], None, False),
    ([2], [1], PointData(x=STATIC_TIME.timestamp(), y=2), True),
    ([1], np.array([1]), None, False),
    ([2], np.array([1]), PointData(x=STATIC_TIME.timestamp(), y=2), True),
    (np.array([1]), [1], None, False),
    (np.array([2]), [1], PointData(x=STATIC_TIME.timestamp(), y=2), True),
    ((), None, None, False),
    ((1,), None, PointData(x=STATIC_TIME.timestamp(), y=1), True),
    ((1,), (1,), None, False),
    ((2,), (1,), PointData(x=STATIC_TIME.timestamp(), y=2), True),
    ((1,), [1], PointData(x=STATIC_TIME.timestamp(), y=1), True),
    ((2,), [1], PointData(x=STATIC_TIME.timestamp(), y=2), True),
    ([1], (1,), PointData(x=STATIC_TIME.timestamp(), y=1), True),
    ([2], (1,), PointData(x=STATIC_TIME.timestamp(), y=2), True),
    (5, 5, None, False),
    (5, 4, PointData(x=STATIC_TIME.timestamp(), y=5), True),
    (5.5, 5.5, None, False),
    (5.5, 4.5, PointData(x=STATIC_TIME.timestamp(), y=5.5), True),
])
def test_pydmchanneldatasource_transforms_value_into_correct_format(input, last_val, output, should_send, qtbot: QtBot):
    data_source = PyDMChannelDataSource(channel_address='dev/prop#field', data_type_to_emit=PointData)
    data_source._last_value = last_val
    with qtbot.wait_signal(data_source.sig_new_data, raising=should_send, timeout=100) as blocker:
        data_source.value_updated(CChannelData(value=input, meta_info={}))
    if should_send:
        print(f'Received {blocker.args[0].x},{blocker.args[0].y}')
        print(f'Expected {output.x},{output.y}')
        assert blocker.args == [output]
    else:
        assert blocker.args is None


def test_cplotwidgetbase_forbids_weird_subclasses(caplog: LogCaptureFixture):

    class WeirdSubclass(QObject, CPlotWidgetBase):
        pass

    assert len(caplog.records) == 0

    WeirdSubclass()

    actual_warnings = [r.msg for r in cast(List[LogRecord], caplog.records) if r.levelno == logging.WARNING]
    assert actual_warnings == ['CPlotWidgetBase implementation relies on attributes provided by ExPlotWidget. '
                               'Use CPlotWidgetBase only as base class of classes derived from ExPlotWidget.']


# Amount of options limited to keep a sane number of dynamicly generated test cases (currently ~1.5k for this one alone)
@pytest.mark.parametrize('data_source', [None, UpdateSource(), 'dev/prop#field'])
@pytest.mark.parametrize('layer', [None, 'mylayer'])
@pytest.mark.parametrize('color', [None, QColor(255, 255, 0)])
@pytest.mark.parametrize('name', [None, 'custom-name'])
@pytest.mark.parametrize('symbol', [None, 'o'])
@pytest.mark.parametrize('symbol_size', [None, 10])
@pytest.mark.parametrize('line_style', [None, Qt.SolidLine])
@pytest.mark.parametrize('line_width', [None, 10])
@pytest.mark.parametrize('widget_type', [
    CScrollingPlot,
    CCyclicPlot,
    CStaticPlot,
])
@mock.patch('comrad.ExPlotWidget.addCurve', return_value='addCurveResult')
def test_addcurve(addCurve, qtbot, widget_type, data_source, layer, color,
                  name, symbol, symbol_size, line_style, line_width):
    widget = widget_type()
    qtbot.add_widget(widget)

    if layer:
        widget.add_layer(layer)

    with mock.patch.object(widget, 'add_channel_attached_item', return_value='channelAttachedResult') as add_channel_attached_item:
        item = widget.addCurve(data_source=data_source,
                               layer=layer,
                               color=color,
                               name=name,
                               symbol=symbol,
                               symbol_size=symbol_size,
                               line_style=line_style,
                               line_width=line_width)
        if isinstance(data_source, str):
            assert item == 'channelAttachedResult'
            add_channel_attached_item.assert_called_once_with(style=PlottingItemTypes.LINE_GRAPH.value,
                                                              channel_address=data_source,
                                                              layer=layer,
                                                              color=color,
                                                              name=name,
                                                              symbol=symbol,
                                                              symbol_size=symbol_size,
                                                              line_style=line_style,
                                                              line_width=line_width)
            addCurve.assert_not_called()
        else:
            assert item == 'addCurveResult'
            add_channel_attached_item.assert_not_called()
            addCurve.assert_called_once_with(widget,
                                             c=None,
                                             params=None,
                                             data_source=data_source,
                                             layer=layer,
                                             buffer_size=DEFAULT_BUFFER_SIZE)


@pytest.mark.parametrize('data_source', [None, UpdateSource(), 'dev/prop#field'])
@pytest.mark.parametrize('layer', [None, 'mylayer'])
@pytest.mark.parametrize('color', [None, QColor(255, 255, 0)])
@pytest.mark.parametrize('bar_width', [None, 15])
@pytest.mark.parametrize('widget_type', [
    CScrollingPlot,
    CCyclicPlot,
    CStaticPlot,
])
@mock.patch('comrad.ExPlotWidget.addBarGraph', return_value='addBarGraphResult')
def test_addbargraph(addBarGraph, qtbot, widget_type, data_source, layer, color, bar_width):
    widget = widget_type()
    qtbot.add_widget(widget)

    if layer:
        widget.add_layer(layer)

    with mock.patch.object(widget, 'add_channel_attached_item', return_value='channelAttachedResult') as add_channel_attached_item:
        item = widget.addBarGraph(data_source=data_source,
                                  layer=layer,
                                  color=color,
                                  bar_width=bar_width)
        if isinstance(data_source, str):
            assert item == 'channelAttachedResult'
            add_channel_attached_item.assert_called_once_with(style=PlottingItemTypes.BAR_GRAPH.value,
                                                              channel_address=data_source,
                                                              layer=layer,
                                                              color=color,
                                                              line_width=bar_width)
            addBarGraph.assert_not_called()
        else:
            assert item == 'addBarGraphResult'
            add_channel_attached_item.assert_not_called()
            addBarGraph.assert_called_once_with(widget,
                                                data_source=data_source,
                                                layer=layer,
                                                buffer_size=DEFAULT_BUFFER_SIZE)


@pytest.mark.parametrize('data_source', [None, UpdateSource(), 'dev/prop#field'])
@pytest.mark.parametrize('layer', [None, 'mylayer'])
@pytest.mark.parametrize('color', [None, QColor(255, 255, 0)])
@pytest.mark.parametrize('line_width', [None, 15])
@pytest.mark.parametrize('widget_type', [
    CScrollingPlot,
    CCyclicPlot,
    CStaticPlot,
])
@mock.patch('comrad.ExPlotWidget.addInjectionBar', return_value='addInjectionBarResult')
def test_addinjectionbar(addInjectionBar, qtbot, widget_type, data_source, layer, color, line_width):
    widget = widget_type()
    qtbot.add_widget(widget)

    if layer:
        widget.add_layer(layer)

    with mock.patch.object(widget, 'add_channel_attached_item', return_value='channelAttachedResult') as add_channel_attached_item:
        item = widget.addInjectionBar(data_source=data_source,
                                      layer=layer,
                                      color=color,
                                      line_width=line_width)
        if isinstance(data_source, str):
            assert item == 'channelAttachedResult'
            add_channel_attached_item.assert_called_once_with(style=PlottingItemTypes.INJECTION_BAR_GRAPH.value,
                                                              channel_address=data_source,
                                                              layer=layer,
                                                              color=color,
                                                              line_width=line_width)
            addInjectionBar.assert_not_called()
        else:
            assert item == 'addInjectionBarResult'
            add_channel_attached_item.assert_not_called()
            addInjectionBar.assert_called_once_with(widget,
                                                    data_source=data_source,
                                                    layer=layer,
                                                    buffer_size=DEFAULT_BUFFER_SIZE)


@pytest.mark.parametrize('data_source', [UpdateSource(), 'dev/prop#field'])
@pytest.mark.parametrize('buffer_size', [0, 1, 10, DEFAULT_BUFFER_SIZE])
@pytest.mark.parametrize('line_width', [None, 15])
@pytest.mark.parametrize('widget_type', [
    CScrollingPlot,
    CCyclicPlot,
    CStaticPlot,
])
@mock.patch('comrad.ExPlotWidget.addTimestampMarker', return_value='addTimestampMarkerResult')
def test_addtimestampmarker(addTimestampMarker, qtbot, widget_type, data_source, buffer_size, line_width):
    widget = widget_type()
    qtbot.add_widget(widget)

    with mock.patch.object(widget, 'add_channel_attached_item', return_value='channelAttachedResult') as add_channel_attached_item:
        item = widget.addTimestampMarker(data_source=data_source,
                                         buffer_size=buffer_size,
                                         line_width=line_width)
        if isinstance(data_source, str):
            assert item == 'channelAttachedResult'
            add_channel_attached_item.assert_called_once_with(style=PlottingItemTypes.TIMESTAMP_MARKERS.value,
                                                              channel_address=data_source,
                                                              line_width=line_width)
            addTimestampMarker.assert_not_called()
        else:
            assert item == 'addTimestampMarkerResult'
            add_channel_attached_item.assert_not_called()
            addTimestampMarker.assert_called_once_with(widget,
                                                       data_source=data_source,
                                                       buffer_size=buffer_size)


@pytest.mark.parametrize('layer', [None, 'mylayer'])
@pytest.mark.parametrize('color,index,expected_color', [
    (None, None, 'white'),
    (None, 0, 'white'),
    (None, 1, 'red'),
    (None, 2, 'dodgerblue'),
    ('red', None, 'red'),
    ('red', 0, 'red'),
    ('red', 1, 'red'),
    ('red', 2, 'red'),
    (QColor(255, 255, 0), None, 'yellow'),
    (QColor(255, 255, 0), 0, 'yellow'),
    (QColor(255, 255, 0), 1, 'yellow'),
    (QColor(255, 255, 0), 2, 'yellow'),
])
@pytest.mark.parametrize('name', [None, 'custom-name'])
@pytest.mark.parametrize('symbol', [None, 'o'])
@pytest.mark.parametrize('symbol_size,expected_symbol_size', [
    (None, 10),
    (5, 5),
])
@pytest.mark.parametrize('line_style,expected_line_style', [
    (None, Qt.SolidLine),
    (Qt.DashLine, Qt.DashLine),
])
@pytest.mark.parametrize('line_width,expected_line_width', [
    (None, 1),
    (10, 10),
])
@pytest.mark.parametrize('widget_type', [
    CScrollingPlot,
    CCyclicPlot,
    CStaticPlot,
])
def test_add_channel_attached_item(qtbot, widget_type, index, layer, color, name, symbol,
                                   symbol_size, line_style, line_width, expected_line_style,
                                   expected_line_width, expected_symbol_size, expected_color):
    widget = widget_type()
    qtbot.add_widget(widget)
    item = widget.add_channel_attached_item(channel_address='dev/prop#field',
                                            layer=layer,
                                            index=index,
                                            name=name,
                                            color=color,
                                            line_style=line_style,
                                            line_width=line_width,
                                            symbol=symbol,
                                            symbol_size=symbol_size)
    assert isinstance(item, AbstractBasePlotCurve)
    assert isinstance(item.data_source, PyDMChannelDataSource)
    assert item.color == QColor(expected_color)
    assert item.line_style == expected_line_style
    assert item.line_width == expected_line_width
    assert item.symbol_size == expected_symbol_size
    assert item.label == name
    assert item.symbol == symbol
    assert item in widget.items()


@pytest.mark.parametrize('style,widget_type,expected_item_type', [
    (PlottingItemTypes.LINE_GRAPH, CScrollingPlot, CScrollingCurve),
    (PlottingItemTypes.BAR_GRAPH, CScrollingPlot, CScrollingBarGraph),
    (PlottingItemTypes.INJECTION_BAR_GRAPH, CScrollingPlot, CScrollingInjectionBarGraph),
    (PlottingItemTypes.TIMESTAMP_MARKERS, CScrollingPlot, CScrollingTimestampMarker),
    (PlottingItemTypes.LINE_GRAPH, CCyclicPlot, CCyclicCurve),
    (PlottingItemTypes.LINE_GRAPH, CStaticPlot, CStaticCurve),
    (PlottingItemTypes.BAR_GRAPH, CStaticPlot, CStaticBarGraph),
    (PlottingItemTypes.INJECTION_BAR_GRAPH, CStaticPlot, CStaticInjectionBarGraph),
    (PlottingItemTypes.TIMESTAMP_MARKERS, CStaticPlot, CStaticTimestampMarker),
])
def test_fitting_items(qtbot, style, widget_type, expected_item_type):
    widget = widget_type()
    qtbot.add_widget(widget)
    item = widget.add_channel_attached_item(channel_address='dev/prop#field',
                                            style=style.value)
    assert isinstance(item, expected_item_type)


@pytest.mark.parametrize('style,widget_type,err', [
    ('not-existing', CScrollingPlot, r"CScrollingPlot does not support style 'not-existing'"),
    ('not-existing', CCyclicPlot, r"CCyclicPlot does not support style 'not-existing'"),
    ('not-existing', CStaticPlot, r"CStaticPlot does not support style 'not-existing'"),
    (PlottingItemTypes.BAR_GRAPH.value, CCyclicPlot, r"CCyclicPlot does not support style 'Bar Graph'"),
    (PlottingItemTypes.INJECTION_BAR_GRAPH.value, CCyclicPlot, r"CCyclicPlot does not support style 'Injection Bar Graph'"),
    (PlottingItemTypes.TIMESTAMP_MARKERS.value, CCyclicPlot, r"CCyclicPlot does not support style 'Timestamp Marker'"),
])
def test_fitting_items_fails(qtbot, style, widget_type, err):
    widget = widget_type()
    qtbot.add_widget(widget)
    with pytest.raises(ValueError, match=err):
        widget.add_channel_attached_item(channel_address='dev/prop#field', style=style)


@pytest.mark.parametrize('widget_type, items,expected_json', [
    (CScrollingPlot, [{
        'channel_address': 'dev1/prop#field',
        'style': PlottingItemTypes.LINE_GRAPH.value,
        'name': 'My curve',
        'line_style': Qt.DashDotDotLine,
        'symbol': 'o',
    }], [{
        'channel': 'dev1/prop#field',
        'style': PlottingItemTypes.LINE_GRAPH.value,
        'layer': '',
        'name': 'My curve',
        'color': 'white',
        'line_style': Qt.DashDotDotLine,
        'line_width': 1,
        'symbol': 'o',
        'symbol_size': 10,
    }]),
    (CCyclicPlot, [{
        'channel_address': 'dev1/prop#field',
        'style': PlottingItemTypes.LINE_GRAPH.value,
        'name': 'My curve',
        'line_style': Qt.DashDotDotLine,
        'symbol': 'o',
    }], [{
        'channel': 'dev1/prop#field',
        'style': PlottingItemTypes.LINE_GRAPH.value,
        'layer': '',
        'name': 'My curve',
        'color': 'white',
        'line_style': Qt.DashDotDotLine,
        'line_width': 1,
        'symbol': 'o',
        'symbol_size': 10,
    }]),
    (CStaticPlot, [{
        'channel_address': 'dev1/prop#field',
        'style': PlottingItemTypes.LINE_GRAPH.value,
        'name': 'My curve',
        'line_style': Qt.DashDotDotLine,
        'symbol': 'o',
    }], [{
        'channel': 'dev1/prop#field',
        'style': PlottingItemTypes.LINE_GRAPH.value,
        'layer': '',
        'name': 'My curve',
        'color': 'white',
        'line_style': Qt.DashDotDotLine,
        'line_width': 1,
        'symbol': 'o',
        'symbol_size': 10,
    }]),
    (CScrollingPlot, [{
        'channel_address': 'dev1/prop#field',
        'style': PlottingItemTypes.INJECTION_BAR_GRAPH.value,
        'line_width': 2,
    }, {
        'channel_address': 'dev2/prop#field',
        'style': PlottingItemTypes.BAR_GRAPH.value,
        'name': 'test',
        'layer': 'secondary',
        'symbol_size': 1,
    }], [{
        'channel': 'dev1/prop#field',
        'style': PlottingItemTypes.INJECTION_BAR_GRAPH.value,
        'layer': '',
        'name': '',
        'color': 'white',
        'line_style': Qt.SolidLine,
        'line_width': 2,
        'symbol': None,
        'symbol_size': 10,
    }, {
        'channel': 'dev2/prop#field',
        'style': PlottingItemTypes.BAR_GRAPH.value,
        'layer': 'secondary',
        'name': 'test',
        'color': 'red',
        'line_style': Qt.SolidLine,
        'line_width': 1,
        'symbol': None,
        'symbol_size': 1,
    }]),
    (CStaticPlot, [{
        'channel_address': 'dev1/prop#field',
        'style': PlottingItemTypes.INJECTION_BAR_GRAPH.value,
        'line_width': 2,
    }, {
        'channel_address': 'dev2/prop#field',
        'style': PlottingItemTypes.BAR_GRAPH.value,
        'name': 'test',
        'layer': 'secondary',
        'symbol_size': 1,
    }], [{
        'channel': 'dev1/prop#field',
        'style': PlottingItemTypes.INJECTION_BAR_GRAPH.value,
        'layer': '',
        'name': '',
        'color': 'white',
        'line_style': Qt.SolidLine,
        'line_width': 2,
        'symbol': None,
        'symbol_size': 10,
    }, {
        'channel': 'dev2/prop#field',
        'style': PlottingItemTypes.BAR_GRAPH.value,
        'layer': 'secondary',
        'name': 'test',
        'color': 'red',
        'line_style': Qt.SolidLine,
        'line_width': 1,
        'symbol': None,
        'symbol_size': 1,
    }]),
])
def test_curves_getter(qtbot, widget_type, items, expected_json):
    widget = widget_type()
    qtbot.add_widget(widget)
    widget.add_layer('secondary')
    for item in items:
        widget.add_channel_attached_item(**item)
    json_repr = [json.loads(c) for c in widget.curves]
    assert json_repr == expected_json


def test_curves_setter(qtbot):
    json_repr = [json.dumps({
        'channel': 'dev1/prop#field',
        'style': PlottingItemTypes.INJECTION_BAR_GRAPH.value,
        'layer': '',
        'name': 'first',
        'color': 'white',
        'line_style': Qt.SolidLine,
        'line_width': 2,
        'symbol': None,
        'symbol_size': 10,
    }), json.dumps({
        'channel': 'dev2/prop#field',
        'style': PlottingItemTypes.BAR_GRAPH.value,
        'layer': 'secondary',
        'name': 'second',
        'color': 'red',
        'line_style': Qt.DashLine,
        'line_width': 1,
        'symbol': 'o',
        'symbol_size': 1,
    })]
    widget = CScrollingPlot()
    qtbot.add_widget(widget)
    widget.add_layer('secondary')
    widget.curves = json_repr
    first_item = [i for i in widget.items() if getattr(i, 'label', '') == 'first'][0]
    second_item = [i for i in widget.items() if getattr(i, 'label', '') == 'second'][0]
    assert isinstance(first_item, CScrollingInjectionBarGraph)
    assert first_item.address == 'dev1/prop#field'
    assert first_item.label == 'first'
    assert first_item.color == QColor(255, 255, 255)
    assert first_item.line_style == Qt.SolidLine
    assert first_item.line_width == 2
    assert first_item.symbol is None
    assert first_item.symbol_size == 10

    assert isinstance(second_item, CScrollingBarGraph)
    assert second_item.address == 'dev2/prop#field'
    assert second_item.label == 'second'
    assert second_item.color == QColor(255, 0, 0)
    assert second_item.line_style == Qt.DashLine
    assert second_item.line_width == 1
    assert second_item.symbol == 'o'
    assert second_item.symbol_size == 1


@pytest.mark.parametrize('widget_type', [
    CScrollingPlot,
    CCyclicPlot,
    CStaticPlot,
])
def test_clear_items(qtbot, widget_type):
    widget = widget_type()
    qtbot.add_widget(widget)
    item1 = widget.add_channel_attached_item(channel_address='dev/prop#field')
    item2 = widget.add_channel_attached_item(channel_address='dev2/prop#field')
    assert widget._items == [item1, item2]
    widget.clear_items()
    assert len(widget._items) == 0


def test_citempropertiesbase_forbids_weird_subclasses(caplog: LogCaptureFixture):

    class WeirdSubclass(CItemPropertiesBase):

        def style_string(self) -> str:
            pass

    assert len(caplog.records) == 0

    WeirdSubclass(related_base_class=int, related_concrete_class=bool)

    actual_warnings = [r.msg for r in cast(List[LogRecord], caplog.records) if r.levelno == logging.WARNING]
    assert actual_warnings == ['WeirdSubclass implementation relies on attributes provided by int. '
                               'Use int only as base class of classes derived from bool.']


@pytest.mark.parametrize('style,widget_type', [
    (PlottingItemTypes.LINE_GRAPH, CScrollingPlot),
    (PlottingItemTypes.BAR_GRAPH, CScrollingPlot),
    (PlottingItemTypes.INJECTION_BAR_GRAPH, CScrollingPlot),
    (PlottingItemTypes.TIMESTAMP_MARKERS, CScrollingPlot),
    (PlottingItemTypes.LINE_GRAPH, CCyclicPlot),
    (PlottingItemTypes.LINE_GRAPH, CStaticPlot),
    (PlottingItemTypes.BAR_GRAPH, CStaticPlot),
    (PlottingItemTypes.INJECTION_BAR_GRAPH, CStaticPlot),
    (PlottingItemTypes.TIMESTAMP_MARKERS, CStaticPlot),
])
@mock.patch('pydm.widgets.channel.PyDMChannel.connect')
@mock.patch('comrad.CContextFrame.context_ready', return_value=True)
@mock.patch('comrad.CItemPropertiesBase.channels', new_callable=mock.PropertyMock)
def test_initialize_style_properties_connects_destroyed_signal(_, __, ___, qtbot, style, widget_type):
    ctx_provider = CContextFrame()
    qtbot.add_widget(ctx_provider)
    ctx_provider.setLayout(QVBoxLayout())
    widget = widget_type()
    ctx_provider.show()  # Make connections establish
    item = widget.add_channel_attached_item(channel_address='dev/prop#field', style=style.value)
    assert item.receivers(item.destroyed) > 0  # The opposite is checked below, in test_citempropertiesbase_props


@pytest.mark.parametrize('style,widget_type,default_label', [
    (PlottingItemTypes.LINE_GRAPH, CScrollingPlot, None),
    (PlottingItemTypes.BAR_GRAPH, CScrollingPlot, ''),
    (PlottingItemTypes.INJECTION_BAR_GRAPH, CScrollingPlot, ''),
    (PlottingItemTypes.TIMESTAMP_MARKERS, CScrollingPlot, ''),
    (PlottingItemTypes.LINE_GRAPH, CCyclicPlot, None),
    (PlottingItemTypes.LINE_GRAPH, CStaticPlot, None),
    (PlottingItemTypes.BAR_GRAPH, CStaticPlot, ''),
    (PlottingItemTypes.INJECTION_BAR_GRAPH, CStaticPlot, ''),
    (PlottingItemTypes.TIMESTAMP_MARKERS, CStaticPlot, ''),
])
def test_citempropertiesbase_props(qtbot, widget_type, style, default_label):
    widget = widget_type()
    qtbot.add_widget(widget)
    item = widget.add_channel_attached_item(channel_address='dev/prop#field', style=style.value)
    assert item.address == 'dev/prop#field'
    assert isinstance(item.data_source, PyDMChannelDataSource)
    assert item.data_source.address == 'dev/prop#field'
    item.address = 'new'
    assert item.data_source.address == 'new'
    assert item.address == 'new'
    assert item.style_string == style.value
    assert item.color_string == 'white'
    item.color_string = 'red'
    assert item.color == QColor(255, 0, 0)
    item.color = 'blue'
    assert item.color_string == 'blue'
    assert item.color == QColor(0, 0, 255)
    item.color = QColor(127, 127, 127)
    assert item.color == QColor(127, 127, 127)
    assert item.color_string == '#7f7f7f'
    assert item.label == default_label
    item.label = 'test'
    assert item.label == 'test'
    assert item.line_style == Qt.SolidLine
    item.line_style = Qt.DashLine
    assert item.line_style == Qt.DashLine
    assert item.line_width == 1
    item.line_width = 10
    assert item.line_width == 10
    assert item.symbol is None
    item.symbol = 'x'
    assert item.symbol == 'x'
    assert item.symbol_size == 10
    item.symbol_size = 5
    assert item.symbol_size == 5
    assert item.receivers(item.destroyed) == 0


@pytest.mark.parametrize('layer', [None, '', 'custom'])
@pytest.mark.parametrize('style,widget_type', [
    (PlottingItemTypes.LINE_GRAPH, CScrollingPlot),
    (PlottingItemTypes.BAR_GRAPH, CScrollingPlot),
    (PlottingItemTypes.INJECTION_BAR_GRAPH, CScrollingPlot),
    (PlottingItemTypes.TIMESTAMP_MARKERS, CScrollingPlot),
    (PlottingItemTypes.LINE_GRAPH, CCyclicPlot),
    (PlottingItemTypes.LINE_GRAPH, CStaticPlot),
    (PlottingItemTypes.BAR_GRAPH, CStaticPlot),
    (PlottingItemTypes.INJECTION_BAR_GRAPH, CStaticPlot),
    (PlottingItemTypes.TIMESTAMP_MARKERS, CStaticPlot),
])
def test_citempropertiesbase_layer(qtbot, widget_type, style, layer):
    widget = widget_type()
    qtbot.add_widget(widget)

    if layer:
        widget.add_layer(layer)

    item = widget.add_channel_attached_item(channel_address='dev/prop#field', style=style.value, layer=layer)
    assert item.layer == (layer or '')
