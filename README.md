# picometar
Micropython METAR Aviation Weather Checker

This is a small app created for viewing METAR data with a Pi Pico W and a Pimoroni Pico Display.

First go ahead and set up the Pico W and the Pico Display - instructions for that are at the Pimoroni GitHub for the Pico Display.  I used I think their Rainbow Unicorn 1.22 or so for the UFW on the Pico W.  It includes the display libraries used by this code.

Then, just save the two .py files, the pico_version.py one and the wifi_congif.py, to your Pico W using Thonny.  If you want it to run automatically, save the pico_version.py as main.py and it will run at boot and you won't need to have Thonny connected.

Keep in mind that this will save the SSID info (including your password) as a plaintext file on your Pico, so anyone with physical access to your Pico W could read that file easily, so just be careful that it doesn't fall into the wrong hands.

Enjoy, and if you have any questions, requests, or bug reports, hit me up at chris at chrisremboldt dot com.

Please feel free to modify and use as you wish.  License is MIT License.

## M5Stack Cardputer
A version of the script for the M5Stack Cardputer is provided in `cardputer_version.py`. Edit the `WIFI_SSID` and `WIFI_PASS` variables at the top of that file before copying it to your Cardputer. The keyboard uses `/` to select, `,` to go back, `;` for up and `.` for down.
