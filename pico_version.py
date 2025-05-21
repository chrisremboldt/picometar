import network
import urequests
import time
from picographics import PicoGraphics, DISPLAY_PICO_DISPLAY, PEN_RGB332
from pimoroni import Button
from machine import RTC
import socket
import struct
import wifi_config

# Initialize display and buttons
display = PicoGraphics(DISPLAY_PICO_DISPLAY, pen_type=PEN_RGB332, rotate=0)
WIDTH, HEIGHT = display.get_bounds()
BLACK = display.create_pen(0, 0, 0)
WHITE = display.create_pen(255, 255, 255)

# Add debouncing to button handling
class DebouncedButton:
    def __init__(self, pin, debounce_ms=100):
        self.button = Button(pin)
        self.debounce_ms = debounce_ms
        self.last_press = 0
        self.last_state = False
        
    def read(self):
        current_time = time.ticks_ms()
        current_state = self.button.read()
        
        # Only trigger on button press (transition from False to True)
        if current_state and not self.last_state:
            if time.ticks_diff(current_time, self.last_press) > self.debounce_ms:
                self.last_press = current_time
                self.last_state = current_state
                return True
        
        self.last_state = current_state
        return False

# Initialize debounced buttons
button_a = DebouncedButton(12, debounce_ms=50)  # Reduced debounce time
button_b = DebouncedButton(13, debounce_ms=50)  # Reduced debounce time
button_x = DebouncedButton(14, debounce_ms=100)
button_y = DebouncedButton(15, debounce_ms=100)

# Add debug print for button presses
def print_button_state():
    if button_a.button.read():
        print("Button A raw state: pressed")
    if button_b.button.read():
        print("Button B raw state: pressed")
    if button_x.button.read():
        print("Button X raw state: pressed")
    if button_y.button.read():
        print("Button Y raw state: pressed")

# Predefined list of METAR stations
metar_stations = [
    {"state": "TN", "name": "NASHVILLE INTL APT", "icao": "KBNA"},
    {"state": "AK", "name": "ADAK NAS", "icao": "PADK"},
    {"state": "AK", "name": "AKHIOK", "icao": "PAKH"},
    {"state": "AK", "name": "AKUTAN", "icao": "PAUT"},
    {"state": "CA", "name": "LOS ANGELES INTL", "icao": "KLAX"},
    {"state": "IL", "name": "CHICAGO O'HARE INTL", "icao": "KORD"},
    {"state": "GA", "name": "HARTSFIELD-JACKSON ATLANTA INTL", "icao": "KATL"},
]

# Supported weather products and their URL patterns.  If a product requires
# a station code in the URL the string contains ``{station}`` as a placeholder.
weather_products = {
    "METAR": {
        "needs_station": True,
        "url": "https://tgftp.nws.noaa.gov/data/observations/metar/stations/{station}.TXT",
    },
    "TAF": {
        "needs_station": True,
        "url": "https://tgftp.nws.noaa.gov/data/forecasts/taf/stations/{station}.TXT",
    },
    # Area products don't require a station
    "AIRMET": {
        "needs_station": False,
        # Use http for area products to avoid HTTPS 403 errors
        "url": "http://tgftp.nws.noaa.gov/data/airmets/airmets.txt",
    },
    "SIGMET": {
        "needs_station": False,
        "url": "http://tgftp.nws.noaa.gov/data/sigmets/sigmets.txt",
    },
    "PIREP": {
        "needs_station": False,
        "url": "http://tgftp.nws.noaa.gov/data/aircraftreports/pireps.txt",
    },
}

def connect_to_wifi():
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            print(f"WiFi connection attempt {attempt + 1}/{max_attempts}")
            if wifi_config.connect_to_wifi():
                print("WiFi connected successfully")
                # Wait a bit for the connection to stabilize
                time.sleep(2)
                return True
            else:
                print("WiFi connection failed, trying configuration")
                wifi_config.configure_wifi(display, BLACK, WHITE, WIDTH)
        except Exception as e:
            print(f"WiFi connection error on attempt {attempt + 1}: {e}")
            display_text([f"WiFi retry {attempt + 1}/{max_attempts}", "Please wait..."])
            time.sleep(2)
    
    display_text(["WiFi connection failed", "Check settings & restart"])
    time.sleep(2)
    return False

def display_text(lines, selected_index=None):
    try:
        display.set_pen(BLACK)
        display.clear()
        for i, line in enumerate(lines):
            if selected_index is not None and i == selected_index:
                display.set_pen(WHITE)
                display.text(">" + line, 0, i * 10, WIDTH, 2)
            else:
                display.set_pen(WHITE)
                display.text(line, 0, i * 10, WIDTH, 2)
        display.update()
    except Exception as e:
        print(f"Display error: {e}")

def ntp_time():
    NTP_PORT = 123
    NTP_PACKET_FORMAT = "!12I"
    NTP_DELTA = 2208988800
    NTP_PACKET_SIZE = 48
    
    # List of NTP servers to try
    ntp_servers = [
        "pool.ntp.org",
        "time.google.com",
        "time.cloudflare.com",
        "time.windows.com"
    ]
    
    for host in ntp_servers:
        sock = None
        try:
            print(f"Trying NTP server: {host}")
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            addr = socket.getaddrinfo(host, NTP_PORT)[0][-1]
            sock.settimeout(2)  # Increased timeout

            msg = b'\x1b' + 47 * b'\0'
            sock.sendto(msg, addr)

            msg, _ = sock.recvfrom(NTP_PACKET_SIZE)
            if len(msg) == NTP_PACKET_SIZE:
                unpacked = struct.unpack(NTP_PACKET_FORMAT, msg)
                timestamp = unpacked[10] - NTP_DELTA
                print(f"NTP time successfully retrieved from {host}")
                return timestamp
        except Exception as e:
            print(f"NTP error with {host}: {e}")
        finally:
            if sock:
                sock.close()
    
    print("All NTP servers failed")
    return None

def set_rtc_from_ntp():
    try:
        timestamp = ntp_time()
        if timestamp is not None and timestamp > 0:
            tm = time.localtime(timestamp)
            rtc = RTC()
            rtc.datetime((tm[0], tm[1], tm[2], tm[6], tm[3], tm[4], tm[5], 0))
            return True
    except Exception as e:
        print(f"RTC update error: {e}")
    return False

def get_current_utc():
    try:
        rtc = RTC()
        datetime = rtc.datetime()
        return "{:02d}/{:02d}/{:04d} {:02d}:{:02d}:{:02d} UTC".format(
            datetime[1], datetime[2], datetime[0], 
            datetime[4], datetime[5], datetime[6]
        )
    except Exception as e:
        print(f"UTC time error: {e}")
        return "Time unavailable"

def product_menu():
    """Allow the user to choose which weather product to view."""
    options = list(weather_products.keys())
    selected = 0
    display.set_font("bitmap8")
    last_update = time.ticks_ms()

    while True:
        current_time = time.ticks_ms()
        if time.ticks_diff(current_time, last_update) >= 100:
            display.set_pen(BLACK)
            display.clear()
            display.set_pen(WHITE)
            display.text("Select Product", 10, 0, WIDTH, 3)
            for i, opt in enumerate(options):
                y = 20 + i * 20
                text = ">" + opt if i == selected else opt
                display.text(text, 10, y, WIDTH, 3)
            display.update()
            last_update = current_time

        if button_x.read():
            selected = (selected - 1) % len(options)
        elif button_y.read():
            selected = (selected + 1) % len(options)
        elif button_a.read():
            return options[selected]
        time.sleep(0.1)

def station_menu():
    display.set_font("bitmap8")
    options = ["Select Airport", "Enter Airport"]
    selected_option = 0
    last_update = time.ticks_ms()
    last_debug = time.ticks_ms()

    while True:
        try:
            current_time = time.ticks_ms()
            
            # Debug button states every second
            if time.ticks_diff(current_time, last_debug) >= 1000:
                print_button_state()
                last_debug = current_time
            
            # Update display every 100ms
            if time.ticks_diff(current_time, last_update) >= 100:
                display.set_pen(BLACK)
                display.clear()
                display.set_pen(WHITE)
                display.text("PICO METAR", 10, 0, WIDTH, 4)

                for i, option in enumerate(options):
                    y_position = 30 + i * 20
                    display.set_pen(WHITE)
                    if i == selected_option:
                        display.text(">" + option, 10, y_position, WIDTH, 3)
                    else:
                        display.text(option, 10, y_position, WIDTH, 3)
                display.update()
                last_update = current_time

            if button_x.read():
                selected_option = (selected_option - 1) % len(options)
            elif button_y.read():
                selected_option = (selected_option + 1) % len(options)
            elif button_a.read():
                return select_station() if selected_option == 0 else enter_airport()

            time.sleep(0.01)  # Short sleep to prevent tight loop
            
        except Exception as e:
            print(f"Menu error: {e}")
            time.sleep(1)  # Pause before retrying

def select_station():
    selected_station_index = 0

    while True:
        display.set_pen(BLACK)
        display.clear()
        
        for i in range(len(metar_stations)):
            station = metar_stations[i]
            city_name = station['name'][:16]  # Truncate city name if longer than 16 characters
            text_line = f"{station['state']} {city_name} {station['icao']}"

            if i == selected_station_index:
                # Highlight the selected station
                display.set_pen(WHITE)
                display.text(">" + text_line, 0, 10 * i, WIDTH, 1)
            else:
                display.set_pen(WHITE)
                display.text(text_line, 0, 10 * i, WIDTH, 1)

        display.update()

        if button_x.read():
            selected_station_index = (selected_station_index - 1) % len(metar_stations)
        elif button_y.read():
            selected_station_index = (selected_station_index + 1) % len(metar_stations)
        elif button_a.read():
            return metar_stations[selected_station_index]['icao']
            
        time.sleep(0.1)

def enter_airport():
    characters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    char_index = 0
    airport_code = ["K", "A", "A", "A"]
    position = 0  # Current position being edited

    last_blink_time = time.ticks_ms()
    cursor_visible = True  # Initial cursor state

    while position < 4:
        current_time = time.ticks_ms()
        if time.ticks_diff(current_time, last_blink_time) > 500:  # Blink every 500 ms
            cursor_visible = not cursor_visible
            last_blink_time = current_time

        # Display code with blinking cursor
        code_str = ''.join(airport_code)
        cursor_str = code_str[:position] + ('_' if cursor_visible else code_str[position]) + code_str[position + 1:]
        display_text([f"Enter Airport: {cursor_str}"], None)

        if button_x.read():
            char_index = (char_index - 1) % len(characters)
            airport_code[position] = characters[char_index]
        elif button_y.read():
            char_index = (char_index + 1) % len(characters)
            airport_code[position] = characters[char_index]
        elif button_a.read():
            position += 1
            char_index = 0  # Reset character index for next position

        time.sleep(0.1)

    return ''.join(airport_code)

def fetch_weather_data(product, station=None, max_retries=3):
    """Fetch text data for the given weather product."""
    info = weather_products.get(product)
    if not info:
        return None
    url = info["url"].format(station=station or "")
    for attempt in range(max_retries):
        print(f"Fetching {product} (attempt {attempt + 1}/{max_retries})")
        try:
            headers = {
                'User-Agent': 'Pico-METAR-Display/1.0',
                'Accept': 'text/plain'
            }
            print(f"Trying URL: {url}")
            response = urequests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.text
                response.close()
                lines = [line for line in data.strip().split('\n') if line.strip()]
                cleaned = '\n'.join(lines)
                print("Successfully fetched data:", cleaned)
                return cleaned
            else:
                print(f"HTTP error {response.status_code}")
                response.close()
        except Exception as e:
            print(f"Error fetching {product}: {e}")
            time.sleep(1)
    print(f"All attempts to fetch {product} failed")
    return None

def display_weather(product, station=None):
    data = fetch_weather_data(product, station)
    last_update = time.ticks_ms()
    last_ntp_update = time.ticks_ms()

    scroll_offset = 0
    line_height = 10
    lines_per_page = HEIGHT // line_height

    while True:
        current_time = time.ticks_ms()

        # Refresh data every 2 minutes
        if time.ticks_diff(current_time, last_update) >= 120000:
            new_data = fetch_weather_data(product, station)
            if new_data:
                data = new_data
                scroll_offset = 0  # Reset scroll after refresh
            last_update = current_time

        # Update NTP time every 2 minutes
        if time.ticks_diff(current_time, last_ntp_update) >= 120000:
            set_rtc_from_ntp()
            last_ntp_update = current_time

        # Prepare lines to display
        current_utc = get_current_utc()
        display_lines = []
        if data:
            display_lines = (current_utc + '\n' + data).split('\n')
        else:
            display_lines = [f"Error fetching {product}"]

        # Bound scroll offset
        max_offset = max(0, len(display_lines) - lines_per_page)
        if scroll_offset > max_offset:
            scroll_offset = max_offset

        # Draw the visible portion of text
        display.set_pen(BLACK)
        display.clear()
        display.set_pen(WHITE)
        display.set_font("bitmap8")
        for i in range(lines_per_page):
            idx = i + scroll_offset
            if idx >= len(display_lines):
                break
            display.text(display_lines[idx], 0, i * line_height, WIDTH, 2)
        display.update()

        if button_x.read():
            scroll_offset = max(0, scroll_offset - 1)
        elif button_y.read():
            scroll_offset = min(max_offset, scroll_offset + 1)
        elif button_b.read():
            break

        time.sleep(0.1)

def main():
    while True:
        try:
            connect_to_wifi()
            if set_rtc_from_ntp():
                product = product_menu()
                station = None
                if weather_products.get(product, {}).get("needs_station"):
                    station = station_menu()
                display_weather(product, station)
            else:
                display_text(["Error: Could not set time", "Press any button"])
                while not any([button_a.read(), button_b.read(), button_x.read(), button_y.read()]):
                    time.sleep(0.1)
        except Exception as e:
            print(f"Main loop error: {e}")
            display_text(["Error occurred", "Restarting..."])
            time.sleep(2)

if __name__ == "__main__":
    main()
