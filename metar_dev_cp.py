from machine import SPI, Pin, RTC
from lib import st7789py, keyboard
import time
import network
import urequests
import gc
from font import vga1_8x16 as font





# WiFi details
ssid = 'Murphys Burrow'
password = 'oinkoink'

# Display initialization with st7789py
tft = st7789py.ST7789(
    SPI(1, baudrate=40000000, sck=Pin(36), mosi=Pin(35)),
    135,
    240,
    reset=Pin(33, Pin.OUT),
    cs=Pin(37, Pin.OUT),
    dc=Pin(34, Pin.OUT),
    backlight=Pin(38, Pin.OUT),
    rotation=1,
    color_order=st7789py.BGR
)

# Initialize keyboard
kb = keyboard.KeyBoard()

def check_buttons():
    pressed_keys = kb.get_new_keys()  # Get list of newly pressed keys
    
    # Using '/' as 'A'
    if '/' in pressed_keys:
        # Handle button A action (e.g., advance, select)
        print("Button A ('/') pressed")

    # Using ',' as 'B'
    elif ',' in pressed_keys:
        # Handle button B action (e.g., back, cancel)
        print("Button B (',') pressed")
    
    # Using ';' as 'X'
    if ';' in pressed_keys:
        # Handle button X action (e.g., left, decrease)
        print("Button X (';') pressed")
    
    # Using '.' as 'Y'
    if '.' in pressed_keys:
        # Handle button Y action (e.g., right, increase)
        print("Button Y ('.') pressed")



# Global color definitions
WHITE = st7789py.color565(255, 255, 255)
BLACK = st7789py.color565(0, 0, 0)
RED = st7789py.color565(255, 0, 0)

# Predefined list of METAR stations
metar_stations = [
    {"state": "AZ", "name": "Phoenix Sky Harbor International Airport", "icao": "KPHX"},
    {"state": "CA", "name": "Los Angeles International Airport", "icao": "KLAX"},
    {"state": "CA", "name": "John Wayne Airport", "icao": "KSNA"},
    {"state": "CA", "name": "Oakland International Airport", "icao": "KOAK"},
    {"state": "CA", "name": "Sacramento International Airport", "icao": "KSMF"},
    {"state": "CA", "name": "San Diego International Airport", "icao": "KSAN"},
    {"state": "CA", "name": "San Francisco International Airport", "icao": "KSFO"},
    {"state": "CA", "name": "San Jose International Airport", "icao": "KSJC"},
    {"state": "CO", "name": "Denver International Airport", "icao": "KDEN"},
    {"state": "FL", "name": "Fort Lauderdale-Hollywood International Airport", "icao": "KFLL"},
    {"state": "FL", "name": "Jacksonville International Airport", "icao": "KJAX"},
    {"state": "FL", "name": "Miami International Airport", "icao": "KMIA"},
    {"state": "FL", "name": "Orlando International Airport", "icao": "KMCO"},
    {"state": "FL", "name": "Palm Beach International Airport", "icao": "KPBI"},
    {"state": "FL", "name": "Southwest Florida International Airport", "icao": "KRSW"},
    {"state": "FL", "name": "Tampa International Airport", "icao": "KTPA"},
    {"state": "GA", "name": "Hartsfield-Jackson Atlanta International Airport", "icao": "KATL"},
    {"state": "HI", "name": "Honolulu International Airport", "icao": "PHNL"},
    {"state": "IL", "name": "Chicago O'Hare International Airport", "icao": "KORD"},
    {"state": "IL", "name": "Chicago Midway International Airport", "icao": "KMDW"},
    {"state": "IN", "name": "Indianapolis International Airport", "icao": "KIND"},
    {"state": "KY", "name": "Cincinnati/Northern Kentucky International Airport", "icao": "KCVG"},
    {"state": "MA", "name": "Boston Logan International Airport", "icao": "KBOS"},
    {"state": "MD", "name": "Baltimore/Washington International Thurgood Marshall Airport", "icao": "KBWI"},
    {"state": "MI", "name": "Detroit Metropolitan Wayne County Airport", "icao": "KDTW"},
    {"state": "MN", "name": "Minneapolis-St. Paul International Airport", "icao": "KMSP"},
    {"state": "MO", "name": "Kansas City International Airport", "icao": "KMCI"},
    {"state": "MO", "name": "Saint Louis Lambert International Airport", "icao": "KSTL"},
    {"state": "NC", "name": "Charlotte Douglas International Airport", "icao": "KCLT"},
    {"state": "NC", "name": "Raleigh-Durham International Airport", "icao": "KRDU"},
    {"state": "NJ", "name": "Newark Liberty International Airport", "icao": "KEWR"},
    {"state": "NV", "name": "McCarran International Airport", "icao": "KLAS"},
    {"state": "NY", "name": "John F. Kennedy International Airport", "icao": "KJFK"},
    {"state": "NY", "name": "LaGuardia Airport", "icao": "KLGA"},
    {"state": "OH", "name": "Cleveland Hopkins International Airport", "icao": "KCLE"},
    {"state": "OR", "name": "Portland International Airport", "icao": "KPDX"},
    {"state": "PA", "name": "Philadelphia International Airport", "icao": "KPHL"},
    {"state": "PA", "name": "Pittsburgh International Airport", "icao": "KPIT"},
    {"state": "TX", "name": "Austin-Bergstrom International Airport", "icao": "KAUS"},
    {"state": "TX", "name": "Dallas/Fort Worth International Airport", "icao": "KDFW"},
    {"state": "TX", "name": "Houston George Bush Intercontinental Airport", "icao": "KIAH"},
    {"state": "TX", "name": "San Antonio International Airport", "icao": "KSAT"},
    {"state": "UT", "name": "Salt Lake City International Airport", "icao": "KSLC"},
    {"state": "VA", "name": "Ronald Reagan Washington National Airport", "icao": "KDCA"},
    {"state": "VA", "name": "Washington Dulles International Airport", "icao": "KIAD"},
    {"state": "WA", "name": "Seattle-Tacoma International Airport", "icao": "KSEA"},
    {"state": "WI", "name": "Milwaukee Mitchell International Airport", "icao": "KMKE"},
    {"state": "NM", "name": "Albuquerque International Sunport", "icao": "KABQ"}
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
# Global color definitions for easy reference
RED = st7789py.color565(255, 0, 0)
# WHITE and BLACK are already defined

def display_text(lines, selected_index=None, font_size=16):
    tft.fill(BLACK)
    y_offset = 0

    # Get current local time from the RTC
    rtc = RTC()
    _, _, _, _, hours, _, _, _ = rtc.datetime()

    # Determine if the current time is between 1800 and 0600
    if 17 <= hours or hours < 6:
        text_color = RED
    else:
        text_color = WHITE

    for i, line in enumerate(lines):
        if selected_index is not None and i == selected_index:
            # Highlight selected line if applicable
            tft.text(font, ">" + line, 0, y_offset, text_color, BLACK)
        else:
            tft.text(font, line, 0, y_offset, text_color, BLACK)
        y_offset += font_size

    
def display_metar_data(metar_data):
    current_utc = get_current_utc()
    full_text = current_utc + '\n' + metar_data
    
    # Extract the hour from the current UTC time
    # Assuming current_utc format is "mm/dd/yyyy hh:mm:ss UTC"
    hour = int(current_utc.split()[1].split(':')[0])
    
    # Determine text color based on the hour
    if 18 <= hour or hour < 6:
        # Use red color for the text between 1800 and 0600
        text_color = st7789py.color565(255, 0, 0)  # RED
    else:
        # Use white color for the text outside these hours
        text_color = st7789py.color565(255, 255, 255)  # WHITE

    background_color = st7789py.color565(0, 0, 0)  # BLACK

    # Calculate maximum characters per line
    max_chars_per_line = tft.width // 8  # Assuming 8 pixels per character width
    
    wrapped_text = wrap_text(full_text, 8, tft.width)
    
    x0, y0 = 0, 0
    
    for line in wrapped_text:
        tft.text(font, line, x0, y0, text_color, background_color)
        y0 += 18

        
# Display METAR data using st7789py
def wrap_text(text, char_width, max_width):
    words = text.split(' ')
    lines = []
    current_line = ''

    for word in words:
        # Check if adding the next word exceeds the line length
        if len(current_line) + len(word) + 1 > max_width // char_width:
            lines.append(current_line)
            current_line = word
        else:
            if current_line:
                # Add a space before the word if it's not the beginning of a line
                current_line += ' '
            current_line += word
    lines.append(current_line)  # Add the last line
    
    return lines


# Get current UTC date and time
def get_current_utc():
    rtc = RTC()
    year, month, day, weekday, hours, minutes, seconds, subseconds = rtc.datetime()
    
    # Central Standard Time (CST) offset from UTC is -6 hours
    # The RTC stores UTC time, so subtract 6 hours to convert
    utc_offset_hours = -6
    
    # Adjust hours for UTC
    hours += utc_offset_hours
    
    # Handle overflow
    if hours < 0:
        hours += 24
        day -= 1
    elif hours >= 24:
        hours -= 24
        day += 1
    
    # Adjust days for month overflow and underflow
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    
    # Check for leap year
    if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
        days_in_month[1] = 29
    
    # Handle day underflow
    if day < 1:
        month -= 1
        if month < 1:
            month = 12
            year -= 1
        day = days_in_month[month - 1]
    
    # Handle day overflow
    elif day > days_in_month[month - 1]:
        day = 1
        month += 1
        if month > 12:
            month = 1
            year += 1
            
    return "{:02d}/{:02d}/{:04d} {:02d}:{:02d}:{:02d} UTC ".format(month, day, year, hours, minutes, seconds)

# Function for manual airport code entry
def enter_airport(kb):
    characters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    airport_code = ["K", "A", "A", "A"]  # Initial code, with "K" now editable
    position = 0  # Start editing from the first character

    # Initialize char_index to match the first character in the airport_code
    char_index = characters.index(airport_code[position])

    last_blink_time = time.ticks_ms()
    cursor_visible = True
    previous_cursor_str = ""

    # Clear the screen initially
    tft.fill(BLACK)

    while position < 4:
        current_time = time.ticks_ms()
        if current_time - last_blink_time > 500:  # Blink cursor
            cursor_visible = not cursor_visible
            last_blink_time = current_time

        # Display code with blinking cursor
        code_str = ''.join(airport_code)
        cursor_str = code_str[:position] + ('_' if cursor_visible else code_str[position]) + code_str[position + 1:]

        if cursor_str != previous_cursor_str:
            display_text([f"Enter Airport: {cursor_str}"], None)
            previous_cursor_str = cursor_str

        pressed_keys = kb.get_pressed_keys()

        # Update char_index and modify character at the current position
        if ';' in pressed_keys:  # Move left in characters array
            char_index = (char_index - 1) % len(characters)
            time.sleep(0.1)
        elif '.' in pressed_keys:  # Move right in characters array
            char_index = (char_index + 1) % len(characters)
            time.sleep(0.1)
            # Update the character at the current position to the new character
        airport_code[position] = characters[char_index]
            

        if ',' in pressed_keys and position > 0:  # Go back to the previous character
            position -= 1
            char_index = characters.index(airport_code[position])  # Update char_index for the new position
            time.sleep(0.1)
        elif '/' in pressed_keys:  # Advance to the next character
            position += 1
            time.sleep(0.1)
            if position < 4:  # Prevent index error and prepare char_index for the next character
                char_index = characters.index(airport_code[position])

        time.sleep(0.1)  # Short delay for button debounce

    return ''.join(airport_code)



# Main menu function
def main_menu(kb):
    options = ["Select Airport", "Enter Airport"]
    selected_option = 0
    
    # Determine the current UTC hour to decide on the text color
    current_utc = get_current_utc()
    hour = int(current_utc.split()[1].split(':')[0])
    if 18 <= hour or hour < 6:
        text_color = st7789py.color565(255, 0, 0)  # RED for 1800-0600 hours
    else:
        text_color = st7789py.color565(255, 255, 255)  # WHITE for other times

    background_color = st7789py.color565(0, 0, 0)  # Always BLACK background

    tft.fill(background_color)  # Clear screen with the background color

    while True:
        for i, option in enumerate(options):
            y_position = 30 + i * 20
            if i == selected_option:
                # Highlight the selected option with a ">" prefix
                tft.text(font, ">" + option, 10, y_position, text_color, background_color)
            else:
                tft.text(font, option, 10, y_position, text_color, background_color)

        pressed_keys = kb.get_pressed_keys()

        if ';' in pressed_keys:  # Use ';' for 'X' (up)
            selected_option = (selected_option - 1) % len(options)
            time.sleep(0.3)
        elif '.' in pressed_keys:  # Use '.' for 'Y' (down)
            selected_option = (selected_option + 1) % len(options)
            time.sleep(0.3)
        elif '/' in pressed_keys:  # Use '/' for 'A' (select)
            if selected_option == 0:
                return select_station(kb)
            elif selected_option == 1:
                return enter_airport(kb)
            time.sleep(0.1)


            
# Function to select a station from the list
def select_station(kb):
    selected_station_index = 0
    
    # Determine the current UTC hour to decide on the text color
    current_utc = get_current_utc()
    hour = int(current_utc.split()[1].split(':')[0])
    if 18 <= hour or hour < 6:
        text_color = st7789py.color565(255, 0, 0)  # RED for 1800-0600 hours
    else:
        text_color = st7789py.color565(255, 255, 255)  # WHITE for other times

    background_color = st7789py.color565(0, 0, 0)  # Always BLACK background

    tft.fill(background_color)  # Clear screen with the background color
    time.sleep(0.2)  # Debounce delay

    while True:
        for i, station in enumerate(metar_stations):
            y_position = i * 20
            text_line = f"{station['state']} {station['name']} {station['icao']}"
            if i == selected_station_index:
                tft.text(font, ">" + text_line, 0, y_position, text_color, background_color)
            else:
                tft.text(font, text_line, 0, y_position, text_color, background_color)

        pressed_keys = kb.get_pressed_keys()

        if ';' in pressed_keys:  # Use ';' for 'X' (previous station)
            selected_station_index = (selected_station_index - 1) % len(metar_stations)
            time.sleep(0.1)  # Debounce delay
        elif '.' in pressed_keys:  # Use '.' for 'Y' (next station)
            time.sleep(0.1)  # Debounce delay
            selected_station_index = (selected_station_index + 1) % len(metar_stations)
        if ',' in pressed_keys:
            time.sleep(0.1)  # Debounce delay
            return  # Exit and return to the main menu
        elif '/' in pressed_keys:  # Use '/' for 'A' (select station)
            return metar_stations[selected_station_index]['icao']
        time.sleep(0.1)




def display_metar(selected_station, kb):
    # Fetch initial METAR data before entering the loop
    metar_data = fetch_metar_data(selected_station)
    last_refresh_time = time.time()
    refresh_interval = 120  # 120 seconds or 2 minutes
    tft.fill(BLACK)


    while True:
        pressed_keys = kb.get_pressed_keys()  # Get current pressed keys

        if ',' in pressed_keys:
            time.sleep(0.2)  # Debounce delay
            return  # Exit and return to the main menu

        current_time = time.time()
        if current_time - last_refresh_time > refresh_interval:
            # Refresh METAR data
            metar_data = fetch_metar_data(selected_station)
            last_refresh_time = current_time  # Reset refresh timer

        current_utc = get_current_utc()  # Fetch the current UTC time before calling the display function
        display_metar_data(metar_data)  # Display the METAR data

        time.sleep(0.05)  # Short delay for responsiveness


def main():
    connect_to_wifi()
    while True:  # Always return to the main menu unless the program is exited
        selected_station = main_menu(kb)
        if selected_station is None:  # User wants to return to the main menu
            continue  # Just continue the loop to show the main menu again
        display_metar(selected_station, kb)  # Proceed with displaying METAR data



if __name__ == "__main__":
    main()
