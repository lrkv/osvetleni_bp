import asyncio
import json
import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hjop import HjopClock
from service import LatestUpdates, LightingService
from configurate import load_settings, ConfigManager


class LayoutTests(unittest.TestCase):
    def test_legacy_address_is_normalized_and_can_change(self):
        manager = ConfigManager()
        light = {"name": "Test", "adress": "1:0", "algorithm": "trvale_vypnuto"}
        with self.assertLogs("configurate", level="WARNING"):
            manager._process_item(light)
        self.assertEqual(light["address"], "1:0")
        self.assertNotIn("adress", light)
        self.assertTrue(manager.change_algorithm(light["id"], "trvale_zapnuto"))
        self.assertEqual(manager.calculate_outputs("05:32", "20:09", now=None), {1: {0: 1}})
        with self.assertRaises(ValueError):
            manager._process_item({"name": "Conflict", "address": "1:0", "adress": "1:1"})

    def test_exhibition_layout_updates_single_light_and_group(self):
        settings = load_settings()
        settings["configurate"] = "vystava_test.yaml"
        service = LightingService(settings)
        leaves = [item for item in service.manager.items_by_id.values() if 'items' not in item]
        self.assertEqual(len(leaves), 15)
        self.assertTrue(all('address' in item for item in leaves))
        group = service.manager.tree_data['groups'][0]
        service.manager.change_algorithm(group['id'], 'trvale_vypnuto')
        service.recalculate()
        self.assertEqual(service.daemon.desired, {1: dict.fromkeys(range(15), 0)})
        leaf = leaves[0]
        service.manager.change_algorithm(leaf['id'], 'trvale_zapnuto')
        service.recalculate()
        self.assertTrue(leaf['is_on'])
        self.assertEqual(service.daemon.desired[1][0], 1)
        self.assertIn('"algorithm": "trvale_zapnuto"', service.snapshot)
        service.manager.change_algorithm(group['id'], 'trvale_zapnuto')
        service.recalculate()
        self.assertEqual(service.daemon.desired, {1: dict.fromkeys(range(15), 1)})


class ClockTests(unittest.TestCase):
    def test_speed_pause_and_freeze(self):
        clock = HjopClock()
        clock.connected = True
        with patch("hjop.monotonic", return_value=10) as timer:
            clock.apply_time("-;MOD-CAS;1;9;2:25:21;1".split(";"))
            timer.return_value = 12
            self.assertEqual(clock.status()["time"], "02:25:39")
            clock.apply_time("-;MOD-CAS;0;9;2:25:39;1".split(";"))
            timer.return_value = 20
            self.assertEqual(clock.status()["time"], "02:25:39")
            self.assertFalse(clock.status()["running"])
            clock.apply_time("-;MOD-CAS;1;2,5;2:25:39;1".split(";"))
            timer.return_value = 22
            self.assertEqual(clock.status()["time"], "02:25:44")
            clock.freeze()
            timer.return_value = 1000
            self.assertEqual(clock.status()["time"], "02:25:44")
            self.assertFalse(clock.status()["available"])

    def test_midnight_sync_keeps_model_date(self):
        clock = HjopClock()
        clock.connected = True
        with patch("hjop.monotonic", return_value=0) as timer:
            clock.apply_time("-;MOD-CAS;1;9;23:59:55;1".split(";"))
            before = clock.now()
            timer.return_value = 1
            self.assertEqual(clock.status()["time"], "00:00:04")
            clock.apply_time("-;MOD-CAS;1;9;0:00:04;1".split(";"))
            self.assertEqual((clock.now().date() - before.date()).days, 1)

    def test_unavailable_and_invalid_messages(self):
        clock = HjopClock()
        self.assertIsNone(clock.now())
        self.assertFalse(clock.status()["available"])
        for message in ("-;MOD-CAS;1;nan;12:00:00;1", "-;MOD-CAS;1;-1;12:00:00;1",
                        "-;MOD-CAS;1;9;25:00:00;1", "-;MOD-CAS;START;9;12:00:00;1"):
            with self.subTest(message=message), self.assertRaises(ValueError):
                clock.apply_time(message.split(";"))
        clock.connected = True
        clock.apply_time("-;MOD-CAS;0;9;12:00:00;0".split(";"))
        self.assertFalse(clock.status()["available"])

    @patch("service.datetime")
    def test_algorithm_uses_model_time_and_static_modes_work_before_sync(self, system_time):
        system_time.now.return_value = datetime(2026, 10, 30, 22, 0)
        settings = load_settings()
        settings["hjop"] = {"enabled": True}
        settings["configurate"] = "lrkv_tt.yaml"
        service = LightingService(settings)
        service.manager.items_by_id = {
            1: {"id": 1, "name": "Shop", "address": "1:0", "algorithm": "prodejna"},
            2: {"id": 2, "name": "Window", "address": "1:1", "algorithm": "vyloha"},
        }
        service.recalculate()
        self.assertEqual(service.daemon.desired[1], {0: 0, 1: 1})
        service.model_clock.connected = True
        with patch("hjop.monotonic", return_value=0):
            service.model_clock.apply_time("-;MOD-CAS;0;9;07:00:00;1".split(";"))
            self.assertEqual(service.daemon.desired[1][0], 1)
            service.model_clock.apply_time("-;MOD-CAS;0;9;19:00:00;1".split(";"))
            self.assertEqual(service.daemon.desired[1][0], 0)
            service.model_clock.apply_time("-;MOD-CAS;0;9;12:00:00;1".split(";"))
            service.model_clock.freeze()
            self.assertEqual(service.daemon.desired[1][0], 0)

    @patch("service.datetime")
    def test_clock_selection_fallback_recovery_and_pause(self, system_time):
        system_time.now.return_value = datetime(2026, 10, 30, 12, 1, 10)
        settings = load_settings()
        settings["hjop"] = {"enabled": True}
        service = LightingService(settings)
        service.manager.items_by_id = {
            1: {"id": 1, "name": "Minute", "address": "1:0", "algorithm": "minuta"},
        }
        def check(source, reason, on):
            service.recalculate()
            status = service.time_status()
            self.assertEqual((status["source"], status["reason"]), (source, reason))
            self.assertEqual(service.daemon.desired[1][0], on)
            self.assertEqual(json.loads(service.clock_snapshot)["clock"], status)
            self.assertEqual(json.loads(service.subscribe().get_nowait())["clock"], status)
        check("system", "hjop_unavailable", 1)
        service.model_clock.connected = True
        check("system", "waiting_for_sync", 1)
        with patch("hjop.monotonic", return_value=0) as timer:
            service.model_clock.apply_time("-;MOD-CAS;0;6;03:00:00;0".split(";"))
            check("system", "model_disabled", 1)
            self.assertEqual(service.time_status()["time"], "12:01:10")
            service.model_clock.apply_time("-;MOD-CAS;1;6;03:00:00;1".split(";"))
            check("hjop", "model", 0)
            timer.return_value = 241
            check("system", "sync_expired", 1)
            service.model_clock.apply_time("-;MOD-CAS;0;6;03:00:00;1".split(";"))
            timer.return_value = 1000
            check("hjop", "model", 0)
            self.assertFalse(service.time_status()["running"])
            service.model_clock.freeze()
            check("system", "hjop_unavailable", 1)
            service.model_clock.connected = True
            service.model_clock.apply_time("-;MOD-CAS;1;6;03:00:00;1".split(";"))
            check("hjop", "model", 0)
            service.use_hjop = False
            check("system", "hjop_disabled", 1)

    def test_corridor_durations_stay_real_seconds(self):
        settings = load_settings()
        settings["hjop"] = {"enabled": True}
        settings["configurate"] = "lrkv_tt.yaml"
        service = LightingService(settings)
        service.manager.items_by_id = {
            1: {"id": 1, "name": "Hall", "address": "1:0", "algorithm": "chodba"},
        }
        service.model_clock.connected = True
        with patch("hjop.monotonic", return_value=0) as model_timer, \
             patch("algorithm.corridor.monotonic", return_value=0) as real_timer, \
             patch("algorithm.corridor.random.randint", side_effect=[60, 20, 60]):
            service.model_clock.apply_time("-;MOD-CAS;1;9;22:00:00;1".split(";"))
            real_timer.return_value = model_timer.return_value = 59
            service.recalculate()
            self.assertEqual(service.daemon.desired[1][0], 0)
            real_timer.return_value = model_timer.return_value = 60
            service.recalculate()
            self.assertEqual(service.daemon.desired[1][0], 1)
            real_timer.return_value = model_timer.return_value = 79
            service.recalculate()
            self.assertEqual(service.daemon.desired[1][0], 1)
            real_timer.return_value = model_timer.return_value = 80
            service.recalculate()
            self.assertEqual(service.daemon.desired[1][0], 0)


class TransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_bounded_queue_keeps_state_and_latest_clock(self):
        queue = LatestUpdates()
        queue.put("state", "state1")
        for n in range(100):
            queue.put("clock", str(n))
        queue.put("state", "state2")
        self.assertEqual(queue.qsize(), 2)
        self.assertEqual(await queue.get(), "state2")
        self.assertEqual(await queue.get(), "99")
        self.assertTrue(queue.empty())

    async def test_handshake_fragmentation_pong_and_reconnect(self):
        commands = []
        connections = 0
        writers = []
        handlers = set()

        async def peer(reader, writer):
            nonlocal connections
            handlers.add(asyncio.current_task())
            writers.append(writer)
            connections += 1
            try:
                commands.append((await reader.readline()).decode().strip())
                writer.write(b"-;HELLO;1.1\r\n-;MOD-")
                await writer.drain()
                await asyncio.sleep(0.01)
                writer.write(b"CAS;1;9;2:25:21;1\r\n-;PING;REQ-RESP;42\r\n")
                await writer.drain()
                commands.append((await reader.readline()).decode().strip())
                if connections == 1:
                    writer.close()
                else:
                    await reader.read()
            finally:
                writer.close()
                await writer.wait_closed()
                handlers.discard(asyncio.current_task())

        server = await asyncio.start_server(peer, "127.0.0.1", 0)
        clock = HjopClock(host="127.0.0.1", port=server.sockets[0].getsockname()[1], timeout=1, reconnect_delay=0.02)
        task = asyncio.create_task(clock.run())
        try:
            async with asyncio.timeout(3):
                while connections < 2 or not clock.synced or len(commands) < 4:
                    await asyncio.sleep(0.005)
            self.assertTrue(clock.status()["available"])
            self.assertEqual(commands, ["-;HELLO;1.1;osvetleni-clock", "-;PONG;42"] * 2)
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            server.close()
            await server.wait_closed()
            for writer in writers:
                writer.close()
            if handlers:
                await asyncio.gather(*list(handlers), return_exceptions=True)
        self.assertFalse(clock.connected)

    async def test_silent_server_times_out_without_blocking(self):
        writers = []
        handlers = set()

        async def peer(reader, writer):
            writers.append(writer)
            handlers.add(asyncio.current_task())
            try:
                await reader.read()
            finally:
                writer.close()
                await writer.wait_closed()
                handlers.discard(asyncio.current_task())

        server = await asyncio.start_server(peer, "127.0.0.1", 0)
        clock = HjopClock(host="127.0.0.1", port=server.sockets[0].getsockname()[1], timeout=0.05, reconnect_delay=0.02)
        task = asyncio.create_task(clock.run())
        try:
            async with asyncio.timeout(2):
                while len(writers) < 2:
                    await asyncio.sleep(0.005)
            self.assertIsNone(clock.now())
            self.assertFalse(clock.status()["available"])
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            server.close()
            await server.wait_closed()
            for writer in writers:
                writer.close()
            if handlers:
                await asyncio.gather(*list(handlers), return_exceptions=True)


if __name__ == "__main__":
    unittest.main()
