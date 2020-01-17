import pytest
import inspect
import operator
from typing import Tuple, List, Type
from unittest import mock
from pathlib import Path
from comrad.app.plugins.common import load_plugins_from_path, filter_enabled_plugins, CPlugin


class CPluginSubclass(CPlugin):
    pass


class NotCPluginSubclass:
    pass


@pytest.mark.parametrize('locations,locatable_files', [
    ([
        (Path('/loc1'), [
            ('/loc1/dir1', None, ['file1{token}', 'file2{token}']),
            ('/loc1/dir2', None, []),
            ('/loc1/__pymodules__', None, ['file3{token}', 'file4{token}']),
            ('/loc1/dir3', None, ['__init__.py']),
        ]),
    ], ['/loc1/dir1/file1{token}', '/loc1/dir1/file2{token}']),
    ([
        (Path('/loc1'), [
            ('/loc1/dir1', None, ['file1{token}', 'file2{token}']),
            ('/loc1/dir2', None, []),
        ]),
        (Path('/loc2'), [
            ('/loc2/dir1', None, ['file3{token}', 'file4{token}']),
            ('/loc2/dir2', None, []),
        ]),
    ], ['/loc1/dir1/file1{token}', '/loc1/dir1/file2{token}', '/loc2/dir1/file3{token}', '/loc2/dir1/file4{token}']),
    ([], []),
])
@pytest.mark.parametrize('expected_token,real_token,should_find_file', [
    ('_plugin.py', '_smth_else.py', False),
    ('_plugin.py', '_plugin.txt', False),
    ('_plugin', '_plugin.py', False),
    ('_plugin.py', '_plugin.py', True),
])
@pytest.mark.parametrize('base_class,requested_base_class,should_find_class', [
    (CPlugin, CPlugin, True),
    (CPlugin, None, True),
    (CPlugin, NotCPluginSubclass, False),
    (CPlugin, CPluginSubclass, False),
    (object, CPlugin, False),
    (object, None, False),
    (CPluginSubclass, CPlugin, True),
    (CPluginSubclass, CPluginSubclass, True),
    (CPluginSubclass, None, True),
    (CPluginSubclass, NotCPluginSubclass, False),
    (NotCPluginSubclass, CPlugin, False),
    (NotCPluginSubclass, None, False),
    (NotCPluginSubclass, CPluginSubclass, False),
    (NotCPluginSubclass, NotCPluginSubclass, True),
])
def test_load_plugins_from_path(locations, locatable_files, expected_token, real_token, should_find_file, base_class, requested_base_class, should_find_class):

    class FakeModule:
        class FakePluginClass(base_class):
            pass

        class FakeNotImportantClass:
            pass

        fake_not_important_attr = True

    map_filenames = lambda x: x.format(token=real_token)

    def fake_walk(location: Path):
        def map_token(content: Tuple[str, None, List[str]]) -> Tuple[str, None, List[str]]:
            name, _, files = content
            return name, None, list(map(map_filenames, files))

        for loc, contents in locations:
            if loc == location:
                return list(map(map_token, contents))
        else:
            return []

    fake_members = inspect.getmembers(FakeModule)

    def get_fake_members(*_, **__):
        return fake_members

    with mock.patch('os.walk', side_effect=fake_walk):
        with mock.patch('importlib.util.spec_from_file_location') as spec_mock:
            with mock.patch('importlib.util.module_from_spec', return_value=FakeModule):
                with mock.patch('inspect.getmembers', side_effect=get_fake_members):
                    kwargs = {}
                    if requested_base_class is not None:
                        kwargs['base_type'] = requested_base_class
                    loaded_classes = load_plugins_from_path(locations=map(operator.itemgetter(0), locations),
                                                            token=expected_token,
                                                            **kwargs)
                    if should_find_file and len(locatable_files) > 0:
                        spec_mock.assert_has_calls([mock.call(location=Path(path), name=mock.ANY)
                                                    for path in map(map_filenames, locatable_files)],
                                                   any_order=True)

                        if should_find_class:
                            assert any(x == FakeModule.FakePluginClass for x in loaded_classes.values())

                            # Check that we do not load anything but the classes that we are interested in
                            assert not any(x == FakeModule.FakeNotImportantClass or not inspect.isclass(x) for x in
                                           loaded_classes.values())

                            return
                    else:
                        spec_mock.assert_not_called()
                    assert loaded_classes == {}


@pytest.mark.parametrize('whitelist,blacklist,plugins', [
    ([], [], [('enabled', 'PluginEnabled')]),
    (['enabled'], [], [('enabled', 'PluginEnabled')]),
    (['enabled'], ['disabled'], [('enabled', 'PluginEnabled')]),
    (['disabled'], [], [('enabled', 'PluginEnabled'), ('disabled', 'PluginDisabled')]),
    (['disabled'], ['enabled'], [('disabled', 'PluginDisabled')]),
    ([], ['enabled'], []),
])
def test_filter_enabled_plugins(whitelist, blacklist, plugins):

    class PluginEnabled(CPlugin):
        plugin_id = 'enabled'
        enabled = True

    class PluginDisabled(CPlugin):
        plugin_id = 'disabled'
        enabled = False

    class PluginIncomplete(CPlugin):
        pass

    class PluginNotSubclass:
        pass

    mapping = {cls.__name__: cls for cls in [PluginEnabled, PluginDisabled, PluginIncomplete, PluginNotSubclass]}

    enabled_plugins = set(filter_enabled_plugins(plugins=[PluginIncomplete, PluginNotSubclass],
                                                 whitelist=whitelist,
                                                 blacklist=blacklist))
    assert enabled_plugins == set()

    def map_plugins(plugin: Tuple[str, str]) -> Tuple[str, Type]:
        return plugin[0], mapping[plugin[1]]

    plugins = set(map(map_plugins, plugins))
    print(f'Expecting {plugins}')

    enabled_plugins = set(filter_enabled_plugins(plugins=[PluginEnabled, PluginDisabled],
                                                 whitelist=whitelist,
                                                 blacklist=blacklist))
    assert enabled_plugins == plugins

    enabled_plugins = set(filter_enabled_plugins(plugins=[PluginEnabled,
                                                          PluginDisabled,
                                                          PluginIncomplete,
                                                          PluginNotSubclass],
                                                 whitelist=whitelist,
                                                 blacklist=blacklist))
    assert enabled_plugins == plugins


@pytest.mark.skip
def test_get_or_create_menu():
    pass


@pytest.mark.skip
def test_load_toolbar_plugins():
    # TODO: Test order as well
    pass


@pytest.mark.skip
@pytest.mark.parametrize('cmdline_path,env_path,shipped_path', [
    ('', '', ''),
])
def test_load_menubar_plugins(cmdline_path, env_path, shipped_path):
    pass


@pytest.mark.skip
def test_load_statusbar_plugins():
    pass
