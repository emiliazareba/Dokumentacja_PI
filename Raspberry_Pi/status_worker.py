from __future__ import annotations

import threading
from typing import Any

import config
from api_client import APIClient
from led_controller import LedController


class StatusWorker:

    def __init__(self, api: APIClient, leds: LedController) -> None:
        self.api = api
        self.leds = leds
        self._refresh_lock = threading.Lock()
    @staticmethod
    def _parse_statuses(response: dict[str, Any]) -> dict[str, str]:
        if not isinstance(response, dict):
            raise ValueError("Odpowiedź API nie jest obiektem")
        lockers = response.get("lockers")
        service_id = response.get("service_locker_id")
        service_open = response.get("is_service_open")
        if not isinstance(lockers, list) or not isinstance(service_id, str) or not isinstance(service_open, bool):
            raise ValueError("Niepełna odpowiedź statusowa API")
        if service_id not in config.RGB_PINS:
            raise ValueError(f"Nieznana skrytka serwisowa: {service_id}")

        statuses: dict[str, str] = {}
        for item in lockers:
            if not isinstance(item, dict):
                raise ValueError("Nieprawidłowy element listy skrytek")
            locker_id = item.get("locker_id")
            status = item.get("status")
            if locker_id not in config.RGB_PINS or locker_id == service_id:
                raise ValueError(f"Nieznana skrytka w odpowiedzi: {locker_id}")
            if status not in ("AVAILABLE", "OCCUPIED"):
                raise ValueError(f"Nieobsługiwany status {locker_id}: {status}")
            if locker_id in statuses:
                raise ValueError(f"Powtórzona skrytka: {locker_id}")
            statuses[locker_id] = status

        expected = set(config.RGB_PINS) - {service_id}
        if set(statuses) != expected:
            raise ValueError(f"Niepełna lista skrytek: oczekiwano {sorted(expected)}")
        statuses[service_id] = "SERVICE" if service_open else "OFF"
        return statuses

    def refresh(self) -> dict[str, str]:
        with self._refresh_lock:
            response = self.api.get_lockers()
            statuses = self._parse_statuses(response)
            self.leds.set_statuses(statuses)
            return statuses


