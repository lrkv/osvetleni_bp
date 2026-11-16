"""Read-only hJOP panel client: HELLO, PONG and incoming model-time broadcasts."""
import asyncio
import logging
import math
from contextlib import suppress
from datetime import datetime, timedelta
from time import monotonic

logger = logging.getLogger(__name__)


class HjopClock:
    def __init__(self, host, port, *, timeout,
                 reconnect_delay, idle_timeout, sync_timeout, on_change=None):
        self.host, self.port = host, int(port)
        self.timeout = float(timeout)
        self.reconnect_delay = float(reconnect_delay)
        self.idle_timeout = float(idle_timeout)
        self.sync_timeout = float(sync_timeout)
        if min(self.timeout, self.reconnect_delay, self.idle_timeout, self.sync_timeout) <= 0:
            raise ValueError("Časové limity hJOP musí být kladné.")
        self.on_change = on_change or (lambda: None)
        self.connected = False
        self.synced = False
        self.running = False
        self.used = False
        self.speed = 1.0
        self.error = None
        self._base = None
        self._received_at = 0.0

    def now(self):
        if self._base is None:
            return None
        elapsed = (monotonic() - self._received_at
                   if self.connected and self.synced and self.running and self.used else 0)
        return self._base + timedelta(seconds=max(0, elapsed) * self.speed)

    def status(self):
        now = self.now()
        fresh = not (self.used and self.running) or monotonic() - self._received_at < self.sync_timeout
        return {
            "source": "hjop", "time": now.strftime("%H:%M:%S") if now else None,
            "connected": self.connected, "available": self.connected and self.synced and self.used and fresh,
            "running": self.running and self.connected and self.synced and self.used,
            "used": self.used, "speed": self.speed, "error": self.error,
        }

    def apply_time(self, fields):
        if len(fields) < 6 or fields[2] not in ("0", "1") or fields[5] not in ("0", "1"):
            raise ValueError("Neplatná zpráva modelového času hJOP.")
        speed = float(fields[3].replace(",", "."))
        if not math.isfinite(speed) or speed < 0:
            raise ValueError("Neplatná rychlost modelového času hJOP.")
        hour, minute, second = map(int, fields[4].split(":"))
        previous = self.now()
        # The protocol sends time-of-day only. Keep a synthetic model date across midnight.
        anchor = previous or datetime(2000, 1, 2)
        candidate = anchor.replace(hour=hour, minute=minute, second=second, microsecond=0)
        if previous is not None:
            candidate = min((candidate + timedelta(days=d) for d in (-1, 0, 1)),
                            key=lambda value: abs(value - previous))
        self._base = candidate
        self._received_at = monotonic()
        self.speed = speed
        self.running = fields[2] == "1"
        self.used = fields[5] == "1"
        self.synced = True
        self.error = None
        self.on_change()

    def freeze(self):
        self._base = self.now()
        self.connected = False
        self.synced = False
        self.on_change()

    async def run(self):
        while True:
            writer = None
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(self.host, self.port, limit=1024 * 1024),
                    self.timeout,
                )
                writer.write(b"-;HELLO;1.1;osvetleni-clock\n")
                await asyncio.wait_for(writer.drain(), self.timeout)
                deadline = monotonic() + self.timeout
                while True:
                    remaining = (self.sync_timeout - (monotonic() - self._received_at)
                                 if self.synced and self.used and self.running else
                                 math.inf if self.synced else deadline - monotonic())
                    if remaining <= 0:
                        raise TimeoutError("hJOP neposlal synchronizaci času.")
                    line = await asyncio.wait_for(reader.readline(), min(self.idle_timeout, remaining))
                    if not line:
                        raise ConnectionError("hJOP ukončil spojení.")
                    fields = line.decode("utf-8").strip().split(";")
                    if len(fields) < 2 or fields[0] != "-":
                        continue
                    command = fields[1].upper()
                    if command == "HELLO":
                        self.connected = True
                        self.error = None
                        self.on_change()
                    elif command == "PING" and len(fields) >= 4 and fields[2].upper() == "REQ-RESP":
                        ping_id = int(fields[3])
                        writer.write(f"-;PONG;{ping_id}\n".encode("ascii"))
                        await asyncio.wait_for(writer.drain(), self.timeout)
                    elif command == "MOD-CAS":
                        if not self.connected:
                            raise ValueError("hJOP poslal čas před potvrzením spojení.")
                        self.apply_time(fields)
            except (OSError, ValueError, TimeoutError) as exc:
                self.error = str(exc) or "hJOP neodpovídá."
                logger.warning("hJOP: %s", self.error)
            finally:
                self.freeze()
                if writer is not None:
                    writer.close()
                    with suppress(OSError, TimeoutError):
                        await asyncio.wait_for(writer.wait_closed(), self.timeout)
            await asyncio.sleep(self.reconnect_delay)
