from __future__ import annotations

import threading
import time
from typing import Mapping

from config import COLORS, RGB_PINS


class LedController:

    def __init__(self, test_mode: bool = False):
        self.test_mode = test_mode
        self._lock = threading.RLock()
        self._devices = {}
        self._base = {locker_id: "OFF" for locker_id in RGB_PINS}
        self._overrides = {}
        self._closed = False

        if not self.test_mode:
            from gpiozero import PWMLED
            try:
                for locker_id, channels in RGB_PINS.items():
                    if set(channels) != {"R", "G", "B"}:
                        raise ValueError(f"Niepełne RGB_PINS dla {locker_id}")
                    self._devices[locker_id] = {
                        color: PWMLED(pin, initial_value=0)
                        for color, pin in channels.items()
                    }
            except Exception:
                self.close()
                raise

    def _validate(self, locker_id: str, status: str) -> None:
        if locker_id not in RGB_PINS:
            raise ValueError(f"Nieznana skrytka: {locker_id}")
        if status not in COLORS:
            raise ValueError(f"Nieznany status/kolor: {status}")
        rgb = COLORS[status]
        if len(rgb) != 3 or any(not 0 <= x <= 1 for x in rgb):
            raise ValueError(f"Nieprawidłowy PWM dla {status}: {rgb}")

    def _render(self, locker_id: str) -> None:
        override = self._overrides.get(locker_id)
        if override is not None and time.monotonic() >= override[1]:
            del self._overrides[locker_id]
            override = None
        status = override[0] if override else self._base[locker_id]
        if self.test_mode:
            print(f"[LED] {locker_id}: {status} RGB={COLORS[status]}")
            return
        red, green, blue = COLORS[status]
        channels = self._devices[locker_id]
        channels["R"].value = red
        channels["G"].value = green
        channels["B"].value = blue

    def set_status(self, locker_id: str, status: str) -> None:
        with self._lock:
            self._ensure_open()
            self._validate(locker_id, status)
            self._base[locker_id] = status
            self._render(locker_id)

    def set_statuses(self, statuses: Mapping[str, str]) -> None:
        with self._lock:
            self._ensure_open()
            for locker_id, status in statuses.items():
                self._validate(locker_id, status)
            for locker_id, status in statuses.items():
                self._base[locker_id] = status
                self._render(locker_id)

    def signal(self, locker_id: str, status: str, duration: float) -> None:
        with self._lock:
            self._ensure_open()
            self._validate(locker_id, status)
            if duration <= 0:
                raise ValueError("Czas sygnału musi być dodatni")
            expiry = time.monotonic() + duration
            self._overrides[locker_id] = (status, expiry)
            self._render(locker_id)
        threading.Thread(target=self._expire, args=(locker_id, expiry), daemon=True).start()

    def _expire(self, locker_id: str, expiry: float) -> None:
        remaining = expiry - time.monotonic()
        if remaining > 0:
            time.sleep(remaining)
        with self._lock:
            if self._closed:
                return
            override = self._overrides.get(locker_id)
            if override is not None and override[1] == expiry:
                del self._overrides[locker_id]
                self._render(locker_id)

    def opened(self, locker_id: str, duration: float = 7.0) -> None:
        self.signal(locker_id, "OPENED", duration)

    def error(self, locker_id: str, duration: float = 3.0) -> None:
        self.signal(locker_id, "ERROR", duration)

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("LedController jest zamknięty")

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            for channels in self._devices.values():
                for led in channels.values():
                    led.close()
            self._devices.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

