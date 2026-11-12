# Moduł Raspberry Pi — system skrytki pocztowej

## Opis

Moduł Raspberry Pi odpowiada za obsługę terminalowego interfejsu użytkownika, sterowanie diodami RGB przypisanymi do skrytek oraz komunikację z serwerem API.

System obsługuje nadawanie i odbieranie przesyłek, operacje kuriera oraz sprawdzanie stanu skrytki serwisowej.

## Struktura plików

| Plik | Funkcja |
|---|---|
| `main.py` | Uruchamia aplikację. |
| `cli.py` | Obsługuje menu użytkownika, nadawcę, odbiorcę, kuriera i opcję obsługi technicznej. |
| `api_client.py` | Odpowiada za komunikację z API oraz symulację operacji w trybie testowym. |
| `status_worker.py` | Pobiera statusy skrytek na żądanie i przekazuje je do sterownika diod. |
| `led_controller.py` | Steruje fizycznymi diodami RGB i tymczasowymi sygnałami świetlnymi. |
| `config.py` | Zawiera konfigurację maszyny, skrytek, pinów GPIO i kolorów diod. |

## Sygnalizacja diod RGB

- Zielony (`AVAILABLE`) — skrytka wolna.
- Fioletowy (`OCCUPIED`) — skrytka zajęta.
- Niebieski (`OPENED`) — sygnał otwarcia przez 3 sekundy.
- Czerwony (`ERROR`) — sygnalizacja błędu.
- Różowy (`SERVICE`) — otwarta skrytka serwisowa.
- Wyłączona dioda (`OFF`) — zamknięta skrytka serwisowa.

## Synchronizacja statusów

Raspberry Pi pobiera statusy skrytek z API na żądanie, m.in. przy uruchomieniu programu, przed operacjami oraz po ich zakończeniu.

Zrezygnowano z automatycznego odpytywania serwera co kilka sekund, aby ograniczyć niepotrzebne zapytania i uniknąć zakłócania sygnalizacji diod.

## Tryb testowy

Program umożliwia symulowanie operacji bez połączenia z rzeczywistym serwerem API.

W trybie testowym sprawdzono nadawanie i odbieranie przesyłek, operacje kuriera, wyświetlanie statusów oraz sterowanie fizycznymi diodami RGB.

Integracja z rzeczywistym API i pełna obsługa błędów wymagają dalszych testów.
