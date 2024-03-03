import network
import urequests
import time
from picographics import PicoGraphics, DISPLAY_PICO_DISPLAY, PEN_RGB332
from pimoroni import Button
from machine import RTC

import socket
import struct


def ntp_time(host="pool.ntp.org"):
    NTP_PORT = 123
    NTP_PACKET_FORMAT = "!12I"
    NTP_DELTA = 2208988800
    NTP_PACKET_SIZE = 48
    try:
        # Create a UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        addr = socket.getaddrinfo(host, NTP_PORT)[0][-1]
        sock.settimeout(1)

        # Send an NTP packet
        msg = b'\x1b' + 47 * b'\0'
        sock.sendto(msg, addr)

        # Receive the response and validate size
        msg, _ = sock.recvfrom(NTP_PACKET_SIZE)
        if len(msg) == NTP_PACKET_SIZE:
            unpacked = struct.unpack(NTP_PACKET_FORMAT, msg)
            timestamp = unpacked[10] - NTP_DELTA  # Use index 10 for the transmit timestamp
            return timestamp
        else:
            print("Invalid NTP response size.")
            return None
    except Exception as e:
        print(f"Failed to get NTP time: {e}")
        return None
    finally:
        sock.close()


def set_rtc_from_ntp():
    timestamp = ntp_time()
    tm = time.gmtime(timestamp)
    rtc = RTC()
    rtc.datetime((tm[0], tm[1], tm[2], tm[6], tm[3], tm[4], tm[5], 0))

# WiFi details
ssid = 'Murphys Burrow'
password = 'oinkoink'

# Initialize display and buttons
display = PicoGraphics(DISPLAY_PICO_DISPLAY, pen_type=PEN_RGB332, rotate=0)
WIDTH, HEIGHT = display.get_bounds()
BLACK = display.create_pen(0, 0, 0)
WHITE = display.create_pen(255, 255, 255)
button_a = Button(12)
button_b = Button(13)
button_x = Button(14)
button_y = Button(15)

# Predefined list of METAR stations
metar_stations = [
    {"state": "AK", "name": "ADAK NAS", "icao": "PADK"},
    {"state": "AK", "name": "AKHIOK", "icao": "PAKH"},
    {"state": "AK", "name": "AKUTAN", "icao": "PAUT"},
    {"state": "CA", "name": "LOS ANGELES INTL", "icao": "KLAX"},
    {"state": "IL", "name": "CHICAGO O'HARE INTL", "icao": "KORD"},
    {"state": "GA", "name": "HARTSFIELD-JACKSON ATLANTA INTL", "icao": "KATL"},
    {"state": "TN", "name": "NASHVILLE INTL APT", "icao": "KBNA"},

]


# Connect to WiFi
def connect_to_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    while not wlan.isconnected():
        time.sleep(1)
    print('WiFi connected')

# Fetch METAR data for a given station
# Fetch METAR data for a given station
def fetch_metar_data(selected_station):
    # Dynamically construct the URL with the selected station's ICAO code
    url = f'https://w1.weather.gov/data/METAR/{selected_station}.1.txt'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    response = urequests.get(url, headers=headers)
    if response.status_code != 200:
        # Handle HTTP errors or unsuccessful responses
        print(f"Error fetching METAR data for {selected_station}: HTTP {response.status_code}")
        return "Error fetching data"
    metar_data = response.text
    response.close()
    
    # Process the METAR data as before...
    metar_lines = metar_data.strip().split('\n')[3:]  # Skip header lines
    cleaned_metar_data = '\n'.join(metar_lines)  # Combine the remaining lines back into a single string
    
    return cleaned_metar_data


# Function to display METAR data
def display_text(lines, selected_index=None):
    display.set_pen(BLACK)
    display.clear()
    for i, line in enumerate(lines):
        if selected_index is not None and i == selected_index:
            # Highlight the selected line
            display.set_pen(WHITE)  # White for text
            display.text(">" + line, 0, i * 10, WIDTH, 2)
        else:
            # Non-selected lines
            display.set_pen(WHITE)
            display.text(line, 0, i * 10, WIDTH, 2)
    display.update()
    
def display_metar_data(metar_data):
    last_time_update = time.ticks_ms()
    while True:
        # Check if the B button is pressed to return to the menu
        if button_b.read():
            time.sleep(0.2)  # A short delay to debounce the button press
            return  # Exit the loop and return to the main menu

        current_time = time.ticks_ms()
        if time.ticks_diff(current_time, last_time_update) >= 1000:  # Every second
            current_utc = get_current_utc()  # Fetch the current UTC time on each iteration
            display.set_pen(BLACK)
            display.clear()
            display.set_pen(WHITE)
            display.set_font("bitmap8")
            full_text = current_utc + '\n' + metar_data
            display.text(full_text, 0, 0, WIDTH, 2)
            display.update()
            last_time_update = current_time

        time.sleep(0.05)  # A brief sleep to reduce CPU usage without affecting responsiveness



def get_current_utc():
    set_rtc_from_ntp()  # This sets the RTC to the current UTC time
    rtc = RTC()
    datetime = rtc.datetime()
    return "{:02d}/{:02d}/{:04d} {:02d}:{:02d}:{:02d} UTC".format(datetime[1], datetime[2], datetime[0], datetime[4], datetime[5], datetime[6])
# Function for manual airport code entry
def enter_airport():
    characters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    char_index = 0
    airport_code = ["K", "A", "A", "A"]
    position = 0  # Current position being edited

    last_blink_time = time.ticks_ms()
    cursor_visible = True  # Initial cursor state

    while position < 4:
        current_time = time.ticks_ms()
        if current_time - last_blink_time > 500:  # Blink every 500 ms
            cursor_visible = not cursor_visible
            last_blink_time = current_time

        # Display code with blinking cursor
        code_str = ''.join(airport_code)
        cursor_str = code_str[:position] + ('_' if cursor_visible else code_str[position]) + code_str[position + 1:]
        display_text([f"Enter Airport: {cursor_str}"], None)  # None because we're not highlighting

        # Immediate response to button press without waiting for blink delay
        if button_x.read():
            char_index = (char_index - 1) % len(characters)
            airport_code[position] = characters[char_index]
            time.sleep(0.1)  # Short debounce delay
        elif button_y.read():
            char_index = (char_index + 1) % len(characters)
            airport_code[position] = characters[char_index]
            time.sleep(0.1)
        elif button_a.read():
            position += 1
            time.sleep(0.1)

    return ''.join(airport_code)



# Main menu function
def main_menu():
    display.set_font("bitmap8")  # Set to a larger font if available, or adjust accordingly
    options = ["Select Airport", "Enter Airport"]  # Reorder options
    selected_option = 0

    while True:
        display.set_pen(BLACK)
        display.clear()
        # Display the title
        display.set_pen(WHITE)  # Set title color
        display.text("PICO METAR", 10, 0, WIDTH, 4)  # Adjust position and scale as needed

        # Display menu options below the title
        for i, option in enumerate(options):
            y_position = 30 + i * 20  # Adjust starting Y position and gap between options
            if i == selected_option:
                # Highlight the selected option
                display.set_pen(WHITE)  # White for text
                display.text(">" + option, 10, y_position, WIDTH, 3)  # Adjust text size if possible
            else:
                # Non-selected options
                display.set_pen(WHITE)
                display.text(option, 10, y_position, WIDTH, 3)  # Adjust text size if possible
        display.update()

        if button_x.read():  # Move up
            selected_option = (selected_option - 1) % len(options)
            time.sleep(0.3)  # Adjust debounce time if necessary
        elif button_y.read():  # Move down
            selected_option = (selected_option + 1) % len(options)
            time.sleep(0.3)
        elif button_a.read():  # Select
            time.sleep(0.1)  # Adjust debounce time if necessary
            if selected_option == 0:
                return select_station()
            elif selected_option == 1:
                return enter_airport()

# Function to select a station from the list
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
            time.sleep(0.3)
        elif button_y.read():
            selected_station_index = (selected_station_index + 1) % len(metar_stations)
            time.sleep(0.3)
        elif button_a.read():
            return metar_stations[selected_station_index]['icao']
        time.sleep(0.1)


def display_metar(selected_station):
    metar_data = fetch_metar_data(selected_station)
    last_metar_update = time.ticks_ms()  # Track the last update time for METAR data

    while True:
        if button_b.read():
            time.sleep(0.2)  # Debounce delay
            return  # Exit and return to the main menu

        # Check if it's time to refresh METAR data
        current_time = time.ticks_ms()
        if time.ticks_diff(current_time, last_metar_update) >= 120000:  # Every 2 minutes
            metar_data = fetch_metar_data(selected_station)  # Refresh METAR data
            last_metar_update = current_time  # Update the last update time

        display_metar_data(metar_data)  # Display METAR data with real-time UTC

        time.sleep(0.05)  # Short delay for responsiveness




def main():
    connect_to_wifi()
    
    while True:  # Always return to the main menu unless the program is exited
        set_rtc_from_ntp()
        selected_station = main_menu()
        display_metar(selected_station)  # Renamed for clarity


if __name__ == "__main__":
    main()

