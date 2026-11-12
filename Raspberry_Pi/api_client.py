from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import config


class APIError(Exception):

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code

class APIClient:
    def __init__(
        self,
        server_url: str | None = None,
        machine_id: str | None = None,
        api_key: str | None = None,
        test_mode: bool | None = None,
        api_key_header: str | None = None,
        admin_api_key: str | None = None,
        timeout: float = 5.0,
    ):
        self.server_url = (server_url or config.SERVER_URL).rstrip("/")
        self.machine_id = machine_id or config.MACHINE_ID
        self.api_key = config.API_KEY if api_key is None else api_key
        self.admin_api_key = admin_api_key
        self.test_mode = config.TEST_MODE if test_mode is None else test_mode
        self.api_key_header = api_key_header or getattr(config, "API_KEY_HEADER", "x-api-key")
        self.timeout = timeout
        self.courier_token: str | None = None
        self._mock_lockers = {
            "KR001_POX1": "AVAILABLE",
            "KR001_POX2": "OCCUPIED",
            "KR001_POX3": "AVAILABLE",
            "KR001_POX4": "OCCUPIED",
            "KR001_POX5": "AVAILABLE",
        }
        self._mock_service_open = False
        self._mock_service_open = False

    def _path(self, suffix: str) -> str:
        return f"/api/machines/{self.machine_id}/{suffix.lstrip('/')}"

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        courier_auth: bool = False,
        admin_auth: bool = False,
    ) -> dict[str, Any]:
        if self.test_mode:
            raise RuntimeError("Żądania HTTP są wyłączone w TEST_MODE")
        if not self.server_url.startswith(("http://", "https://")):
            raise APIError("SERVER_URL musi zaczynać się od http:// lub https://")
        key = self.admin_api_key if admin_auth else self.api_key
        if not key:
            raise APIError("Brak klucza API. Ustaw RASP_API_KEY / konfigurację klucza administratora")
        headers = {"Accept": "application/json", self.api_key_header: key}
        if courier_auth:
            if not self.courier_token:
                raise APIError("Kurier nie jest zalogowany")
            headers["Authorization"] = f"Bearer {self.courier_token}"
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(self.server_url + path, data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
                result = json.loads(body) if body else {}
                if not isinstance(result, dict):
                    raise APIError("Odpowiedź API nie jest obiektem JSON")
                return result
        except HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            try:
                details = json.loads(details).get("detail", details)
            except (ValueError, AttributeError):
                pass
            raise APIError(f"HTTP {exc.code}: {details}", exc.code) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise APIError(f"Brak połączenia z serwerem: {exc}") from exc
        except ValueError as exc:
            raise APIError(f"Nieprawidłowy JSON z serwera: {exc}") from exc

    def get_lockers(self) -> dict[str, Any]:
        if self.test_mode:
            return {
                "machine_id": self.machine_id,
                "service_locker_id": "KR001_SRV1",
                "is_service_open": self._mock_service_open,
                "lockers": [
                    {"locker_id": locker, "status": status}
                    for locker, status in self._mock_lockers.items()
                ],
            }
        result = self._request("GET", self._path("lockers"))
        if not isinstance(result.get("lockers"), list) or not isinstance(result.get("is_service_open"), bool):
            raise APIError("Odpowiedź serwera nie odpowiada MachineStatusResponse")
        return result

    def create_package(self, recipient_phone: str) -> dict[str, Any]:
        if self.test_mode:
            locker = next((k for k, v in self._mock_lockers.items() if v == "AVAILABLE"), None)
            if locker is None:
                raise APIError("Brak wolnych skrytek (symulacja)", 400)
            self._mock_lockers[locker] = "OCCUPIED"
            return {"success": True, "message": "Symulacja nadania", "package_number": 123456789, "locker_id": locker}
        return self._request("POST", self._path("sender/create-package"), {"recipient_phone": recipient_phone})

    def recipient_pickup(self, recipient_phone: str, pin_code: str) -> dict[str, Any]:
        if self.test_mode:
            locker = next((k for k, v in self._mock_lockers.items() if v == "OCCUPIED"), None)
            if locker is None:
                raise APIError("Brak zajętych skrytek (symulacja)", 400)
            if pin_code != "123456":
                raise APIError("Błędny PIN (symulacja; testowy PIN: 123456)", 400)
            self._mock_lockers[locker] = "AVAILABLE"
            return {"success": True, "message": "Symulacja odbioru", "locker_id": locker}
        return self._request("POST", self._path("recipient/pickup"), {"recipient_phone": recipient_phone, "pin_code": pin_code})

    def courier_login(self, courier_login: str, password: str) -> dict[str, Any]:
        if self.test_mode:
            self.courier_token = "test-token"
            return {"authenticated": True, "token_session": self.courier_token, "message": "Symulacja logowania"}
        result = self._request("POST", "/api/auth/courier-login", {"courier_login": courier_login, "password": password})
        if result.get("authenticated") and isinstance(result.get("token_session"), str):
            self.courier_token = result["token_session"]
        return result

    def courier_logout(self) -> dict[str, Any]:
        if self.test_mode:
            self.courier_token = None
            return {"success": True, "message": "Symulacja wylogowania"}
        try:
            return self._request("POST", "/api/auth/courier-logout", courier_auth=True)
        finally:
            self.courier_token = None

    def courier_pickups(self) -> dict[str, Any]:
        if self.test_mode:
            lockers = [
                k for k, v in self._mock_lockers.items()
                if v == "OCCUPIED"
            ]
            return {
                "success": True,
                "message": "Symulacja listy",
                "lockers_to_open": lockers
            }
        return self._request("GET", self._path("courier/pickups"), courier_auth=True)

    def confirm_courier_pickups(self) -> dict[str, Any]:
        if self.test_mode:
            lockers = [k for k, v in self._mock_lockers.items() if v == "OCCUPIED"]
            for locker in lockers:
                self._mock_lockers[locker] = "AVAILABLE"
            return {"success": True, "message": "Symulacja potwierdzenia", "lockers_to_open": lockers}
        return self._request("POST", self._path("courier/confirm-pickups"), courier_auth=True)

    def courier_deliver(self, package_number: int) -> dict[str, Any]:
        if self.test_mode:
            locker = next((k for k, v in self._mock_lockers.items() if v == "AVAILABLE"), None)
            if locker is None:
                raise APIError("Brak wolnych skrytek (symulacja)", 400)
            self._mock_lockers[locker] = "OCCUPIED"
            return {"success": True, "message": "Symulacja doręczenia", "locker_id": locker}
        return self._request("POST", self._path("courier/deliver"), {"package_number": package_number}, courier_auth=True)


if __name__ == "__main__":
    client = APIClient()
    try:
        print(json.dumps(client.get_lockers(), indent=2, ensure_ascii=False))
    except APIError as exc:
        print(f"Błąd API: {exc}")
        raise SystemExit(1)
