"""Run: python -m unittest discover -s backend/tests -v"""
import asyncio
import json
import socket
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from configurate import load_settings
from mtb import DaemonClient
from service import LightingService


def fixture_settings(layout="lrkv_tt.yaml"):
    settings = load_settings()
    settings["configurate"] = layout
    settings["hjop"] = {"enabled": False}
    return settings


async def eventually(predicate, timeout=2):
    async with asyncio.timeout(timeout):
        while not predicate():
            await asyncio.sleep(0.005)


def response(request, **extra):
    return {**request, "type": "response", "status": "ok", **extra}


async def send(writer, message):
    writer.write((json.dumps(message) + "\n").encode())
    await writer.drain()


async def receive(reader):
    return json.loads(await asyncio.wait_for(reader.readline(), 2))


class DaemonTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.connections = asyncio.Queue()
        self.writers = []
        self.handlers = set()

        async def peer(reader, writer):
            self.writers.append(writer)
            self.connections.put_nowait((reader, writer))
            task = asyncio.current_task()
            self.handlers.add(task)
            try:
                await writer.wait_closed()
            finally:
                self.handlers.discard(task)

        self.server = await asyncio.start_server(peer, "127.0.0.1", 0)
        port = self.server.sockets[0].getsockname()[1]
        self.client = DaemonClient(port=port, timeout=0.4, reconnect_delay=0.04)
        self.task = asyncio.create_task(self.client.run())
        self.reader, self.writer = await asyncio.wait_for(self.connections.get(), 2)

    async def asyncTearDown(self):
        self.task.cancel()
        await asyncio.gather(self.task, return_exceptions=True)
        for writer in self.writers:
            writer.close()
        self.server.close()
        await self.server.wait_closed()
        if self.handlers:
            await asyncio.gather(*list(self.handlers), return_exceptions=True)
        self.assertFalse(self.client._pending)
        self.assertFalse(self.client._retry)

    async def test_fragmented_and_reversed_responses_with_event(self):
        self.client.set_outputs(1, {0: 1})
        self.client.set_outputs(2, {0: 60})
        first, second = await receive(self.reader), await receive(self.reader)
        payload = (json.dumps({"type": "event", "command": "unknown"}) + "\n"
                   + json.dumps(response(second)) + "\n"
                   + json.dumps(response(first)) + "\n").encode()
        self.writer.write(payload[:17])
        await self.writer.drain()
        await asyncio.sleep(0.01)
        self.assertEqual(self.client.confirmed, {})
        self.writer.write(payload[17:])
        await self.writer.drain()
        await eventually(lambda: len(self.client.confirmed) == 2)
        self.assertEqual(self.client.confirmed, {1: {0: 1}, 2: {0: 60}})

    async def test_changes_coalesce_while_response_is_pending(self):
        self.client.set_outputs(1, {0: 1})
        first = await receive(self.reader)
        self.client.set_outputs(1, {0: 0})
        self.client.set_outputs(1, {0: 60})
        await send(self.writer, response(first))
        latest = await receive(self.reader)
        self.assertEqual(latest["outputs"]["0"]["value"], 60)
        await send(self.writer, response(latest))
        await eventually(lambda: self.client.confirmed.get(1) == {0: 60})
        self.client.set_outputs(1, {0: 60})
        with self.assertRaises(TimeoutError):
            await asyncio.wait_for(self.reader.readline(), 0.06)

    async def test_timeout_reconnects_and_resends_latest_state(self):
        self.client.set_outputs(1, {0: 1})
        await receive(self.reader)
        self.client.set_outputs(1, {0: 0})
        reader, writer = await asyncio.wait_for(self.connections.get(), 2)
        request = await receive(reader)
        self.assertEqual(request["outputs"]["0"]["value"], 0)
        await send(writer, response(request))
        await eventually(lambda: self.client.confirmed.get(1) == {0: 0})

    async def test_error_response_is_visible_and_retried(self):
        self.client.set_outputs(1, {0: 1})
        request = await receive(self.reader)
        await send(self.writer, response(request, status="error", error={"message": "offline"}))
        await eventually(lambda: self.client.module_errors.get(1) == "offline")
        retry = await receive(self.reader)
        await send(self.writer, response(retry))
        await eventually(lambda: self.client.confirmed.get(1) == {0: 1})
        self.assertFalse(self.client.module_errors)

    async def test_eof_reconnects(self):
        self.writer.close()
        reader, writer = await asyncio.wait_for(self.connections.get(), 2)
        self.client.set_outputs(1, {0: 1})
        request = await receive(reader)
        await send(writer, response(request))
        await eventually(lambda: self.client.confirmed.get(1) == {0: 1})

    async def test_unknown_id_cannot_confirm_request(self):
        self.client.set_outputs(1, {0: 1})
        request = await receive(self.reader)
        await send(self.writer, response(request, id=999999))
        await asyncio.sleep(0.02)
        self.assertEqual(self.client.confirmed, {})
        await send(self.writer, response(request))
        await eventually(lambda: self.client.confirmed.get(1) == {0: 1})


class ServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_unsupported_algorithm_does_not_prevent_startup(self):
        service = LightingService(fixture_settings())
        light = next(x for x in service.manager.items_by_id.values() if "address" in x)
        light["algorithm"] = "unimplemented_test_algorithm"
        module, port = map(int, light["address"].split(":"))

        async def offline(_client):
            await asyncio.Future()

        with patch.object(DaemonClient, "run", offline):
            with self.assertLogs("configurate", level="WARNING") as captured:
                await service.start()
            try:
                self.assertEqual(len(captured.output), 1)
                self.assertEqual(len(json.loads(service.snapshot)["configuration_errors"]), 1)
                self.assertFalse(light["is_on"])
                self.assertEqual(service.daemon.desired[module][port], 0)
                with self.assertNoLogs("configurate", level="WARNING"):
                    service.recalculate()
                service.manager.change_algorithm(light["id"], "trvale_zapnuto")
                service.recalculate()
                self.assertTrue(light["is_on"])
                self.assertNotIn("configuration_error", light)
                self.assertEqual(json.loads(service.snapshot)["configuration_errors"], [])
            finally:
                await service.stop()

    async def test_unchanged_state_is_not_published_and_queue_is_bounded(self):
        service = LightingService(fixture_settings())
        service.recalculate()
        queue = service.subscribe()
        queue.get_nowait()
        service.recalculate()
        self.assertTrue(queue.empty())
        leaf = next(x for x in service.manager.items_by_id.values() if "address" in x)
        service.manager.change_algorithm(leaf["id"], "trvale_vypnuto")
        service.recalculate()
        service.manager.change_algorithm(leaf["id"], "disco")
        service.recalculate()
        self.assertEqual(queue.qsize(), 1)
        self.assertIn('"algorithm": "disco"', queue.get_nowait())


class IntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_http_websocket_lan_and_silent_daemon(self):
        import httpx
        import uvicorn
        from websockets.asyncio.client import connect
        from websockets.exceptions import InvalidStatus
        from web import create_app

        peers = []
        requests = []
        handlers = set()

        async def silent_daemon(reader, writer):
            peers.append(writer)
            task = asyncio.current_task()
            handlers.add(task)
            try:
                while line := await reader.readline():
                    requests.append(json.loads(line))
            finally:
                writer.close()
                await writer.wait_closed()
                handlers.discard(task)

        daemon_server = await asyncio.start_server(silent_daemon, "127.0.0.1", 0)
        settings = fixture_settings()
        settings["mtb"]["port"] = daemon_server.sockets[0].getsockname()[1]
        settings["mtb"]["timeout"] = 10
        app = create_app(settings)
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        listener.setblocking(False)
        server = uvicorn.Server(uvicorn.Config(app, log_level="error", lifespan="on",
                                             ws="websockets-sansio"))
        server_task = asyncio.create_task(server.serve(sockets=[listener]))
        try:
            await eventually(lambda: server.started)
            base = f"http://127.0.0.1:{port}"
            wsurl = f"ws://127.0.0.1:{port}/api/ws"
            origin = "http://192.168.1.42:3000"
            async with httpx.AsyncClient(base_url=base, timeout=1) as http:
                preflight = await http.options("/api/algorithm", headers={
                    "Origin": origin, "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type",
                })
                self.assertEqual(preflight.headers["access-control-allow-origin"], origin)
                async with connect(wsurl, origin=origin) as ws1, connect(wsurl, origin=origin) as ws2:
                    first = json.loads(await ws1.recv())
                    await ws2.recv()
                    self.assertEqual(first["type"], "state")
                    leaf = app.state.service.manager.tree_data["groups"][0]["items"][0]
                    result = await http.post("/api/algorithm", json={
                        "item_id": leaf["id"], "new_algorithm": "trvale_vypnuto",
                    })
                    self.assertEqual(result.status_code, 202)

                    async def await_changed(ws):
                        async with asyncio.timeout(1):
                            while True:
                                state = json.loads(await ws.recv())
                                if state["type"] != "state":
                                    continue
                                item = state["structure"]["groups"][0]["items"][0]
                                if item["algorithm"] == "trvale_vypnuto":
                                    return state
                    one, two = await asyncio.gather(await_changed(ws1), await_changed(ws2))
                    self.assertFalse(one["structure"]["groups"][0]["items"][0]["is_on"])
                    self.assertEqual(one, two)
                    self.assertTrue(requests)  # Daemon received commands but never replied.
                    result = await http.get("/api/structure")
                    self.assertEqual(result.status_code, 200)
                    self.assertEqual((await http.post("/api/algorithm", json={
                        "item_id": leaf["id"], "new_algorithm": "invalid",
                    })).status_code, 422)
                    self.assertEqual((await http.post("/api/algorithm", json={
                        "item_id": -1, "new_algorithm": "disco",
                    })).status_code, 404)
                    # A backend timer tick must not produce an unchanged WS snapshot.
                    with self.assertRaises(TimeoutError):
                        async with asyncio.timeout(1.1):
                            while True:
                                message = json.loads(await ws1.recv())
                                self.assertEqual(message["type"], "clock")

                async with connect(wsurl, origin=origin) as reconnected:
                    state = json.loads(await reconnected.recv())
                    self.assertEqual(state["structure"]["groups"][0]["items"][0]["algorithm"],
                                     "trvale_vypnuto")
                with self.assertRaises(InvalidStatus):
                    async with connect(wsurl, origin="https://unrelated.example"):
                        self.fail("Origin should have been rejected")
        finally:
            server.should_exit = True
            await asyncio.wait_for(server_task, 5)
            for writer in peers:
                writer.close()
            daemon_server.close()
            await daemon_server.wait_closed()
            if handlers:
                await asyncio.gather(*list(handlers), return_exceptions=True)
            listener.close()


if __name__ == "__main__":
    unittest.main()
