"""Event-driven MTB TCP client; all methods run on the application's asyncio loop."""
import asyncio
import json
import logging
from contextlib import suppress

from connection_config import MtbConfig
from mtb_outputs import encode_outputs

logger = logging.getLogger(__name__)


class DaemonClient:
    def __init__(self, config: MtbConfig, *, on_change=None):
        self.config = config
        self.on_change = on_change or (lambda: None)
        self.connected = False
        self.error = None
        self.module_errors = {}
        self.desired = {}
        self.confirmed = {}
        self._pending = {}
        self._queries = {}
        self.module_types = {}
        self._confirmed_wire = {}
        self._encoding_errors = {}
        self._retry = {}
        self._next_id = 1
        self._wake = asyncio.Event()
        self._writer = None

    def set_outputs(self, module_address, outputs_data):
        """Queue the latest desired state; never wait for a daemon response."""
        outputs = dict(outputs_data)
        if self.desired.get(module_address) != outputs:
            self.desired[module_address] = outputs
            self._wake.set()

    def status(self):
        return {
            "connected": self.connected,
            "error": self.error,
            "module_errors": {**self.module_errors, **self._encoding_errors},
            "module_types": dict(self.module_types),
            "pending_modules": sorted(
                module for module, outputs in self.desired.items()
                if self.confirmed.get(module) != outputs
            ),
        }

    async def run(self):
        """Reconnect in the background, keeping exactly one TCP reader."""
        try:
            while True:
                sender = None
                try:
                    reader, self._writer = await asyncio.wait_for(
                        asyncio.open_connection(self.config.host, self.config.port, limit=1024 * 1024),
                        self.config.timeout,
                    )
                    self.connected = True
                    self.error = None
                    self.on_change()
                    self._wake.set()
                    sender = asyncio.create_task(self._send_loop())
                    await self._read_loop(reader)
                except (OSError, ValueError, TimeoutError) as exc:
                    self.error = str(exc) or type(exc).__name__
                    logger.warning("MTB spojení: %s", self.error)
                finally:
                    if sender is not None:
                        sender.cancel()
                        await asyncio.gather(sender, return_exceptions=True)
                    await self._disconnect()
                await asyncio.sleep(self.config.reconnect_delay)
        finally:
            await self._disconnect()

    async def _disconnect(self):
        self.connected = False
        for _, _, timer, _ in self._pending.values():
            timer.cancel()
        self._pending.clear()
        for _, timer in self._queries.values():
            timer.cancel()
        self._queries.clear()
        self.module_types.clear()
        self._confirmed_wire.clear()
        self._encoding_errors.clear()
        for timer in self._retry.values():
            timer.cancel()
        self._retry.clear()
        self.confirmed.clear()
        self.module_errors.clear()
        writer, self._writer = self._writer, None
        self.on_change()
        if writer is not None:
            writer.close()
            with suppress(OSError, TimeoutError):
                await asyncio.wait_for(writer.wait_closed(), self.config.timeout)

    def _queue_request(self, command, module, **fields):
        request_id = self._next_id
        self._next_id += 1
        request = {"type": "request", "command": command, "id": request_id,
                   "address": module, **fields}
        timer = asyncio.get_running_loop().call_later(
            self.config.timeout, self._request_timed_out, request_id)
        self._writer.write((json.dumps(request) + "\n").encode("utf-8"))
        return request_id, timer

    async def _send_loop(self):
        try:
            while True:
                await self._wake.wait()
                self._wake.clear()
                busy = {entry[0] for entry in self._pending.values()} | {entry[0] for entry in self._queries.values()}
                for module, outputs in list(self.desired.items()):
                    if module in busy or module in self._retry:
                        continue
                    if module not in self.module_types:
                        request_id, timer = self._queue_request("module", module, state=False)
                        self._queries[request_id] = (module, timer)
                        continue
                    try:
                        wire = encode_outputs(self.module_types[module], outputs)
                    except ValueError as exc:
                        if self._encoding_errors.get(module) != str(exc):
                            self._encoding_errors[module] = str(exc)
                            self.on_change()
                        continue
                    self._encoding_errors.pop(module, None)
                    if self._confirmed_wire.get(module) == wire:
                        if self.confirmed.get(module) != outputs:
                            self.confirmed[module] = outputs.copy()
                            self.on_change()
                        continue
                    request_id, timer = self._queue_request("module_set_outputs", module, outputs=wire)
                    self._pending[request_id] = (module, outputs.copy(), timer, wire)
                await asyncio.wait_for(self._writer.drain(), self.config.timeout)
        except (OSError, TimeoutError) as exc:
            self.error = str(exc) or "Vypršel čas pro odeslání dat."
            self._writer.close()

    def _request_timed_out(self, request_id):
        if request_id in self._pending or request_id in self._queries:
            self.error = "MTB démon neodpověděl v časovém limitu."
            self._writer.close()

    def _retry_module(self, module):
        self._retry.pop(module, None)
        self._wake.set()

    async def _read_loop(self, reader):
        while True:
            line = await reader.readline()  # Sleeps until a complete JSON line arrives.
            if not line:
                raise ConnectionError(self.error or "MTB démon ukončil spojení.")
            if not line.strip():
                continue
            message = json.loads(line)
            if not isinstance(message, dict):
                raise ValueError("MTB zpráva musí být JSON objekt.")
            if message.get("type") == "event":
                self._handle_event(message)
                continue
            if message.get("type") != "response":
                continue
            request_id = message.get("id")
            if type(request_id) is not int:
                continue
            if request_id in self._queries:
                module, timer = self._queries[request_id]
                if message.get("command") != "module":
                    continue
                if message.get("status") == "ok":
                    info = message.get("module")
                    if (not isinstance(info, dict) or info.get("address") != module
                            or not isinstance(info.get("type"), str)):
                        raise ValueError("Neplatná odpověď na zjištění typu MTB modulu.")
                    self.module_types[module] = info["type"]
                else:
                    error = message.get("error")
                    self.module_errors[module] = str(error.get("message", "Nelze zjistit typ modulu.")
                                                     if isinstance(error, dict) else "Nelze zjistit typ modulu.")
                    self._retry[module] = asyncio.get_running_loop().call_later(
                        self.config.reconnect_delay, self._retry_module, module)
                timer.cancel()
                del self._queries[request_id]
                self.on_change()
                self._wake.set()
                continue
            if request_id not in self._pending:
                continue
            module, outputs, timer, wire = self._pending[request_id]
            if (message.get("command") != "module_set_outputs"
                    or message.get("address", module) != module):
                continue
            del self._pending[request_id]
            timer.cancel()
            if message.get("status") == "ok":
                self._confirmed_wire[module] = wire
                self.confirmed[module] = outputs
                self.module_errors.pop(module, None)
            else:
                error = message.get("error")
                if not isinstance(error, dict):
                    error = {}
                self.module_errors[module] = str(error.get("message", "MTB příkaz selhal."))
                self.confirmed.pop(module, None)
                self._confirmed_wire.pop(module, None)
                self.module_types.pop(module, None)
                self._retry[module] = asyncio.get_running_loop().call_later(
                    self.config.reconnect_delay, self._retry_module, module
                )
                logger.warning("MTB modul %s: %s", module, self.module_errors[module])
            self.on_change()
            self._wake.set()  # Send newer state queued while this request was in flight.

    def _handle_event(self, message):
        if message.get("command") == "mtbusb":
            # USB may reconnect while the TCP connection stays open.
            self.confirmed.clear()
            self._confirmed_wire.clear()
            self.module_types.clear()
            self._encoding_errors.clear()
            for _, _, timer, _ in self._pending.values():
                timer.cancel()
            self._pending.clear()
            for _, timer in self._queries.values():
                timer.cancel()
            self._queries.clear()
            usb = message.get("mtbusb")
            if not isinstance(usb, dict) or not isinstance(usb.get("connected"), bool):
                raise ValueError("Neplatná událost MTB-USB.")
            connected = usb["connected"]
            self.error = None if connected else "MTB-USB je odpojeno."
            self._wake.set()
            self.on_change()
        else:
            logger.debug("MTB událost: %s", message)
