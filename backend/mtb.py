"""Event-driven MTB TCP client; all methods run on the application's asyncio loop."""
import asyncio
import json
import logging
from contextlib import suppress

logger = logging.getLogger(__name__)


class DaemonClient:
    def __init__(self, host, port, *, timeout,
                 reconnect_delay, on_change=None):
        if timeout <= 0 or reconnect_delay <= 0:
            raise ValueError("MTB timeout a reconnect_delay musí být kladné.")
        self.host, self.port = host, port
        self.timeout, self.reconnect_delay = timeout, reconnect_delay
        self.on_change = on_change or (lambda: None)
        self.connected = False
        self.error = None
        self.module_errors = {}
        self.desired = {}
        self.confirmed = {}
        self._pending = {}
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
            "module_errors": dict(self.module_errors),
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
                        asyncio.open_connection(self.host, self.port, limit=1024 * 1024),
                        self.timeout,
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
                await asyncio.sleep(self.reconnect_delay)
        finally:
            await self._disconnect()

    async def _disconnect(self):
        self.connected = False
        for _, _, timer in self._pending.values():
            timer.cancel()
        self._pending.clear()
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
                await asyncio.wait_for(writer.wait_closed(), self.timeout)

    async def _send_loop(self):
        try:
            while True:
                await self._wake.wait()
                self._wake.clear()
                busy = {module for module, _, _ in self._pending.values()}
                for module, outputs in list(self.desired.items()):
                    if (module in busy or module in self._retry
                            or self.confirmed.get(module) == outputs):
                        continue
                    request_id = self._next_id
                    self._next_id += 1
                    request = {
                        "type": "request", "command": "module_set_outputs",
                        "id": request_id, "address": module,
                        "outputs": {
                            port: {"type": "plain" if value in (0, 1) else "flicker",
                                   "value": value}
                            for port, value in outputs.items()
                        },
                    }
                    timer = asyncio.get_running_loop().call_later(
                        self.timeout, self._request_timed_out, request_id
                    )
                    self._pending[request_id] = (module, outputs.copy(), timer)
                    self._writer.write((json.dumps(request) + "\n").encode("utf-8"))
                await asyncio.wait_for(self._writer.drain(), self.timeout)
        except (OSError, TimeoutError) as exc:
            self.error = str(exc) or "Vypršel čas pro odeslání dat."
            self._writer.close()  # Wakes the reader, which owns reconnecting.

    def _request_timed_out(self, request_id):
        if request_id in self._pending:
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
            if not isinstance(request_id, int) or request_id not in self._pending:
                continue
            module, outputs, timer = self._pending[request_id]
            if (message.get("command") != "module_set_outputs"
                    or message.get("address", module) != module):
                continue
            del self._pending[request_id]
            timer.cancel()
            if message.get("status") == "ok":
                self.confirmed[module] = outputs
                self.module_errors.pop(module, None)
            else:
                error = message.get("error")
                if not isinstance(error, dict):
                    error = {}
                self.module_errors[module] = str(error.get("message", "MTB příkaz selhal."))
                self.confirmed.pop(module, None)
                self._retry[module] = asyncio.get_running_loop().call_later(
                    self.reconnect_delay, self._retry_module, module
                )
                logger.warning("MTB modul %s: %s", module, self.module_errors[module])
            self.on_change()
            self._wake.set()  # Send newer state queued while this request was in flight.

    def _handle_event(self, message):
        if message.get("command") == "mtbusb":
            # USB may reconnect while the TCP connection stays open.
            self.confirmed.clear()
            usb = message.get("mtbusb")
            if not isinstance(usb, dict) or not isinstance(usb.get("connected"), bool):
                raise ValueError("Neplatná událost MTB-USB.")
            connected = usb["connected"]
            self.error = None if connected else "MTB-USB je odpojeno."
            self._wake.set()
            self.on_change()
        else:
            logger.debug("MTB událost: %s", message)
