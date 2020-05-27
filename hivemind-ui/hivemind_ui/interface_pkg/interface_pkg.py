import json
import os
import shutil
import tempfile
from typing import *
import zipfile

import cerberus
import hivemind_client

from hivemind_ui import config, errors
import hivemind_ui.interface_pkg.download as download


__all__ = [
    'init_interfaces',
    'synchronize',
    'install_interface',
    'remove_interface',
    'list_interfaces',
    'list_available_interfaces',
    'Interface',
    'InterfaceView',
]


metadata_validator = {
    'name': {
        'type': 'string',
        'required': True,
    },
    'human_name': {
        'type': 'string',
        'required': False,
    },
    'views': {
        'type': 'dict',
        'keysrules': {
            'type': 'string',
        },
        'valuesrules': {
            'type': 'dict',
            'schema': {
                'root': {
                    'type': 'string',
                    'required': True,
                },
                'page': {
                    'type': 'string',
                    'required': True,
                },
            },
        },
    },
    'requires_daemon': {
        'type': 'list',
        'schema': {
            'type': 'string',
        },
    },
}


# TODO: invalidate old package->interface index
package_interface_index = None  
interface_index = None


class Interface(object):
    def __init__(
            self,
            name: str,
            human_name: str,
            views: List['InterfaceView'],
            requires_daemon: List[str],
    ):
        self.name = name
        self.human_name = human_name
        self.views = views
        self.requires_daemon = requires_daemon

    @staticmethod
    def load(fpath: str) -> 'Interface':
        metadata_fname = os.path.join(fpath, 'meta.json')
        meta = _parse_metadata_file(metadata_fname)
        views = []
        for name, view_meta in meta['views'].items():
            rel_path = view_meta['root'].split('/')
            views.append(InterfaceView(
                name=name, 
                root=os.path.join(fpath, *rel_path),
                page=view_meta['page']
            ))
        return Interface(
            name=meta['name'], 
            human_name=meta['human_name'], 
            views=views, 
            requires_daemon=meta['requires_daemon']
        )


class InterfaceView(object):
    def __init__(
            self,
            name: str,
            root: str,
            page: str,
    ):
        self.name = name
        self.root = root
        self.page = page
        
    def get_page(self):
        return os.path.join(self.root, self.page)


def init_interfaces():
    interface_dir = os.path.join(config.get_config('storage.rootpath'), 'interfaces')
    if not os.path.isdir(interface_dir):
        os.makedirs(interface_dir)
    download_dir = os.path.join(config.get_config('storage.rootpath'), 'download')
    if not os.path.isdir(download_dir):
        os.makedirs(download_dir)
        
        
def synchronize():
    for interface_name in _check_wanted_interfaces():
        install_interface(interface_name)


def install_interface(interface_name: str):
    url, hashsum = _locate_interface(interface_name)
    if url.startswith('/'):
        fname = url
    else:
        fname = download.get_file(url, hashsum)
    _install_from_zip(fname)


def remove_interface(interface_name: str):
    interface_fpath = os.path.join(config.get_config('storage.rootpath'), 'interfaces', interface_name)
    shutil.rmtree(interface_fpath)


def list_interfaces() -> List[Interface]:
    interface_dir = os.path.join(config.get_config('storage.rootpath'), 'interfaces')
    res = []
    for fname in os.listdir(interface_dir):
        fpath = os.path.join(interface_dir, fname)
        res.append(Interface.load(fpath))
    return res


def list_available_interfaces() -> List[Tuple[str, str]]:
    client = hivemind_client.HivemindClient(config.get_config('daemon.server'), config.get_config('daemon.port'))
    list_packages = [p['name'] for p in client.package.list()['packages']]
    pi_index = get_package_interface_index()
    res = []
    for package in list_packages:
        if package not in pi_index:
            continue
        for interface in pi_index[package]:
            res.append((package, interface))
    return res


def _check_wanted_interfaces() -> List[str]:
    client = hivemind_client.HivemindClient(config.get_config('daemon.server'), config.get_config('daemon.port'))
    list_packages = [p['name'] for p in client.package.list()['packages']]
    pi_index = get_package_interface_index()
    wanted_interfaces = []
    for package in list_packages:
        if package in pi_index:
            wanted_interfaces.extend(pi_index[package])
    return wanted_interfaces


def _locate_interface(name: str) -> Tuple[str, str]:
    index = get_interface_index()
    return index[name]


def _install_from_zip(zip_fname: str):
    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(zip_fname) as zip_f:
            for fname in zip_f.filelist:
                zip_f.extract(fname, tmpdir)
        _install_from_temp(tmpdir)


def _install_from_temp(tmpdir: str):
    metadata_fname = os.path.join(tmpdir, 'meta.json')
    meta = _parse_metadata_file(metadata_fname)
    interface_name = meta['name']
    interface_fpath = os.path.join(config.get_config('storage.rootpath'), 'interfaces', interface_name)
    if os.path.exists(interface_fpath):
        # TODO: handle interface collision
        shutil.rmtree(interface_fpath)
    os.makedirs(interface_fpath)

    for fname in os.listdir(tmpdir):
        fpath = os.path.join(tmpdir, fname)
        fdest = os.path.join(interface_fpath, fname)
        if os.path.isdir(fpath):
            shutil.copytree(fpath, fdest)
        else:
            shutil.copy(fpath, fdest)


def _parse_metadata_file(fname: str):
    with open(fname, 'r') as in_f:
        meta = json.load(in_f)
    validator = cerberus.Validator(schema=metadata_validator)
    if not validator.validate(meta):
        raise errors.InterfaceError(json.dumps(validator.errors))
    return validator.document


def get_package_interface_index() -> Dict[str, List[str]]:
    # TODO: package_interface_index on web
    # This is a stubbed out version that pulls from the local machine
    # Eventually this wants to 'requests' out to amazon or something
    global package_interface_index
    sep = '|'
    repo_root = '/home/anton/code/hivemind/mock-repo'

    if package_interface_index is None:
        fname = os.path.join(repo_root, 'ui', 'package_interface')
        with open(fname, 'r') as in_f:
            raw = in_f.readlines()

        package_interface_index = {}
        for line in raw:
            package, interface = line.strip().split(sep)
            if package not in package_interface_index:
                package_interface_index[package] = []
            package_interface_index[package].append(interface)

    return package_interface_index


def get_interface_index() -> Dict[str, Tuple[str, str]]:
    # TODO: interface_index on web
    # This is a stubbed out version that pulls from the local machine
    # Eventually this wants to 'requests' out to amazon or something
    global interface_index
    sep = '|'
    repo_root = '/home/anton/code/hivemind/mock-repo'

    if interface_index is None:
        fname = os.path.join(repo_root, 'ui', 'index')
        with open(fname, 'r') as in_f:
            raw = in_f.readlines()

        interface_index = {}
        for line in raw:
            name, url, hashsum = line.strip().split(sep)
            interface_index[name] = (url, hashsum)

    return interface_index
