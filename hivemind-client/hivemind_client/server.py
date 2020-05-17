import json
from typing import Dict, Optional

import requests

import hivemind_client.errors as errors


class DaemonLink(object):
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        
        
class AsyncRequest(object):
    def __init__(self, server, endpoint, params=None, files=None, jsn=None):
        self.server = server
        
        self.url = f'http://{server.host}:{server.port}/async{endpoint}'
        self.request_args = {}
        if params is not None:
            self.request_args['params'] = params
        if files is not None:
            self.request_args['files'] = files
        if json is not None:
            self.request_args['json'] = jsn

        self.status = None  # type: Optional[str]
        self.uid = None  # type: Optional[str]
        self.data = None  # type: Optional[Dict]
        self.result = None  # type: Optional[Dict]  # ...probably. It might be different, based on the wrapper
        self.error = None  # type: Optional[Dict]

    def refresh(self):
        url_update = f'http://{self.server.host}:{self.server.port}/async/get/{self.uid}'
        r = requests.get(url_update)
        resp = self._parse_response(r)
        self._update(resp)

    def _update(self, response):
        self.uid = response['uid']
        self.status = response['status']
        self.data = response['data']
        if 'result' in response:
            self.result = response['result']
        if 'error' in response:
            self.error = response['error']

    def __enter__(self):
        r = requests.post(self.url, **self.request_args)
        resp = self._parse_response(r)
        self._update(resp)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.done:
            return
        url_cancel = f'http://{self.server.host}:{self.server.port}/async/cancel/{self.uid}'
        requests.get(url_cancel)

    @property
    def done(self):
        return self.status in {'Error', 'Done'}

    @staticmethod
    def _parse_response(response):
        try:
            resp = json.loads(response.content)
        except json.JSONDecodeError:
            raise errors.ServerError('Malformed server response', data={'response': response.content.decode('utf-8')})
        if response.status_code != 200:
            raise errors.ServerError('Server rejected request', data=resp)
        return resp


def get_server() -> DaemonLink:
    # Probably wants to read a config file or something
    return DaemonLink(host='127.0.0.1', port=5402)