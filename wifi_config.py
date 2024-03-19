import network
import time
from machine import Pin
from pimoroni import Button

# Initialize buttons
button_a = Button(12)
button_b = Button(13)
button_x = Button(14)
button_y = Button(15)

def scan_wifi_networks():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    networks = wlan.scan()
    return [(n[0].decode(), n[3]) for n in networks]

def enter_password(display, BLACK, WHITE, WIDTH):
    characters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()-_=+[]{}|;:,.<>?"
    char_index = 0
    password = []
    position = 0

    while True:
        display.set_pen(BLACK)
        display.clear()

        password_str = ''.join(password)
        display.set_pen(WHITE)
        display.text(f"Enter Password:", 0, 0, WIDTH, 2)

        # Display the entered password
        display.text(password_str, 0, 20, WIDTH, 2)

        # Display the current character being entered (larger font)
        current_char = characters[char_index]
        display.set_font("bitmap14_outline")
        display.text(current_char, (WIDTH - 14) // 2, 40, 14, 2)

        # Display the preceding and following characters (smaller font)
        display.set_font("bitmap8")
        preceding_char = characters[(char_index - 1) % len(characters)]
        following_char = characters[(char_index + 1) % len(characters)]
        display.text(preceding_char, (WIDTH - 14) // 2 - 8, 50, 8, 1)
        display.text(following_char, (WIDTH - 14) // 2 + 14, 50, 8, 1)

        display.update()

        if button_x.read():
            char_index = (char_index - 1) % len(characters)
            time.sleep(0.1)
        elif button_y.read():
            char_index = (char_index + 1) % len(characters)
            time.sleep(0.1)
        elif button_a.read():
            if position < len(password):
                password[position] = current_char
            else:
                password.append(current_char)
            position += 1
            time.sleep(0.1)
        elif button_b.read():
            return ''.join(password)
        
def save_wifi_config(ssid, password):
    with open("wifi_config.txt", "w") as f:
        f.write(f"{ssid}\n{password}")

def load_wifi_config():
    try:
        with open("wifi_config.txt", "r") as f:
            ssid = f.readline().strip()
            password = f.readline().strip()
            return ssid, password
    except:
        return None, None

def connect_to_wifi():
    ssid, password = load_wifi_config()
    if ssid and password:
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        wlan.connect(ssid, password)
        timeout = 10
        while not wlan.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1
        if wlan.isconnected():
            return True
    return False

def display_network_menu(networks, display, BLACK, WHITE, WIDTH):
    selected_network_index = 0
    start_index = 0
    max_networks_per_page = 5
    max_ssid_length = 16

    while True:
        display.set_pen(BLACK)
        display.clear()

        for i in range(start_index, start_index + max_networks_per_page):
            if i >= len(networks):
                break

            network = networks[i]
            ssid = network[0]
            strength = network[1]

            if i == selected_network_index:
                display.set_pen(WHITE)
                if len(ssid) > max_ssid_length:
                    # Truncate the SSID if it's longer than max_ssid_length
                    display.text(f"> {ssid[:max_ssid_length]}...", 0, 10 * (i - start_index), WIDTH - 30, 2)
                else:
                    display.text(f"> {ssid}", 0, 10 * (i - start_index), WIDTH - 30, 2)
                display.text(f"({strength})", WIDTH - 30, 10 * (i - start_index), 30, 2)
            else:
                display.set_pen(WHITE)
                if len(ssid) > max_ssid_length:
                    display.text(f"  {ssid[:max_ssid_length]}...", 0, 10 * (i - start_index), WIDTH - 30, 2)
                else:
                    display.text(f"  {ssid}", 0, 10 * (i - start_index), WIDTH - 30, 2)
                display.text(f"({strength})", WIDTH - 30, 10 * (i - start_index), 30, 2)

        display.update()

        if button_x.read():
            selected_network_index = (selected_network_index - 1) % len(networks)
            if selected_network_index < start_index:
                start_index = max(0, start_index - max_networks_per_page)
            time.sleep(0.1)
        elif button_y.read():
            selected_network_index = (selected_network_index + 1) % len(networks)
            if selected_network_index >= start_index + max_networks_per_page:
                start_index = min(len(networks) - max_networks_per_page, start_index + max_networks_per_page)
            time.sleep(0.1)
        elif button_a.read():
            selected_ssid = networks[selected_network_index][0]
            password = enter_password(display, BLACK, WHITE, WIDTH)
            return selected_ssid, password

def configure_wifi(display, BLACK, WHITE, WIDTH):
    while True:
        networks = scan_wifi_networks()
        ssid, password = display_network_menu(networks, display, BLACK, WHITE, WIDTH)
        save_wifi_config(ssid, password)

        display.set_pen(BLACK)
        display.clear()
        display.set_pen(WHITE)
        display.text("Connecting to network...", 0, 0, WIDTH, 2)
        display.update()

        if connect_to_wifi():
            display.set_pen(BLACK)
            display.clear()
            display.set_pen(WHITE)
            display.text("Connected successfully!", 0, 0, WIDTH, 2)
            display.update()
            time.sleep(2)  # Wait for 2 seconds to show the success message
            return  # Exit the function if the connection is successful
        else:
            display.set_pen(BLACK)
            display.clear()
            display.set_pen(WHITE)
            display.text("Connection failed!", 0, 0, WIDTH, 2)
            display.text("Press A to try again", 0, 20, WIDTH, 2)
            display.text("Press B to select another network", 0, 40, WIDTH, 2)
            display.update()

            while True:
                if button_a.read():
                    time.sleep(0.1)  # Debounce delay
                    break  # Try connecting again with the same network
                elif button_b.read():
                    time.sleep(0.1)  # Debounce delay
                    break  # Go back to network selection menu
