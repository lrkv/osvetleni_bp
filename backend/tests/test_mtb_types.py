import asyncio
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import test_async
from test_async import response, send, eventually
from mtb_outputs import encode_outputs


async def receive_wire(reader):
    return json.loads(await asyncio.wait_for(reader.readline(), 2))


class ModuleTypeTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = test_async.DaemonTests.asyncSetUp
    asyncTearDown = test_async.DaemonTests.asyncTearDown

    async def answer_type(self, name, reader=None, writer=None):
        reader = reader or self.reader
        writer = writer or self.writer
        request = await receive_wire(reader)
        self.assertEqual(request['command'], 'module')
        await send(writer, response(request, module={'address': request['address'], 'type': name}))
        return request

    async def test_mixed_modules_use_discovered_types_before_writing(self):
        self.client.set_outputs(11, {0: 1, 31: 0})
        self.client.set_outputs(1, {0: 0, 15: 60})
        requests = [await receive_wire(self.reader), await receive_wire(self.reader)]
        self.assertTrue(all(r['command'] == 'module' for r in requests))
        with self.assertRaises(TimeoutError):
            await asyncio.wait_for(self.reader.readline(), 0.03)
        for r in reversed(requests):
            name = 'MTB-LED' if r['address'] == 11 else 'MTB-UNI v4'
            await send(self.writer, response(r, module={'address': r['address'], 'type': name}))
        writes = [await receive_wire(self.reader), await receive_wire(self.reader)]
        by_address = {r['address']: r for r in writes}
        self.assertIs(by_address[11]['outputs']['0'], True)
        self.assertIs(by_address[11]['outputs']['31'], False)
        self.assertEqual(by_address[1]['outputs']['15'], {'type': 'flicker', 'value': 60})
        self.assertIs(type(by_address[1]['outputs']['0']['value']), int)
        for r in writes:
            await send(self.writer, response(r))
        await eventually(lambda: len(self.client.confirmed) == 2)
        self.assertEqual(self.client.status()['module_types'], {1: 'MTB-UNI v4', 11: 'MTB-LED'})

    async def test_led_static_state_does_not_send_periodic_updates(self):
        self.client.set_outputs(11, {0: 1})
        await self.answer_type('MTB-LED')
        request = await receive_wire(self.reader)
        self.assertIs(request['outputs']['0'], True)
        await send(self.writer, response(request))
        await eventually(lambda: self.client.confirmed.get(11) == {0: 1})
        with self.assertRaises(TimeoutError):
            await asyncio.wait_for(self.reader.readline(), .55)

    async def test_reconnect_discovers_replaced_module_type(self):
        self.client.set_outputs(11, {0: 1})
        await self.answer_type('MTB-UNI v4')
        request = await receive_wire(self.reader)
        self.assertEqual(request['outputs']['0'], {'type': 'plain', 'value': 1})
        await send(self.writer, response(request))
        await eventually(lambda: 11 in self.client.confirmed)
        self.writer.close()
        reader, writer = await asyncio.wait_for(self.connections.get(), 2)
        await self.answer_type('MTB-LED', reader, writer)
        request = await receive_wire(reader)
        self.assertIs(request['outputs']['0'], True)
        await send(writer, response(request))
        await eventually(lambda: self.client.module_types.get(11) == 'MTB-LED' and 11 in self.client.confirmed)

    async def test_unknown_module_type_does_not_guess_output_format(self):
        self.client.set_outputs(11, {0: 1})
        await self.answer_type('Unknown board')
        await eventually(lambda: 11 in self.client.status()['module_errors'])
        self.assertIn('Nepodporovaný typ', self.client.status()['module_errors'][11])
        with self.assertRaises(TimeoutError):
            await asyncio.wait_for(self.reader.readline(), 0.06)

    async def test_discovery_error_retries_without_writing(self):
        self.client.set_outputs(11, {0: 1})
        query = await receive_wire(self.reader)
        await send(self.writer, response(query, status='error', error={'message': 'Invalid module address'}))
        await eventually(lambda: self.client.module_errors.get(11) == 'Invalid module address')
        await self.answer_type('MTB-LED')
        request = await receive_wire(self.reader)
        self.assertIs(request['outputs']['0'], True)
        await send(self.writer, response(request))
        await eventually(lambda: 11 in self.client.confirmed)
        self.assertFalse(self.client.status()['module_errors'])

    async def test_daemon_validates_port_and_reports_its_error(self):
        self.client.set_outputs(11, {32: 1})
        await self.answer_type('MTB-LED')
        request = await receive_wire(self.reader)
        self.assertIs(request['outputs']['32'], True)
        await send(self.writer, response(request, status='error', error={'message': 'Invalid port 32'}))
        await eventually(lambda: self.client.module_errors.get(11) == 'Invalid port 32')
        self.assertNotIn(11, self.client.confirmed)


class OutputFormatTests(unittest.TestCase):
    def test_led_only_accepts_boolean_states(self):
        self.assertIs(encode_outputs('MTB-LED', {0: 1})[0], True)
        self.assertIs(encode_outputs('MTB-LED', {0: 0})[0], False)
        with self.assertRaises(ValueError):
            encode_outputs('MTB-LED', {0: 60})

    def test_port_numbers_do_not_limit_output_encoding(self):
        for kind in ('MTB-UNI', 'MTB-UNI v2', 'MTB-UNI v4', 'MTB-UNIS', 'MTB-LED'):
            for port in (-1, 16, 28, 32, 1000):
                with self.subTest(kind=kind, port=port):
                    encoded = encode_outputs(kind, {port: 1})
                    expected = True if kind == 'MTB-LED' else {'type': 'plain', 'value': 1}
                    self.assertEqual(encoded, {port: expected})
