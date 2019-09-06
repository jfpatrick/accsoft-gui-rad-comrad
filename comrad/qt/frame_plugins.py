import os
import uuid
import inspect
import logging
import importlib
from typing import Dict, List, cast, Type
from types import ModuleType
from .plugin import CPlugin


logger = logging.getLogger(__name__)


def load_plugins_from_path(locations: List[str], token: str, base_type: Type = CPlugin):
    """
    Load plugins from file locations that match a specific token.

    Returns
    -------
    plugins: dict
        D

    Args:
        locations: list of file locations.
        token: a phrase that must match the end of the filename for it to be checked for.
        base_type: Base class of the plugins to look for. It should be a subclass of / or CPlugin.

    Returns:
        dictionary of plugins add from this folder.
    """
    plugin_classes: Dict[str, ModuleType] = {}
    for loc in locations:
        for root, _, files in os.walk(loc):
            if root.split(os.path.sep)[-1].startswith('__'):
                continue

            logger.debug(f'Looking for plugins at: {root}')
            for name in files:
                if not name.endswith(token):
                    continue
                temp_name = str(uuid.uuid4())
                logger.debug(f'Trying to load {name} (as {temp_name})...')
                spec: importlib.machinery.ModuleSpec = \
                    importlib.util.spec_from_file_location(name=temp_name, location=os.path.join(root, name))
                mod: ModuleType = importlib.util.module_from_spec(spec)
                loader = cast(importlib.machinery.SourceFileLoader, spec.loader)
                try:
                    loader.exec_module(mod)
                except ImportError as ex:
                    logger.exception(f'Cannot import plugin from {name}: {str(ex)}')
                    continue
                classes = {f'{temp_name}:{obj_name}': obj for obj_name, obj in inspect.getmembers(mod)
                           if (inspect.isclass(obj) and issubclass(obj, base_type) and obj is not base_type
                               and not inspect.isabstract(obj))}
                logger.debug(f'Found new plugin classes:\n{classes}')
                plugin_classes.update(classes)
    return plugin_classes
