import asyncio
import json
import logging
from datetime import datetime

from configurate import BASE_DIR, ConfigManager, SUPPORTED_ALGORITHMS
from mtb import DaemonClient
from hjop import HjopClock
from algorithm import ALGORITHM_LABELS
from events import upcoming_events
from connection_config import HjopConfig, MtbConfig, ServerConfig
from yaml_config import mapping, text

logger = logging.getLogger(__name__)


class LatestUpdates:
    """At most one pending message of each type; clock updates cannot evict state."""
    def __init__(self):
        self.messages = {}
        self.ready = asyncio.Event()

    def put(self, kind, message):
        self.messages[kind] = message
        self.ready.set()

    def get_nowait(self):
        if not self.messages:
            raise asyncio.QueueEmpty
        message = self.messages.pop(next(iter(self.messages)))
        if not self.messages:
            self.ready.clear()
        return message

    async def get(self):
        await self.ready.wait()
        return self.get_nowait()

    def empty(self):
        return not self.messages

    def qsize(self):
        return len(self.messages)


class LightingService:
    def __init__(self, settings):
        mapping(settings, ('configurate', 'light', 'server', 'mtb', 'hjop'), 'config')
        text(settings['configurate'], 'layout.file')
        ServerConfig.from_mapping(settings['server'])
        hjop_config = HjopConfig.from_mapping(settings['hjop'])
        mtb_config = MtbConfig.from_mapping(settings['mtb'])
        self.manager = ConfigManager.from_settings(settings['light'])
        self.manager.load_yaml(BASE_DIR / "config" / settings["configurate"])
        self.sunrise = str(settings["light"]["sunrise"])
        self.sunset = str(settings["light"]["sunset"])
        self.subscribers = set()
        self.snapshot = ""
        self.clock_snapshot = ""
        self.events_snapshot = ""
        self.tasks = []
        self.use_hjop = hjop_config.enabled
        self.model_clock = HjopClock(hjop_config, on_change=self.recalculate)
        self.daemon = DaemonClient(mtb_config, on_change=self.publish)

    def selected_time(self):
        status = self.model_clock.status()
        if self.use_hjop and status["available"]:
            now = self.model_clock.now()
            return now, {**status, "time": now.strftime("%H:%M:%S"), "reason": "model"}
        if not self.use_hjop:
            reason = "hjop_disabled"
        elif not status["connected"]:
            reason = "hjop_unavailable"
        elif not self.model_clock.synced:
            reason = "waiting_for_sync"
        elif not status["used"]:
            reason = "model_disabled"
        else:
            reason = "sync_expired"
        # MOD-CAS does not transmit the remote server's system clock.
        now = datetime.now()
        return now, {"source": "system", "time": now.strftime("%H:%M:%S"),
                     "connected": True, "available": True, "running": True,
                     "used": True, "speed": 1, "reason": reason,
                     "error": status["error"] if self.use_hjop else None}

    def time_status(self):
        return self.selected_time()[1]

    def recalculate(self):
        now, status = self.selected_time()
        for module, outputs in self.manager.calculate_outputs(self.sunrise, self.sunset, now=now).items():
            self.daemon.set_outputs(module, outputs)
        self.publish()
        self.publish_clock(status)
        self.publish_events(now, status)

    def publish_events(self, now, status=None):
        forecast = upcoming_events(self.manager, self.sunrise, self.sunset, now,
                                   status if status is not None else self.time_status(), datetime.now())
        message = json.dumps({"type": "events", "upcoming": forecast}, ensure_ascii=False)
        if message != self.events_snapshot:
            self.events_snapshot = message
            for queue in self.subscribers:
                queue.put("events", message)

    def publish_clock(self, status=None):
        message = json.dumps({"type": "clock", "clock": status if status is not None else self.time_status()}, ensure_ascii=False)
        if message == self.clock_snapshot:
            return
        self.clock_snapshot = message
        for queue in self.subscribers:
            queue.put("clock", message)

    def publish(self):
        snapshot = json.dumps({
            "type": "state",
            "structure": self.manager.tree_data,
            "hardware": self.daemon.status(),
            "algorithms": SUPPORTED_ALGORITHMS,
            "algorithm_labels": ALGORITHM_LABELS,
            "configuration_errors": [
                {"id": item["id"], "name": item.get("name"),
                 "message": item["configuration_error"]}
                for item in self.manager.items_by_id.values()
                if item.get("configuration_error")
            ],
        }, ensure_ascii=False)
        if snapshot == self.snapshot:
            return
        self.snapshot = snapshot
        for queue in self.subscribers:
            queue.put("state", snapshot)

    def subscribe(self):
        queue = LatestUpdates()
        self.subscribers.add(queue)
        initial = json.loads(self.snapshot)
        initial["clock"] = self.time_status()
        if self.events_snapshot:
            initial["upcoming"] = json.loads(self.events_snapshot)["upcoming"]
        queue.put("state", json.dumps(initial, ensure_ascii=False))
        return queue

    async def start(self):
        self.recalculate()
        self.tasks = [asyncio.create_task(self.daemon.run()),
                      asyncio.create_task(self._clock())]
        if self.use_hjop:
            self.tasks.append(asyncio.create_task(self.model_clock.run()))

    async def stop(self):
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()

    async def _clock(self):
        while True:
            await asyncio.sleep(1)
            try:
                self.recalculate()
            except Exception:
                logger.exception("Přepočet osvětlení selhal")
