import os

MACHINE_ID = "KR001"
SERVER_URL = os.getenv("SERVER_URL", "http://127.0.0.1:8000").rstrip("/")
API_KEY = os.getenv("RASP_API_KEY", "")

# True = testy bez serwera
# False = komunikacja z prawdziwym backendem
TEST_MODE = True


OPENED_DURATION = 3.0
ERROR_DURATION = 3.0

LOCKER_IDS = (
    "KR001_POX1",
    "KR001_POX2",
    "KR001_POX3",
    "KR001_POX4",
    "KR001_POX5",
    "KR001_SRV1",
)

GPIO_CHANNELS = {
    "KR001_POX1": (14, 15, 18),
    "KR001_POX2": (17, 27, 22),
    "KR001_POX3": (10, 9, 11),
    "KR001_POX4": (25, 8, 7),
    "KR001_POX5": (5, 6, 13),
    "KR001_SRV1": (16, 20, 21),
}

RGB_PINS = {
    "KR001_POX1": {"R": 18, "G": 15, "B": 14},
    "KR001_POX2": {"R": 22, "G": 27, "B": 17},
    "KR001_POX3": {"R": 11, "G": 9, "B": 10},
    "KR001_POX4": {"R": 7, "G": 8, "B": 25},
    "KR001_POX5": {"R": 13, "G": 6, "B": 5},
    "KR001_SRV1": {"R": 21, "G": 20, "B": 16},
}

COLORS = {
    "AVAILABLE": (0.0, 1.0, 0.0),  # zielony — wolna
    "OCCUPIED":  (1.0, 0.0, 0.5),  # fioletowy — zajęta
    "OPENED":    (0.0, 0.7, 1.0),  # jasnoniebieski — otwarta
    "ERROR":     (1.0, 0.0, 0.0),  # czerwony — błąd
    "SERVICE":   (1.0, 0.0, 0.15), # różowy — serwisowa
    "OFF":       (0.0, 0.0, 0.0),  # wyłączona
}

