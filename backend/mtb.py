import socket
from typing import Dict, Any
import json


class EDaemonResponse(Exception):
    pass


class DaemonClient:
    def __init__(self, host: str = '127.0.0.1', port: int = 3841):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))

    def request_response(self, request: Dict[str, Any]) -> Dict[str, Any]:
        to_send = request
        to_send['type'] = 'request'
        self.sock.send((json.dumps(to_send) + '\n').encode('utf-8'))

        while True:
            data = self.sock.recv(0xFFFF).decode('utf-8').strip()
            messages = [json.loads(msg) for msg in data.split('\n')]
            for message in messages:
                assert isinstance(message, dict)
                if message.get('command', '') == request['command']:
                    if message.get('status', '') != 'ok':
                        raise EDaemonResponse(
                            message.get('error', {}).get('message', 'Unknown error!')
                        )
                    return message

    def set_outputs(self, module_address: int, outputs_data: Dict[int, int]) -> None:
        formatted_outputs = {}

        for out_addr, val in outputs_data.items():
            if val in (0, 1):
                formatted_outputs[out_addr] = {'type': 'plain', 'value': val}
            else:
                formatted_outputs[out_addr] = {'type': 'flicker', 'value': val}

        self.request_response({
            'command': 'module_set_outputs',
            'address': module_address,
            'outputs': formatted_outputs,
        })

    def keep_alive(self) -> None:
        while True:
            self.sock.recv(0xFFFF).decode('utf-8').strip()