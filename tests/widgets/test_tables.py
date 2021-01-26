import pytest
import logging
from logging import LogRecord
from typing import List, cast
from pytestqt.qtbot import QtBot
from _pytest.logging import LogCaptureFixture
from unittest import mock
from accwidgets.log_console import LogConsoleRecord
from comrad import CLogConsole, CLogDisplay, LogLevel, LogConsoleModel, AbstractLogConsoleModel


@pytest.fixture(autouse=True, scope='function')
def clean_logging():
    orig_level = logging.Logger.root.level
    logging.Logger.manager.loggerDict.clear()
    logging.Logger.root.setLevel(logging.NOTSET)
    yield
    logging.Logger.root.setLevel(orig_level)
    logging.Logger.manager.loggerDict.clear()


@pytest.mark.parametrize('is_designer_value,expect_warning', [
    (True, False),
    (False, True),
])
@mock.patch('comrad.widgets.tables.is_qt_designer')
def test_clogdisplay_issues_warning_on_creation(is_qt_designer, is_designer_value, expect_warning,
                                                caplog: LogCaptureFixture, qtbot: QtBot):
    is_qt_designer.return_value = is_designer_value
    widget = CLogDisplay()
    qtbot.add_widget(widget)
    actual_errors = [r.msg for r in cast(List[LogRecord], caplog.records) if r.levelno == logging.WARNING and r.module == 'tables']
    if expect_warning:
        assert actual_errors == ['CLogDisplay is deprecated, please use CLogConsole instead.']
    else:
        assert not actual_errors


@pytest.mark.parametrize('loggers,model,expect_raises', [
    ({'logger1': LogLevel.WARNING}, mock.MagicMock(), True),
    ({'logger1': LogLevel.WARNING}, None, False),
    ({}, mock.MagicMock(), True),
    ({}, None, False),
    (None, mock.MagicMock(), False),
    (None, None, False),
])
def test_clogconsole_raises_with_mutually_exclusive_args(loggers, model, expect_raises, qtbot: QtBot):
    if expect_raises:
        with pytest.raises(ValueError, match=r"'model' and 'loggers' are mutually exclusive."):
            CLogConsole(loggers=loggers, model=model)
    else:
        widget = CLogConsole(loggers=loggers, model=model)
        qtbot.add_widget(widget)


@pytest.mark.parametrize('model_levels,expected_levels', [
    ({}, {}),
    ({'logger1': LogLevel.WARNING}, {'logger1': LogLevel.WARNING}),
    ({'logger1': LogLevel.INFO}, {'logger1': LogLevel.INFO}),
    ({'logger1': LogLevel.INFO, 'logger2': LogLevel.WARNING}, {'logger1': LogLevel.INFO, 'logger2': LogLevel.WARNING}),
])
def test_clogconsole_sets_loggers_when_created_with_model(model_levels, expected_levels, qtbot: QtBot):
    model = mock.MagicMock()
    model.selected_logger_levels = model_levels
    widget = CLogConsole(model=model)
    qtbot.add_widget(widget)
    assert widget.loggers == expected_levels


@pytest.mark.parametrize('input_levels,expected_levels', [
    ({}, {}),
    ({'logger1': LogLevel.WARNING}, {'logger1': LogLevel.WARNING}),
    ({'logger1': LogLevel.INFO}, {'logger1': LogLevel.INFO}),
    ({'logger1': LogLevel.INFO, 'logger2': LogLevel.WARNING}, {'logger1': LogLevel.INFO, 'logger2': LogLevel.WARNING}),
])
def test_clogconsole_sets_loggers_when_created_with_loggers(input_levels, expected_levels, qtbot: QtBot):
    widget = CLogConsole(loggers=input_levels)
    qtbot.add_widget(widget)
    assert widget.loggers == expected_levels


@pytest.mark.parametrize('input_levels', [
    ({}, {}),
    ({'logger1': LogLevel.WARNING}),
    ({'logger1': LogLevel.INFO}),
    ({'logger1': LogLevel.INFO, 'logger2': LogLevel.WARNING}),
])
def test_clogconsole_creates_does_not_create_model_when_created_with_loggers(input_levels, qtbot: QtBot):
    widget = CLogConsole(loggers=input_levels)
    qtbot.add_widget(widget)
    assert widget.model is None


def test_clogconsole_default_loggers_without_model_or_loggers_arg(qtbot: QtBot):
    widget = CLogConsole()
    qtbot.add_widget(widget)
    assert widget.model is None
    assert widget.loggers == {}


@pytest.mark.parametrize('is_designer_value,levels,expected_value', [
    (False, {}, {}),
    (False, {'logger1': LogLevel.WARNING}, {'logger1': LogLevel.WARNING}),
    (False, {'logger1': LogLevel.INFO}, {'logger1': LogLevel.INFO}),
    (False, {'logger1': LogLevel.INFO, 'logger2': LogLevel.WARNING}, {'logger1': LogLevel.INFO, 'logger2': LogLevel.WARNING}),
    (True, {}, '{}'),
    (True, {'logger1': LogLevel.WARNING}, '{"logger1": 30}'),
    (True, {'logger1': LogLevel.INFO}, '{"logger1": 20}'),
    (True, {'logger1': LogLevel.INFO, 'logger2': LogLevel.WARNING}, '{"logger1": 20, "logger2": 30}'),
])
@mock.patch('comrad.widgets.tables.is_qt_designer')
def test_clogconsole_loggers_getter(is_qt_designer, is_designer_value, expected_value, levels, qtbot: QtBot):
    is_qt_designer.return_value = is_designer_value
    widget = CLogConsole(loggers=levels)
    qtbot.add_widget(widget)
    assert widget._logger_levels == levels
    assert widget.loggers == expected_value


@pytest.mark.parametrize('is_designer_value,new_levels,expected_value', [
    (False, {}, {}),
    (False, {'logger1': LogLevel.WARNING}, {'logger1': LogLevel.WARNING}),
    (False, {'logger1': LogLevel.INFO}, {'logger1': LogLevel.INFO}),
    (False, {'logger1': LogLevel.INFO, 'logger2': LogLevel.WARNING}, {'logger1': LogLevel.INFO, 'logger2': LogLevel.WARNING}),
    (True, '{}', {}),
    (True, '{"logger1": 30}', {'logger1': LogLevel.WARNING}),
    (True, '{"logger1": 20}', {'logger1': LogLevel.INFO}),
    (True, '{"logger1": 20, "logger2": 30}', {'logger1': LogLevel.INFO, 'logger2': LogLevel.WARNING}),
])
@mock.patch('comrad.widgets.tables.is_qt_designer')
def test_clogconsole_loggers_setter(is_qt_designer, is_designer_value, expected_value, new_levels, qtbot: QtBot):
    is_qt_designer.return_value = is_designer_value
    widget = CLogConsole()
    qtbot.add_widget(widget)
    assert widget._logger_levels == {}
    widget.loggers = new_levels
    assert widget._logger_levels == expected_value


@pytest.mark.parametrize('input,expected_warning', [
    ('{', 'Failed to decode json: Expecting property name enclosed in double quotes:'),
    ('{logger1: 20}', 'Failed to decode json: Expecting property name enclosed in double quotes:'),
    ('', 'Failed to decode json: Expecting value:'),
])
@mock.patch('comrad.widgets.tables.is_qt_designer', return_value=True)
def test_clogconsole_loggers_setter_json_decode_error(_, input, qtbot: QtBot, expected_warning, caplog: LogCaptureFixture):
    get_records = lambda: [r.msg for r in cast(List[LogRecord], caplog.records) if r.levelno == logging.WARNING and r.module == 'tables']
    widget = CLogConsole()
    qtbot.add_widget(widget)
    assert get_records() == []
    assert widget._logger_levels == {}
    widget.loggers = input
    assert widget._logger_levels == {}
    warnings = get_records()
    assert len(warnings) == 1
    assert warnings[0].startswith(expected_warning)


@pytest.mark.parametrize('input,expect_warning', [
    ('{}', False),
    ('[]', True),
    ('{"logger1": 20}', False),
    ('[{"logger1": 20}]', True),
])
@mock.patch('comrad.widgets.tables.is_qt_designer', return_value=True)
def test_clogconsole_loggers_setter_json_not_dict_error(_, input, qtbot: QtBot, expect_warning, caplog: LogCaptureFixture):
    get_records = lambda: [r.msg for r in cast(List[LogRecord], caplog.records) if r.levelno == logging.WARNING and r.module == 'tables']
    widget = CLogConsole()
    qtbot.add_widget(widget)
    assert get_records() == []
    widget.loggers = input
    if expect_warning:
        assert get_records() == ['Decoded logger levels is not a dictionary']
    else:
        assert get_records() == []


@pytest.mark.parametrize('input,expect_raises', [
    ('{"logger1": 10}', False),
    ('{"logger1": 20}', False),
    ('{"logger1": 30}', False),
    ('{"logger1": 40}', False),
    ('{"logger1": 50}', False),
    ('{"logger1": 21}', True),
    ('{"logger1": 20, "logger2": 21}', True),
    ('{"logger1": 999}', True),
])
@mock.patch('comrad.widgets.tables.is_qt_designer', return_value=True)
def test_clogconsole_loggers_setter_json_unknown_level_error(_, input, qtbot: QtBot, expect_raises):
    widget = CLogConsole()
    qtbot.add_widget(widget)
    if expect_raises:
        with pytest.raises(ValueError):
            widget.loggers = input
    else:
        widget.loggers = input


@pytest.mark.parametrize('is_designer_value,new_levels', [
    (False, {}),
    (False, {'logger1': LogLevel.WARNING}),
    (False, {'logger1': LogLevel.INFO}),
    (False, {'logger1': LogLevel.INFO, 'logger2': LogLevel.WARNING}),
    (True, '{}'),
    (True, '{"logger1": 30}'),
    (True, '{"logger1": 20}'),
    (True, '{"logger1": 20, "logger2": 30}'),
])
@mock.patch('comrad.widgets.tables.is_qt_designer')
def test_clogconsole_loggers_setter_does_not_create_implicit_model(is_qt_designer, is_designer_value, new_levels, qtbot: QtBot):
    is_qt_designer.return_value = is_designer_value
    widget = CLogConsole(model=None)
    qtbot.add_widget(widget)
    assert widget.model is None
    widget.loggers = new_levels
    assert widget.model is None


@pytest.mark.parametrize('is_designer_value,new_levels', [
    (False, {}),
    (False, {'logger1': LogLevel.WARNING}),
    (False, {'logger1': LogLevel.INFO}),
    (False, {'logger1': LogLevel.INFO, 'logger2': LogLevel.WARNING}),
    (True, '{}'),
    (True, '{"logger1": 30}'),
    (True, '{"logger1": 20}'),
    (True, '{"logger1": 20, "logger2": 30}'),
])
@mock.patch('comrad.widgets.tables.is_qt_designer')
def test_clogconsole_loggers_setter_cant_derive_from_custom_model(is_qt_designer, is_designer_value, new_levels,
                                                                  qtbot: QtBot, custom_model_class, caplog: LogCaptureFixture):
    is_qt_designer.return_value = is_designer_value
    model = custom_model_class()
    get_records = lambda: [r.msg for r in cast(List[LogRecord], caplog.records) if r.levelno == logging.ERROR and r.module == 'tables']
    widget = CLogConsole(model=model)
    qtbot.add_widget(widget)
    assert get_records() == []
    widget.loggers = new_levels
    assert get_records() == ['Cannot set Python loggers on an unsupported model type "TestModel".']


@pytest.mark.parametrize('is_designer_value,new_levels', [
    (False, {}),
    (False, {'logger1': LogLevel.WARNING}),
    (False, {'logger1': LogLevel.INFO}),
    (False, {'logger1': LogLevel.INFO, 'logger2': LogLevel.WARNING}),
    (True, '{}'),
    (True, '{"logger1": 30}'),
    (True, '{"logger1": 20}'),
    (True, '{"logger1": 20, "logger2": 30}'),
])
@mock.patch('comrad.widgets.tables.is_qt_designer')
def test_clogconsole_loggers_setter_cant_derive_from_model_subclass(is_qt_designer, is_designer_value, new_levels,
                                                                    qtbot: QtBot, custom_model_class, caplog: LogCaptureFixture):
    is_qt_designer.return_value = is_designer_value

    class ModelSubclass(LogConsoleModel):
        pass

    model = ModelSubclass()
    get_records = lambda: [r.msg for r in cast(List[LogRecord], caplog.records) if r.levelno == logging.ERROR and r.module == 'tables']
    widget = CLogConsole(model=model)
    qtbot.add_widget(widget)
    assert get_records() == []
    widget.loggers = new_levels
    assert get_records() == ['Cannot set Python loggers on an unsupported model type "ModelSubclass".']


@pytest.mark.parametrize('buf_size', [0, 1, 1000])
@pytest.mark.parametrize('visible_levels,expected_visible_levels', [
    (None, {LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR, LogLevel.CRITICAL}),
    (set(), set()),
    ({LogLevel.WARNING}, {LogLevel.WARNING}),
    ({LogLevel.WARNING, LogLevel.INFO}, {LogLevel.WARNING, LogLevel.INFO}),
])
@pytest.mark.parametrize('modifies_loggers,init_loggers,init_selected_levels,new_levels,expected_loggers,expected_selected_levels', [
    (True, None, {}, {}, {'root'}, {'root': LogLevel.NOTSET}),
    (True, set(), {}, {}, {'root'}, {'root': LogLevel.NOTSET}),
    (True, {''}, {}, {}, {'root'}, {'root': LogLevel.NOTSET}),
    (True, {''}, {'root': LogLevel.INFO}, {}, {'root'}, {'root': LogLevel.INFO}),
    (True, {''}, {'root': LogLevel.WARNING}, {}, {'root'}, {'root': LogLevel.WARNING}),
    (True, {'logger1'}, {}, {}, {'root'}, {'root': LogLevel.NOTSET}),
    (True, {'logger1'}, {'logger1': LogLevel.INFO}, {}, {'root'}, {'root': LogLevel.NOTSET}),
    (True, {'logger1'}, {'logger1': LogLevel.WARNING}, {}, {'root'}, {'root': LogLevel.NOTSET}),
    (True, {'', 'logger1'}, {}, {}, {'root'}, {'root': LogLevel.NOTSET}),
    (True, {'', 'logger1'}, {'logger1': LogLevel.INFO}, {}, {'root'}, {'root': LogLevel.NOTSET}),
    (True, {'', 'logger1'}, {'root': LogLevel.INFO}, {}, {'root'}, {'root': LogLevel.INFO}),
    (True, {'', 'logger1'}, {'root': LogLevel.INFO, 'logger1': LogLevel.WARNING}, {}, {'root'}, {'root': LogLevel.INFO}),
    (True, None, {}, {'logger1': LogLevel.ERROR}, {'logger1'}, {'logger1': LogLevel.ERROR}),
    (True, set(), {}, {'logger1': LogLevel.ERROR}, {'logger1'}, {'logger1': LogLevel.ERROR}),
    (True, {''}, {}, {'logger1': LogLevel.ERROR}, {'logger1'}, {'logger1': LogLevel.ERROR}),
    (True, {''}, {'root': LogLevel.INFO}, {'logger1': LogLevel.ERROR}, {'logger1'}, {'logger1': LogLevel.ERROR}),
    (True, {''}, {'root': LogLevel.WARNING}, {'logger1': LogLevel.ERROR}, {'logger1'}, {'logger1': LogLevel.ERROR}),
    (True, {'logger1'}, {}, {'logger1': LogLevel.ERROR}, {'logger1'}, {'logger1': LogLevel.ERROR}),
    (True, {'logger1'}, {'logger1': LogLevel.INFO}, {'logger1': LogLevel.ERROR}, {'logger1'}, {'logger1': LogLevel.ERROR}),
    (True, {'logger1'}, {'logger1': LogLevel.WARNING}, {'logger1': LogLevel.ERROR}, {'logger1'}, {'logger1': LogLevel.ERROR}),
    (True, {'', 'logger1'}, {}, {'logger1': LogLevel.ERROR}, {'logger1'}, {'logger1': LogLevel.ERROR}),
    (True, {'', 'logger1'}, {'logger1': LogLevel.INFO}, {'logger1': LogLevel.ERROR}, {'logger1'}, {'logger1': LogLevel.ERROR}),
    (True, {'', 'logger1'}, {'root': LogLevel.INFO}, {'logger1': LogLevel.ERROR}, {'logger1'}, {'logger1': LogLevel.ERROR}),
    (True, {'', 'logger1'}, {'root': LogLevel.INFO, 'logger1': LogLevel.WARNING}, {'logger1': LogLevel.ERROR}, {'logger1'}, {'logger1': LogLevel.ERROR}),
    (True, None, {}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}, {'logger1', 'root'}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}),
    (True, set(), {}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}, {'logger1', 'root'}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}),
    (True, {''}, {}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}, {'logger1', 'root'}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}),
    (True, {''}, {'root': LogLevel.INFO}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}, {'logger1', 'root'}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}),
    (True, {''}, {'root': LogLevel.WARNING}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}, {'logger1', 'root'}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}),
    (True, {'logger1'}, {}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}, {'logger1', 'root'}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}),
    (True, {'logger1'}, {'logger1': LogLevel.INFO}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}, {'logger1', 'root'}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}),
    (True, {'logger1'}, {'logger1': LogLevel.WARNING}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}, {'logger1', 'root'}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}),
    (True, {'', 'logger1'}, {}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}, {'logger1', 'root'}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}),
    (True, {'', 'logger1'}, {'logger1': LogLevel.INFO}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}, {'logger1', 'root'}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}),
    (True, {'', 'logger1'}, {'root': LogLevel.INFO}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}, {'logger1', 'root'}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}),
    (True, {'', 'logger1'}, {'root': LogLevel.INFO, 'logger1': LogLevel.WARNING}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}, {'logger1', 'root'}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}),
    (True, None, {}, {'logger2': LogLevel.CRITICAL}, {'logger2'}, {'logger2': LogLevel.CRITICAL}),
    (True, set(), {}, {'logger2': LogLevel.CRITICAL}, {'logger2'}, {'logger2': LogLevel.CRITICAL}),
    (True, {''}, {}, {'logger2': LogLevel.CRITICAL}, {'logger2'}, {'logger2': LogLevel.CRITICAL}),
    (True, {''}, {'root': LogLevel.INFO}, {'logger2': LogLevel.CRITICAL}, {'logger2'}, {'logger2': LogLevel.CRITICAL}),
    (True, {''}, {'root': LogLevel.WARNING}, {'logger2': LogLevel.CRITICAL}, {'logger2'}, {'logger2': LogLevel.CRITICAL}),
    (True, {'logger1'}, {}, {'logger2': LogLevel.CRITICAL}, {'logger2'}, {'logger2': LogLevel.CRITICAL}),
    (True, {'logger1'}, {'logger1': LogLevel.INFO}, {'logger2': LogLevel.CRITICAL}, {'logger2'}, {'logger2': LogLevel.CRITICAL}),
    (True, {'logger1'}, {'logger1': LogLevel.WARNING}, {'logger2': LogLevel.CRITICAL}, {'logger2'}, {'logger2': LogLevel.CRITICAL}),
    (True, {'', 'logger1'}, {}, {'logger2': LogLevel.CRITICAL}, {'logger2'}, {'logger2': LogLevel.CRITICAL}),
    (True, {'', 'logger1'}, {'logger1': LogLevel.INFO}, {'logger2': LogLevel.CRITICAL}, {'logger2'}, {'logger2': LogLevel.CRITICAL}),
    (True, {'', 'logger1'}, {'root': LogLevel.INFO}, {'logger2': LogLevel.CRITICAL}, {'logger2'}, {'logger2': LogLevel.CRITICAL}),
    (True, {'', 'logger1'}, {'root': LogLevel.INFO, 'logger1': LogLevel.WARNING}, {'logger2': LogLevel.CRITICAL}, {'logger2'}, {'logger2': LogLevel.CRITICAL}),
    (False, None, {}, {}, {'root'}, {'root': LogLevel.NOTSET}),
    (False, set(), {}, {}, {'root'}, {'root': LogLevel.NOTSET}),
    (False, {''}, {}, {}, {'root'}, {'root': LogLevel.NOTSET}),
    (False, {''}, {'root': LogLevel.INFO}, {}, {'root'}, {'root': LogLevel.NOTSET}),
    (False, {''}, {'root': LogLevel.WARNING}, {}, {'root'}, {'root': LogLevel.NOTSET}),
    (False, {'logger1'}, {}, {}, {'root'}, {'root': LogLevel.NOTSET}),
    (False, {'logger1'}, {'logger1': LogLevel.INFO}, {}, {'root'}, {'root': LogLevel.NOTSET}),
    (False, {'logger1'}, {'logger1': LogLevel.WARNING}, {}, {'root'}, {'root': LogLevel.NOTSET}),
    (False, {'', 'logger1'}, {}, {}, {'root'}, {'root': LogLevel.NOTSET}),
    (False, {'', 'logger1'}, {'logger1': LogLevel.INFO}, {}, {'root'}, {'root': LogLevel.NOTSET}),
    (False, {'', 'logger1'}, {'root': LogLevel.INFO}, {}, {'root'}, {'root': LogLevel.NOTSET}),
    (False, {'', 'logger1'}, {'root': LogLevel.INFO, 'logger1': LogLevel.WARNING}, {}, {'root'}, {'root': LogLevel.NOTSET}),
    (False, None, {}, {'logger1': LogLevel.ERROR}, {'logger1'}, {'logger1': LogLevel.ERROR}),
    (False, set(), {}, {'logger1': LogLevel.ERROR}, {'logger1'}, {'logger1': LogLevel.ERROR}),
    (False, {''}, {}, {'logger1': LogLevel.ERROR}, {'logger1'}, {'logger1': LogLevel.ERROR}),
    (False, {''}, {'root': LogLevel.INFO}, {'logger1': LogLevel.ERROR}, {'logger1'}, {'logger1': LogLevel.ERROR}),
    (False, {''}, {'root': LogLevel.WARNING}, {'logger1': LogLevel.ERROR}, {'logger1'}, {'logger1': LogLevel.ERROR}),
    (False, {'logger1'}, {}, {'logger1': LogLevel.ERROR}, {'logger1'}, {'logger1': LogLevel.ERROR}),
    (False, {'logger1'}, {'logger1': LogLevel.INFO}, {'logger1': LogLevel.ERROR}, {'logger1'}, {'logger1': LogLevel.ERROR}),
    (False, {'logger1'}, {'logger1': LogLevel.WARNING}, {'logger1': LogLevel.ERROR}, {'logger1'}, {'logger1': LogLevel.ERROR}),
    (False, {'', 'logger1'}, {}, {'logger1': LogLevel.ERROR}, {'logger1'}, {'logger1': LogLevel.ERROR}),
    (False, {'', 'logger1'}, {'logger1': LogLevel.INFO}, {'logger1': LogLevel.ERROR}, {'logger1'}, {'logger1': LogLevel.ERROR}),
    (False, {'', 'logger1'}, {'root': LogLevel.INFO}, {'logger1': LogLevel.ERROR}, {'logger1'}, {'logger1': LogLevel.ERROR}),
    (False, {'', 'logger1'}, {'root': LogLevel.INFO, 'logger1': LogLevel.WARNING}, {'logger1': LogLevel.ERROR}, {'logger1'}, {'logger1': LogLevel.ERROR}),
    (False, None, {}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}, {'logger1', 'root'}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}),
    (False, set(), {}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}, {'logger1', 'root'}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}),
    (False, {''}, {}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}, {'logger1', 'root'}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}),
    (False, {''}, {'root': LogLevel.INFO}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}, {'logger1', 'root'}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}),
    (False, {''}, {'root': LogLevel.WARNING}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}, {'logger1', 'root'}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}),
    (False, {'logger1'}, {}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}, {'logger1', 'root'}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}),
    (False, {'logger1'}, {'logger1': LogLevel.INFO}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}, {'logger1', 'root'}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}),
    (False, {'logger1'}, {'logger1': LogLevel.WARNING}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}, {'logger1', 'root'}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}),
    (False, {'', 'logger1'}, {}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}, {'logger1', 'root'}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}),
    (False, {'', 'logger1'}, {'logger1': LogLevel.INFO}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}, {'logger1', 'root'}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}),
    (False, {'', 'logger1'}, {'root': LogLevel.INFO}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}, {'logger1', 'root'}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}),
    (False, {'', 'logger1'}, {'root': LogLevel.INFO, 'logger1': LogLevel.WARNING}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}, {'logger1', 'root'}, {'logger1': LogLevel.ERROR, 'root': LogLevel.DEBUG}),
    (False, None, {}, {'logger2': LogLevel.CRITICAL}, {'logger2'}, {'logger2': LogLevel.CRITICAL}),
    (False, set(), {}, {'logger2': LogLevel.CRITICAL}, {'logger2'}, {'logger2': LogLevel.CRITICAL}),
    (False, {''}, {}, {'logger2': LogLevel.CRITICAL}, {'logger2'}, {'logger2': LogLevel.CRITICAL}),
    (False, {''}, {'root': LogLevel.INFO}, {'logger2': LogLevel.CRITICAL}, {'logger2'}, {'logger2': LogLevel.CRITICAL}),
    (False, {''}, {'root': LogLevel.WARNING}, {'logger2': LogLevel.CRITICAL}, {'logger2'}, {'logger2': LogLevel.CRITICAL}),
    (False, {'logger1'}, {}, {'logger2': LogLevel.CRITICAL}, {'logger2'}, {'logger2': LogLevel.CRITICAL}),
    (False, {'logger1'}, {'logger1': LogLevel.INFO}, {'logger2': LogLevel.CRITICAL}, {'logger2'}, {'logger2': LogLevel.CRITICAL}),
    (False, {'logger1'}, {'logger1': LogLevel.WARNING}, {'logger2': LogLevel.CRITICAL}, {'logger2'}, {'logger2': LogLevel.CRITICAL}),
    (False, {'', 'logger1'}, {}, {'logger2': LogLevel.CRITICAL}, {'logger2'}, {'logger2': LogLevel.CRITICAL}),
    (False, {'', 'logger1'}, {'logger1': LogLevel.INFO}, {'logger2': LogLevel.CRITICAL}, {'logger2'}, {'logger2': LogLevel.CRITICAL}),
    (False, {'', 'logger1'}, {'root': LogLevel.INFO}, {'logger2': LogLevel.CRITICAL}, {'logger2'}, {'logger2': LogLevel.CRITICAL}),
    (False, {'', 'logger1'}, {'root': LogLevel.INFO, 'logger1': LogLevel.WARNING}, {'logger2': LogLevel.CRITICAL}, {'logger2'}, {'logger2': LogLevel.CRITICAL}),
])
def test_clogconsole_loggers_setter_replaces_existing_model(buf_size, visible_levels, modifies_loggers, init_loggers,
                                                            init_selected_levels, new_levels, expected_loggers,
                                                            expected_selected_levels, expected_visible_levels, qtbot: QtBot):
    loggers = None if init_loggers is None else [logging.getLogger(name) for name in init_loggers]
    init_model = LogConsoleModel(buffer_size=buf_size,
                                 visible_levels=visible_levels,
                                 loggers=loggers,
                                 level_changes_modify_loggers=modifies_loggers)
    init_model.selected_logger_levels = init_selected_levels
    widget = CLogConsole(model=init_model)
    qtbot.add_widget(widget)
    widget.loggers = new_levels
    assert widget.model != init_model
    assert widget.model.buffer_size == buf_size
    assert widget.model.visible_levels == expected_visible_levels
    assert widget.model.selected_logger_levels == expected_selected_levels
    assert set(widget.model.available_logger_levels.keys()) == expected_loggers


@pytest.mark.parametrize('initial_loggers,expected_loggers', [
    ({}, {'root'}),
    ({'': LogLevel.ERROR}, {'root'}),
    ({'logger1': LogLevel.ERROR}, {'root'}),
    ({'logger1': LogLevel.ERROR, 'logger2': LogLevel.WARNING}, {'root'}),
    ({'logger1': LogLevel.ERROR, 'pydm': LogLevel.CRITICAL}, {'root', 'pydm'}),
    ({'logger1': LogLevel.ERROR, 'pydm.sublogger': LogLevel.CRITICAL}, {'root'}),
    ({'logger1': LogLevel.ERROR, 'papc': LogLevel.CRITICAL}, {'root'}),
    ({'logger1': LogLevel.ERROR, 'papc.sublogger': LogLevel.CRITICAL}, {'root', 'papc.sublogger'}),
    ({'pyjapc': LogLevel.ERROR, 'pydm': LogLevel.CRITICAL}, {'root', 'pyjapc', 'pydm'}),
    ({'pyjapc': LogLevel.ERROR, 'pjlsa': LogLevel.WARNING, 'pytimber': LogLevel.WARNING}, {'root', 'pyjapc', 'pjlsa', 'pytimber'}),
    ({'': LogLevel.ERROR, 'logger1': LogLevel.WARNING}, {'root'}),
    ({'logger1': LogLevel.ERROR, 'logger1.sublogger': LogLevel.INFO, 'logger2': LogLevel.WARNING}, {'root'}),
])
def test_clogconsole_detects_existing_loggers_on_show_when_non_were_set(initial_loggers, expected_loggers, qtbot: QtBot):
    for logger_name, level in initial_loggers.items():
        logging.getLogger(logger_name).setLevel(level.value)

    widget = CLogConsole()
    qtbot.add_widget(widget)
    with qtbot.wait_exposed(widget):
        widget.show()
    assert set(widget.model._handlers.keys()) == expected_loggers


@pytest.mark.parametrize('existing_loggers', [
    {},
    {'': LogLevel.ERROR},
    {'logger1': LogLevel.ERROR},
    {'logger1': LogLevel.ERROR, 'logger2': LogLevel.WARNING},
    {'logger1': LogLevel.ERROR, 'pydm': LogLevel.CRITICAL},
    {'logger1': LogLevel.ERROR, 'pydm.sublogger': LogLevel.CRITICAL},
    {'logger1': LogLevel.ERROR, 'papc': LogLevel.CRITICAL},
    {'logger1': LogLevel.ERROR, 'papc.sublogger': LogLevel.CRITICAL},
    {'pyjapc': LogLevel.ERROR, 'pydm': LogLevel.CRITICAL},
    {'pyjapc': LogLevel.ERROR, 'pjlsa': LogLevel.WARNING, 'pytimber': LogLevel.WARNING},
    {'': LogLevel.ERROR, 'logger1': LogLevel.WARNING},
    {'logger1': LogLevel.ERROR, 'logger1.sublogger': LogLevel.INFO, 'logger2': LogLevel.WARNING},
])
@pytest.mark.parametrize('initial_levels,expected_loggers', [
    ({'': LogLevel.ERROR}, {'root'}),
    ({'root': LogLevel.ERROR}, {'root'}),
    ({'ROOT': LogLevel.ERROR}, {'root'}),
    ({'logger1': LogLevel.ERROR}, {'logger1'}),
    ({'logger1': LogLevel.ERROR, 'logger2': LogLevel.WARNING}, {'logger1', 'logger2'}),
    ({'logger1': LogLevel.ERROR, 'pydm': LogLevel.CRITICAL}, {'logger1', 'pydm'}),
    ({'logger1': LogLevel.ERROR, 'pydm.sublogger': LogLevel.CRITICAL}, {'logger1', 'pydm.sublogger'}),
    ({'logger1': LogLevel.ERROR, 'papc': LogLevel.CRITICAL}, {'logger1', 'papc'}),
    ({'logger1': LogLevel.ERROR, 'papc.sublogger': LogLevel.CRITICAL}, {'logger1', 'papc.sublogger'}),
    ({'pyjapc': LogLevel.ERROR, 'pydm': LogLevel.CRITICAL}, {'pyjapc', 'pydm'}),
    ({'pyjapc': LogLevel.ERROR, 'pjlsa': LogLevel.WARNING, 'pytimber': LogLevel.WARNING}, {'pyjapc', 'pjlsa', 'pytimber'}),
    ({'': LogLevel.ERROR, 'logger1': LogLevel.WARNING}, {'root', 'logger1'}),
    ({'root': LogLevel.ERROR, 'logger1': LogLevel.WARNING}, {'root', 'logger1'}),
    ({'ROOT': LogLevel.ERROR, 'logger1': LogLevel.WARNING}, {'root', 'logger1'}),
    ({'logger1': LogLevel.ERROR, 'logger1.sublogger': LogLevel.INFO, 'logger2': LogLevel.WARNING}, {'logger1', 'logger1.sublogger', 'logger2'}),
])
def test_clogconsole_detects_reuses_set_loggers_on_show_when_set(existing_loggers, initial_levels, expected_loggers, qtbot: QtBot):
    for logger_name, level in existing_loggers.items():
        logging.getLogger(logger_name).setLevel(level.value)

    widget = CLogConsole(loggers=initial_levels)
    qtbot.add_widget(widget)
    with qtbot.wait_exposed(widget):
        widget.show()
    assert set(widget.model._handlers.keys()) == expected_loggers


@pytest.fixture
def custom_model_class():

    class TestModel(AbstractLogConsoleModel):

        def __init__(self, parent=None):
            super().__init__(parent)
            self._selected_levels = {}

        @property
        def all_records(self):
            yield LogConsoleRecord(logger_name='test_logger', message='test message', level=LogLevel.WARNING, timestamp=0)

        def clear(self):
            pass

        def freeze(self):
            pass

        def unfreeze(self):
            pass

        @property
        def frozen(self):
            return False

        @property
        def buffer_size(self):
            return 1

        @buffer_size.setter
        def buffer_size(self, _):
            pass

        @property
        def visible_levels(self):
            return set()

        @visible_levels.setter
        def visible_levels(self, _):
            pass

        @property
        def selected_logger_levels(self):
            return self._selected_levels

        @selected_logger_levels.setter
        def selected_logger_levels(self, new_val):
            self._selected_levels = new_val

    return TestModel
