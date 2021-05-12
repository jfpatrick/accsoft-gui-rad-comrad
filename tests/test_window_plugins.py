import pytest
import inspect
import operator
from typing import Tuple, List, Type
from unittest import mock
from pathlib import Path
from qtpy.QtCore import Qt
from qtpy.QtGui import QIcon
from comrad.app.plugins.common import load_plugins_from_path, filter_enabled_plugins, CPlugin, CActionPlugin
from comrad.app.plugins._config import WindowPluginConfigTrie


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
        with mock.patch('importlib.util.spec_from_file_location') as spec_from_file_location:
            with mock.patch('importlib.util.module_from_spec', return_value=FakeModule):
                with mock.patch('inspect.getmembers', side_effect=get_fake_members):
                    kwargs = {}
                    if requested_base_class is not None:
                        kwargs['base_type'] = requested_base_class
                    loaded_classes = load_plugins_from_path(locations=map(operator.itemgetter(0), locations),
                                                            token=expected_token,
                                                            **kwargs)
                    if should_find_file and len(locatable_files) > 0:
                        spec_from_file_location.assert_has_calls([mock.call(location=Path(path), name=mock.ANY)
                                                                  for path in map(map_filenames, locatable_files)],
                                                                 any_order=True)

                        if should_find_class:
                            assert any(x == FakeModule.FakePluginClass for x in loaded_classes.values())

                            # Check that we do not load anything but the classes that we are interested in
                            assert not any(x == FakeModule.FakeNotImportantClass or not inspect.isclass(x) for x in
                                           loaded_classes.values())

                            return
                    else:
                        spec_from_file_location.assert_not_called()
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


def test_trie_default_dict_on_init():
    trie = WindowPluginConfigTrie()
    assert trie.root == {}
    assert trie.root['test'] == {}
    assert trie.root == {'test': {}}
    assert trie.root['test']['subtree'] == {}
    assert trie.root == {'test': {'subtree': {}}}
    assert trie.root['test']['subtree']['subsubtree'] == {}
    assert trie.root == {'test': {'subtree': {'subsubtree': {}}}}


def test_trie_add_val_succeeds_with_proper_hierarchy():
    trie = WindowPluginConfigTrie()
    assert trie.root == {}
    trie.add_val('key', 'val1')
    assert trie.root == {'key': 'val1'}
    trie.add_val('key2', 'val2')
    assert trie.root == {'key': 'val1', 'key2': 'val2'}
    trie.add_val('key3.subkey', 'val3')
    assert trie.root == {'key': 'val1', 'key2': 'val2', 'key3': {'subkey': 'val3'}}
    trie.add_val('key3.subkey2.subsubkey', 'val4')
    assert trie.root == {'key': 'val1', 'key2': 'val2', 'key3': {'subkey': 'val3', 'subkey2': {'subsubkey': 'val4'}}}


@pytest.mark.parametrize('added_key,faulty_key', [
    ('key', ''),
    ('key', 'key.subkey'),
    ('key.subkey', 'key.subkey.subsubkey'),
    ('key.subkey', 'key.subkey.subsubkey.subsubsub'),
])
def test_trie_add_val_fails_with_invalid_hierarchy(added_key, faulty_key):
    # When first using key for non-dictionary value, and then trying to assign a subkey
    trie = WindowPluginConfigTrie()
    assert trie.root == {}
    trie.add_val(added_key, 'val1')
    with pytest.raises(KeyError):
        trie.add_val(faulty_key, 'val2')


def test_trie_add_val_fails_with_empty_key():
    trie = WindowPluginConfigTrie()
    assert trie.root == {}
    with pytest.raises(KeyError):
        trie.add_val('', 'val1')


@pytest.mark.parametrize('inputs,key,expected_config', [
    ([], '', None),
    ([], 'plugin_id', None),
    ([('plugin_id.key', 'val')], '', None),
    ([('plugin_id.key', 'val')], 'plugin_id', {'key': 'val'}),
    ([('plugin_id.key.subkey.subsubkey', 'val'), ('plugin_id.key.subkey2', 'val3'), ('plugin_id.key2', 'val2')], 'plugin_id', {'key.subkey.subsubkey': 'val', 'key.subkey2': 'val3', 'key2': 'val2'}),
    ([('plugin_id.key.subkey.subsubkey', 'val'), ('plugin_id.key.subkey2', 'val3'), ('plugin_id.key2', 'val2')], 'plugin_id.key', {'subkey.subsubkey': 'val', 'subkey2': 'val3'}),
    ([('plugin_id.key.subkey.subsubkey', 'val'), ('plugin_id.key.subkey2', 'val3'), ('plugin_id.key2', 'val2')], 'plugin_id.key.subkey', {'subsubkey': 'val'}),
    ([('plugin_id.key.subkey.subsubkey', 'val'), ('plugin_id.key.subkey2', 'val3'), ('plugin_id.key2', 'val2')], 'plugin_id.key2', None),
    ([('plugin_id.key.subkey.subsubkey', 'val'), ('plugin_id.key.subkey2', 'val3'), ('plugin_id.key2', 'val2')], '.', None),
    ([('plugin_id.key.subkey.subsubkey', 'val'), ('plugin_id.key.subkey2', 'val3'), ('plugin_id.key2', 'val2')], '.key', None),
    ([('plugin_id.key.subkey.subsubkey', 'val'), ('plugin_id.key.subkey2', 'val3'), ('plugin_id.key2', 'val2')], 'plugin_id.', None),
    ([('plugin_id.key.subkey.subsubkey', 'val'), ('plugin_id.key.subkey2', 'val3'), ('plugin_id.key2', 'val2')], 'unknown_id', None),
])
def test_trie_get_flat_config(inputs, key, expected_config):
    trie = WindowPluginConfigTrie()
    for k, v in inputs:
        trie.add_val(key=k, val=v)
    assert trie.get_flat_config(key) == expected_config


@pytest.mark.parametrize('config', [None, {}, {'something': 'val'}])
@pytest.mark.parametrize('orig_title', ['', 'Test title'])
@pytest.mark.parametrize('orig_icon,expected_font_icon', [
    (None, None),
    ('iconname', True),
    (QIcon(), False),
])
@pytest.mark.parametrize('orig_shortcut', [None, 'Ctrl+A'])
@mock.patch('qtpy.QtWidgets.QAction.setShortcutContext')
@mock.patch('qtpy.QtWidgets.QAction.setIcon')
@mock.patch('qtpy.QtWidgets.QAction.setShortcut')
@mock.patch('comrad.app.plugins.common.IconFont')
def test_action_plugin_creates_action(IconFont, setShortcut, setIcon, setShortcutContext, config, orig_title,
                                      orig_icon, orig_shortcut, expected_font_icon):

    class PluginSubclass(CActionPlugin):

        icon = orig_icon
        shortcut = orig_shortcut

        def title(self):
            return orig_title

        def triggered(self):
            pass

    plugin = PluginSubclass()
    action = plugin.create_action(config)
    assert action.text() == orig_title
    if orig_shortcut is None:
        setShortcut.assert_not_called()
    else:
        setShortcut.assert_called_once_with(orig_shortcut)
    assert action.receivers(action.triggered) == 1
    setShortcutContext.assert_called_once_with(Qt.ApplicationShortcut)
    if expected_font_icon is None:
        setIcon.assert_not_called()
    elif expected_font_icon is True:
        setIcon.assert_called_once_with(IconFont.return_value.icon.return_value)
        IconFont.return_value.icon.assert_called_once_with(orig_icon)
    else:
        setIcon.assert_called_once_with(orig_icon)
