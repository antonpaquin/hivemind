import json
from typing import *

from citrine_client import api, errors
import citrine_client.cli.util as util


server, port = util.get_server()
subcommand_handler, dispatch = util.subcommand_registry()


def install_spec_args(args) -> List[Dict]:
    if args['name']:
        res = []
        for pkg_name in args['name']:
            res.append({'name': pkg_name})
        return res
            
    elif args['specfile']:
        res = []
        for fname in args['specfile']:
            res.append({'specfile': fname})
        return res

    elif 'localfile' in args and args['localfile'] is not None:
        return [{'localfile': args['localfile']}]
    
    elif (
            'url' in args
            and args['url'] is not None
            and 'hash' in args
            and args['hash'] is not None
    ):
        return [{'url': args['url'], 'package_hash': args['hash']}]
    
    else:
        raise errors.InvalidOptions('Invalid options for package specification', data={
            'allowed': [
                ['name'],
                ['--specfile'],
                ['--localfile'],
                ['--url', '--hash'],
            ]
        })
    
    
def install_or_fetch(args, command):
    res = []
    client = api.PackageClient(server, port, async_=True)
    specs = install_spec_args(args)

    for spec in specs:
        if 'name' in spec:
            name = spec['name']
            fill_bar, finish_bar = util.make_progress_bar(f'Downloading package {name}: ')
        elif 'specfile' in spec:
            name = spec['specfile']
            fill_bar, finish_bar = util.make_progress_bar(f'Downloading package for {name}: ')
        elif 'url' in spec:
            name = spec['url']
            fill_bar, finish_bar = util.make_progress_bar(f'Downloading package for {name}: ')
        elif 'localfile' in spec:
            name = spec['localfile']
            fill_bar, finish_bar = None, None
        else:
            raise errors.NoBranch(__file__)
        
        if command == 'install':
            print(f'Installing {name}')
        elif command == 'fetch':
            print(f'Fetching {name}')

        try:
            if command == 'install':
                result = client.install(**spec, progress_callback=fill_bar)
            elif command == 'fetch':
                result = client.fetch(**spec, progress_callback=fill_bar)
            else:
                raise errors.NoBranch(__file__)
        finally:
            if finish_bar is not None:
                finish_bar()

        res.append(result)
    print(json.dumps(res, indent=4))


@subcommand_handler('install')
def command_install(args):
    install_or_fetch(args, 'install')


@subcommand_handler('fetch')
def command_fetch(args):
    install_or_fetch(args, 'fetch')


@subcommand_handler('activate')
def command_activate(args):
    client = api.PackageClient(server, port)
    result = client.activate(name=args['name'], version=args['version'])
    print(json.dumps(result, indent=4))


@subcommand_handler('deactivate')
def command_deactivate(args):
    client = api.PackageClient(server, port)
    result = client.deactivate(name=args['name'], version=args['version'])
    print(json.dumps(result, indent=4))


@subcommand_handler('remove')
def command_deactivate(args):
    client = api.PackageClient(server, port)
    result = client.remove(name=args['name'], version=args['version'])
    print(json.dumps(result, indent=4))


@subcommand_handler('list')
def command_list(args):
    client = api.PackageClient(server, port)
    result = client.list()
    print(json.dumps(result, indent=4))


@subcommand_handler('search')
def command_list(args):
    client = api.PackageClient(server, port)
    result = client.search(query=args['query'])
    print(json.dumps(result, indent=4))
