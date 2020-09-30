import json
import logging
from json import JSONDecodeError
from pathlib import Path
from typing import Any, Dict
from xdg import BaseDirectory
from hashlib import sha1
from .spec import PackageSpec


logger = logging.getLogger(__name__)


def read_spec_cache(entrypoint: Path) -> PackageSpec:
    cache_file = _get_cache_filename(entrypoint)
    pkg_spec_dict: Dict[str, Any]
    logger.debug(f'Attempting to get cache from {cache_file!s}')
    with cache_file.open('r') as f:
        try:
            pkg_spec_dict = json.load(f)
        except (ValueError, JSONDecodeError):
            pkg_spec_dict = {}
    return PackageSpec.from_dict(pkg_spec_dict)


def dump_spec_cache(spec: PackageSpec, entrypoint: Path):
    cache_file = _get_cache_filename(entrypoint, create_parent=True)
    logger.debug(f'Writing cache into {cache_file!s}')
    with cache_file.open('w') as f:
        json.dump(spec.to_dict(), f)


def _get_cache_filename(entrypoint: Path, create_parent: bool = False):
    path_hash = sha1(str(entrypoint.absolute()).encode())
    parent_path = Path(BaseDirectory.xdg_cache_home) / 'comrad' / path_hash.hexdigest()
    if create_parent:
        parent_path.mkdir(parents=True, exist_ok=True)
    return parent_path / f'spec_{entrypoint.name}.json'
