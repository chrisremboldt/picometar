# M5Stack Cardputer version of Pico METAR display
# This script displays METAR data using the Cardputer keyboard and ST7789 display.
# WiFi credentials are defined at the top; edit them before running.

from machine import SPI, Pin, RTC
from lib import st7789py, keyboard
import network
import urequests
import socket
import struct
import time

# Replace with your WiFi credentials
WIFI_SSID = 'YOUR_SSID'
WIFI_PASS = 'YOUR_PASSWORD'

# Initialize display (240x135) and keyboard
TFT = st7789py.ST7789(
    SPI(1, baudrate=40_000_000, sck=Pin(36), mosi=Pin(35)),
    135,
    240,
    reset=Pin(33, Pin.OUT),
    cs=Pin(37, Pin.OUT),
    dc=Pin(34, Pin.OUT),
    backlight=Pin(38, Pin.OUT),
    rotation=1,
    color_order=st7789py.BGR,
)
TFT.fill(st7789py.color565(0, 0, 0))
KB = keyboard.KeyBoard()

WHITE = st7789py.color565(255, 255, 255)
BLACK = st7789py.color565(0, 0, 0)
RED = st7789py.color565(255, 0, 0)

# Map Cardputer keys to actions
KEY_UP = ';'
KEY_DOWN = '.'
KEY_BACK = ','
KEY_SELECT = '/'

# Simple WiFi connection
def connect_to_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASS)
    for _ in range(10):
        if wlan.isconnected():
            return True
        time.sleep(1)
    return False

# ----- Time handling using NTP -----
NTP_PORT = 123
NTP_PACKET_FORMAT = "!12I"
NTP_DELTA = 2208988800
NTP_PACKET_SIZE = 48
NTP_SERVERS = [
    "pool.ntp.org",
    "time.google.com",
    "time.cloudflare.com",
    "time.windows.com",
]

def ntp_time():
    for host in NTP_SERVERS:
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            addr = socket.getaddrinfo(host, NTP_PORT)[0][-1]
            sock.settimeout(2)
            msg = b"\x1b" + 47 * b"\0"
            sock.sendto(msg, addr)
            msg, _ = sock.recvfrom(NTP_PACKET_SIZE)
            if len(msg) == NTP_PACKET_SIZE:
                unpacked = struct.unpack(NTP_PACKET_FORMAT, msg)
                return unpacked[10] - NTP_DELTA
        except Exception:
            pass
        finally:
            if sock:
                sock.close()
    return None

def set_rtc_from_ntp():
    timestamp = ntp_time()
    if timestamp is None:
        return False
    tm = time.localtime(timestamp)
    rtc = RTC()
    rtc.datetime((tm[0], tm[1], tm[2], tm[6], tm[3], tm[4], tm[5], 0))
    return True

# ----- Display helpers -----

def display_text(lines, selected_index=None):
    TFT.fill(BLACK)
    for i, line in enumerate(lines):
        prefix = ">" if selected_index is not None and i == selected_index else ""
        TFT.text(font, prefix + line, 0, i * 16, WHITE, BLACK)

# Predefined list of METAR stations
METAR_STATIONS = [
    {"state": "TN", "name": "NASHVILLE INTL APT", "icao": "KBNA"},
    {"state": "CA", "name": "LOS ANGELES INTL", "icao": "KLAX"},
    {"state": "IL", "name": "CHICAGO O'HARE INTL", "icao": "KORD"},
    {"state": "GA", "name": "HARTSFIELD-JACKSON ATLANTA INTL", "icao": "KATL"},
]

# ---- User interface helpers ----

def select_station():
    index = 0
    while True:
        lines = []
        for i, st in enumerate(METAR_STATIONS):
            line = f"{st['state']} {st['name']} {st['icao']}"
            lines.append(line)
        display_text(lines, index)
        keys = KB.get_pressed_keys()
        if KEY_UP in keys:
            index = (index - 1) % len(METAR_STATIONS)
            time.sleep(0.1)
        elif KEY_DOWN in keys:
            index = (index + 1) % len(METAR_STATIONS)
            time.sleep(0.1)
        elif KEY_SELECT in keys:
            return METAR_STATIONS[index]['icao']
        elif KEY_BACK in keys:
            return None
        time.sleep(0.05)

def enter_airport():
    characters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    code = ["K", "A", "A", "A"]
    pos = 0
    char_index = 0
    last_blink = time.ticks_ms()
    cursor_visible = True
    while pos < 4:
        if time.ticks_diff(time.ticks_ms(), last_blink) > 500:
            cursor_visible = not cursor_visible
            last_blink = time.ticks_ms()
        current = ''.join(code)
        cursor = current[:pos] + ('_' if cursor_visible else current[pos]) + current[pos+1:]
        display_text([f"Enter Airport: {cursor}"])
        keys = KB.get_pressed_keys()
        if KEY_UP in keys:
            char_index = (char_index - 1) % len(characters)
            code[pos] = characters[char_index]
            time.sleep(0.1)
        elif KEY_DOWN in keys:
            char_index = (char_index + 1) % len(characters)
            code[pos] = characters[char_index]
            time.sleep(0.1)
        elif KEY_SELECT in keys:
            pos += 1
            char_index = 0
            time.sleep(0.1)
        elif KEY_BACK in keys and pos > 0:
            pos -= 1
            char_index = characters.index(code[pos])
            time.sleep(0.1)
        time.sleep(0.05)
    return ''.join(code)

# ---- METAR retrieval and display ----

def fetch_metar_data(station):
    url = f"https://tgftp.nws.noaa.gov/data/observations/metar/stations/{station}.TXT"
    headers = {"User-Agent": "Cardputer-METAR/1.0", "Accept": "text/plain"}
    try:
        resp = urequests.get(url, headers=headers)
        if resp.status_code == 200:
            data = resp.text.strip().split('\n')
            resp.close()
            return '\n'.join([l for l in data if l])
    except Exception:
        pass
    return None

def get_current_utc():
    rtc = RTC()
    y, m, d, wd, h, mi, s, _ = rtc.datetime()
    return f"{m:02d}/{d:02d}/{y:04d} {h:02d}:{mi:02d}:{s:02d} UTC"

def display_metar(station):
    metar = fetch_metar_data(station)
    last_update = time.ticks_ms()
    while True:
        if time.ticks_diff(time.ticks_ms(), last_update) >= 120000:
            new_data = fetch_metar_data(station)
            if new_data:
                metar = new_data
            last_update = time.ticks_ms()
        TFT.fill(BLACK)
        if metar:
            text = get_current_utc() + '\n' + metar
        else:
            text = "Error fetching METAR"
        y = 0
        for line in text.split('\n'):
            TFT.text(font, line, 0, y, WHITE, BLACK)
            y += 16
        keys = KB.get_pressed_keys()
        if KEY_BACK in keys:
            return
        time.sleep(0.1)

# ---- Main menu ----

def main_menu():
    options = ["Select Airport", "Enter Airport"]
    idx = 0
    while True:
        display_text(options, idx)
        keys = KB.get_pressed_keys()
        if KEY_UP in keys:
            idx = (idx - 1) % len(options)
            time.sleep(0.1)
        elif KEY_DOWN in keys:
            idx = (idx + 1) % len(options)
            time.sleep(0.1)
        elif KEY_SELECT in keys:
            if idx == 0:
                return select_station()
            else:
                return enter_airport()
        time.sleep(0.05)

# ---- Entry point ----

def main():
    if not connect_to_wifi():
        display_text(["WiFi failed"])
        time.sleep(2)
        return
    set_rtc_from_ntp()
    while True:
        station = main_menu()
        if station:
            display_metar(station)

if __name__ == "__main__":
    main()
