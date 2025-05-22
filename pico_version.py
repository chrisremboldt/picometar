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
        "url": "http://tgftp.nws.noaa.gov/data/observations/metar/stations/{station}.TXT",
    },
    "TAF": {
        "needs_station": True,
        "url": "http://tgftp.nws.noaa.gov/data/forecasts/taf/stations/{station}.TXT",
    },
    "AIRMET": {
        "needs_station": False,
        "url": "https://aviationweather.gov/api/data/gairmet?format=raw",
    },
    "SIGMET": {
        "needs_station": False,
        "url": "https://aviationweather.gov/api/data/airsigmet?format=raw",
    },
    "PIREP": {
        "needs_station": False,
        "url": "https://aviationweather.gov/api/data/pirep?format=raw",
    },
    "ISIGMET": {
        "needs_station": False,
        "url": "https://aviationweather.gov/api/data/isigmet?format=raw",
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

def wrap_text(text, char_width, max_width):
    """Word-wrap text for a fixed-width font."""
    words = text.split(" ")
    lines = []
    current = ""
    for word in words:
        if len(current) + len(word) + (1 if current else 0) > max_width // char_width:
            lines.append(current)
            current = word
        else:
            if current:
                current += " "
            current += word
    lines.append(current)
    return lines

def parse_isigmet(raw_text):
    """Split ISIGMET data into pages and reorder US pages first."""
    import re

    pages = [p.strip() for p in raw_text.split("----------------------") if p.strip()]

    def has_us_identifier(text):
        return re.search(r"\bK[A-Z]{3}\b", text) is not None

    us_pages = [p for p in pages if has_us_identifier(p)]
    other_pages = [p for p in pages if not has_us_identifier(p)]
    ordered_pages = us_pages + other_pages

    # Split each page into wrapped lines
    wrapped_pages = []
    for page in ordered_pages:
        lines = []
        for raw in page.split("\n"):
            lines.extend(wrap_text(raw, CHAR_WIDTH * TEXT_SCALE, WIDTH))
        wrapped_pages.append(lines)
    return wrapped_pages

def fetch_large_data_stream(url, max_size=8192, chunk_size=1024):
    """Generic function to fetch large weather data with memory management."""
    try:
        headers = {
            'User-Agent': 'Pico-METAR-Display/1.0',
            'Accept': 'text/plain'
        }
        print(f"Trying URL: {url}")
        
        response = urequests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"HTTP error {response.status_code}")
            response.close()
            return None

        # Read content in smaller chunks to avoid memory allocation issues
        content_parts = []
        total_size = 0
        
        try:
            while True:
                chunk = response.raw.read(chunk_size)
                if not chunk:
                    break
                
                total_size += len(chunk)
                if total_size > max_size:
                    print(f"Response too large ({total_size} bytes), truncating at {max_size}")
                    break
                    
                content_parts.append(chunk.decode('utf-8'))
                
        except MemoryError:
            print("Memory error during read, using partial data")
        
        response.close()
        
        # Join the parts
        result = ''.join(content_parts).strip()
        print(f"Fetched data: {len(result)} characters")
        return result
        
    except MemoryError:
        print("Memory allocation failed")
        return ""  # Return empty string instead of None
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def fetch_pirep_stream(url):
    """Fetch PIREP data with memory optimization and filtering."""
    try:
        # Add parameters to limit response size
        # Get only recent PIREPs (last 2 hours) to reduce data volume
        limited_url = f"{url}&age=2"
        
        return fetch_large_data_stream(limited_url, max_size=6144, chunk_size=512)
        
    except Exception as e:
        print(f"Error fetching PIREP: {e}")
        return None

def fetch_sigmet_stream(url):
    """Fetch SIGMET data with memory optimization."""
    try:
        # SIGMETs are usually smaller but can still cause issues
        return fetch_large_data_stream(url, max_size=8192, chunk_size=1024)
        
    except Exception as e:
        print(f"Error fetching SIGMET: {e}")
        return None

def fetch_isigmet_stream(url):
    """Fetch ISIGMET data with memory optimization."""
    try:
        # Add parameters to limit response size
        # Filter by hazard type to reduce data volume
        limited_url = f"{url}&hazard=turb"  # Only turbulence SIGMETs
        
        return fetch_large_data_stream(limited_url, max_size=8192, chunk_size=1024)
        
    except Exception as e:
        print(f"Error fetching ISIGMET: {e}")
        return None

def fetch_weather_data(product, station=None, max_retries=3):
    """Fetch text data for the given weather product with memory management."""
    info = weather_products.get(product)
    if not info:
        return None
    url = info["url"].format(station=station or "")
    
    for attempt in range(max_retries):
        print(f"Fetching {product} (attempt {attempt + 1}/{max_retries})")
        try:
            # Use specialized fetchers for large data products
            if product == "PIREP":
                data = fetch_pirep_stream(url)
            elif product == "SIGMET":
                data = fetch_sigmet_stream(url)
            elif product == "ISIGMET":
                data = fetch_isigmet_stream(url)
            else:
                # Regular handling for METAR, TAF, AIRMET
                headers = {
                    'User-Agent': 'Pico-METAR-Display/1.0',
                    'Accept': 'text/plain'
                }
                print(f"Trying URL: {url}")
                response = urequests.get(url, headers=headers)
                if response.status_code == 200:
                    data = response.text
                    response.close()
                    
                    # Clean up the data
                    lines = [line for line in data.strip().split('\n') if line.strip()]
                    cleaned = '\n'.join(lines)
                    print("Successfully fetched data:", cleaned[:200] + "..." if len(cleaned) > 200 else cleaned)
                    return cleaned
                else:
                    print(f"HTTP error {response.status_code}")
                    response.close()
                    continue
            
            # Handle the streamed data response
            if data is not None:  # Allow empty string but not None
                if data == "":
                    return "No current data available"
                # Clean up the data
                lines = [line for line in data.strip().split('\n') if line.strip()]
                cleaned = '\n'.join(lines)
                return cleaned
            else:
                raise Exception(f"Failed to fetch {product}")
                
        except Exception as e:
            print(f"Error fetching {product}: {e}")
            time.sleep(1)
    
    print(f"All attempts to fetch {product} failed")
    return None

# Text rendering configuration
TEXT_SCALE = 2
LINE_HEIGHT = 16  # bitmap8 at scale 2 is ~16px tall
CHAR_WIDTH = 5    # Approximate average character width in pixels

def display_weather(product, station=None):
    data = fetch_weather_data(product, station)
    last_update = time.ticks_ms()
    last_ntp_update = time.ticks_ms()
    scroll = 0
    page_index = 0
    pages = None

    while True:
        current_time = time.ticks_ms()

        # Refresh data every 2 minutes
        if time.ticks_diff(current_time, last_update) >= 120000:
            new_data = fetch_weather_data(product, station)
            if new_data:
                data = new_data
            last_update = current_time

        # Update NTP time every 2 minutes
        if time.ticks_diff(current_time, last_ntp_update) >= 120000:
            set_rtc_from_ntp()
            last_ntp_update = current_time

        current_utc = get_current_utc()
        display.set_pen(BLACK)
        display.clear()
        display.set_pen(WHITE)
        display.set_font("bitmap8")

        if product == "ISIGMET" and data is not None:
            if data.strip() == "":
                lines = ["No active ISIGMETs"]
            else:
                if pages is None:
                    pages = parse_isigmet(data)
                if page_index >= len(pages):
                    page_index = len(pages) - 1
                lines = pages[page_index]
        else:
            if data:
                full_text = current_utc + '\n' + data
            else:
                full_text = f"Error fetching {product}"
            lines = []
            for raw in full_text.split('\n'):
                lines.extend(wrap_text(raw, CHAR_WIDTH * TEXT_SCALE, WIDTH))

        line_height = LINE_HEIGHT
        lines_per_screen = HEIGHT // line_height
        scroll = min(max(scroll, 0), max(0, len(lines) - lines_per_screen))

        for i in range(lines_per_screen):
            line_index = scroll + i
            if line_index >= len(lines):
                break
            display.text(lines[line_index], 0, i * line_height, WIDTH, TEXT_SCALE)

        display.update()

        if button_x.read():
            if scroll > 0:
                scroll = max(0, scroll - 1)
            elif product == "ISIGMET" and pages and page_index > 0:
                page_index -= 1
                scroll = 0
        elif button_y.read():
            if scroll + lines_per_screen < len(lines):
                scroll += 1
            else:
                if product == "ISIGMET" and pages and page_index + 1 < len(pages):
                    page_index += 1
                    scroll = 0
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
