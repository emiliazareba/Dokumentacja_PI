from __future__ import annotations

import getpass
import logging
import os
import time
from typing import Any, Callable

import config
from api_client import APIClient, APIError
from led_controller import LedController
from status_worker import StatusWorker


class LockerCLI:
    def __init__(self, api: APIClient, leds: LedController, worker: StatusWorker):
        self.api = api
        self.leds = leds
        self.worker = worker

    @staticmethod
    def _message(result: dict[str, Any]) -> None:
        print(result.get("message") or "Operacja zakończona.")

    def _opened(self, locker_id: Any) -> None:
        if isinstance(locker_id, str) and locker_id in config.RGB_PINS:
            self.leds.opened(locker_id, getattr(config, "OPENED_DURATION", 7.0))
            print(f"Skrytka: {locker_id} (sygnał otwarcia)")

    def _error(self, locker_id: str | None = None) -> None:
        if locker_id and locker_id in config.RGB_PINS:
            self.leds.error(locker_id, getattr(config, "ERROR_DURATION", 3.0))

    def _execute(self, action: Callable[[], dict[str, Any]], *, locker_id: str | None = None) -> dict[str, Any] | None:
        try:
            result = action()
            self._message(result)
            return result
        except (APIError, ValueError, OSError) as exc:
            print(f"Błąd: {exc}")
            self._error(locker_id)
            return None

    def sender(self) -> None:
        self.worker.refresh()
        phone = input("Numer telefonu odbiorcy: ").strip()
        if not phone:
            print("Numer telefonu jest wymagany.")
            return
        result = self._execute(lambda: self.api.create_package(phone))
        if result and result.get("success"):
            if result.get("package_number") is not None:
                print(f"Numer przesyłki: {result['package_number']}")

            self._opened(result.get("locker_id"))
            time.sleep(config.OPENED_DURATION)
            self.worker.refresh()

    def recipient(self) -> None:
        self.worker.refresh()

        phone = input("Numer telefonu odbiorcy: ").strip()
        pin = getpass.getpass("PIN: ").strip()

        if not phone or not pin:
            print("Telefon i PIN są wymagane.")
            return

        result = self._execute(lambda: self.api.recipient_pickup(phone, pin))

        if result and result.get("success"):
            self._opened(result.get("locker_id"))
            time.sleep(config.OPENED_DURATION)
            self.worker.refresh()

    def courier(self) -> None:
        login = input("Login kuriera: ").strip()
        password = getpass.getpass("Hasło: ")
        if not login or not password:
            print("Login i hasło są wymagane.")
            return
        result = self._execute(lambda: self.api.courier_login(login, password))
        if not result or not result.get("authenticated"):
            print("Nie zalogowano kuriera.")
            return
        try:
            while True:
                print("\n*** KURIER ***")
                print("1. Odbierz przesyłki")
                print("2. Dostarcz przesyłkę")
                print("0. Wyloguj")
                choice = input("Wybierz: ").strip()
                if choice == "0":
                    break
                if choice == "1":
                    self.worker.refresh()
                    pickups = self._execute(self.api.courier_pickups)
                    if pickups is None:
                        continue
                    lockers = pickups.get("lockers_to_open", [])
                    if not lockers:
                        print("Brak przesyłek do odbioru.")
                        continue
                    print("Skrytki do odbioru:", ", ".join(lockers))
                    if input("Potwierdzić odbiór przesyłek? [t/N]: ").strip().lower() != "t":
                        continue
                    confirmed = self._execute(self.api.confirm_courier_pickups)
                    if confirmed and confirmed.get("success"):
                        for locker_id in confirmed.get("lockers_to_open", []):
                            self._opened(locker_id)

                        time.sleep(config.OPENED_DURATION)
                        self.worker.refresh()
                elif choice == "2":
                    self.worker.refresh()
                    raw = input("Numer przesyłki: ").strip()
                    if not raw.isdecimal():
                        print("Numer przesyłki musi być liczbą.")
                        continue
                    delivery = self._execute(lambda: self.api.courier_deliver(int(raw)))
                    if delivery and delivery.get("success"):
                        self._opened(delivery.get("locker_id"))
                        time.sleep(config.OPENED_DURATION)
                        self.worker.refresh()
                else:
                    print("Nieznana opcja.")
        finally:
            self._execute(self.api.courier_logout)

    def run(self) -> None:
        self.worker.refresh()
        try:
            while True:
                print("\n*** SKRYTKA POCZTOWA ***")
                print("1. Nadaj przesyłkę")
                print("2. Odbierz przesyłkę")
                print("3. Kurier")
                print("4. Obsługa techniczna")
                print("0. Zakończ")
                choice = input("Wybierz: ").strip()
                if choice == "0":
                    break
                if choice == "1":
                    self.sender()
                elif choice == "2":
                    self.recipient()
                elif choice == "3":
                    self.courier()
                elif choice == "4":
                    try:
                        statuses = self.worker.refresh()
                        service_id = config.LOCKER_IDS[-1]
                        status = statuses.get(service_id)

                        if status == "SERVICE":
                            print("Skrytka serwisowa jest otwarta.")
                        elif status == "OFF":
                            print("Skrytka serwisowa jest zamknięta.")
                        else:
                            print("Nieznany stan skrytki serwisowej.")
                    except (APIError, ValueError, RuntimeError, OSError) as exc:
                        print(f"Błąd pobierania statusu serwisowego: {exc}")
                else:
                    print("Nieznana opcja.")
        finally:
            pass


def main() -> None:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    no_gpio = os.getenv("CLI_NO_GPIO", "0") == "1"
    api = APIClient()
    with LedController(test_mode=no_gpio) as leds:
        worker = StatusWorker(api, leds)
        LockerCLI(api, leds, worker).run()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nZakończono.")
