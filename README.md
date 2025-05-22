# picometar
Micropython METAR Aviation Weather Checker

This is a small app created for viewing aviation weather with a Pi Pico W and a Pimoroni Pico Display. A top menu lets you pick between METARs, TAFs and other text products from NOAA. Use the **X** and **Y** buttons to scroll through long text products. Long lines are wrapped automatically so information doesn't overlap on the display.

The "ISIGMET" option pulls international SIGMETs from AviationWeather.gov. The
feed is requested using a bounding box over the United States to keep the
download size small. SIGMET pages are separated by dashed lines, and any entry
with an identifier beginning with `K` is shown first. Scroll with **X** and
**Y** to move within a SIGMET and advance to the next or previous report when
reaching the end.

Some of the area weather products on NOAA's server require HTTPS while others only allow plain HTTP. The app now uses whichever protocol works for each feed.

First go ahead and set up the Pico W and the Pico Display - instructions for that are at the Pimoroni GitHub for the Pico Display.  I used I think their Rainbow Unicorn 1.22 or so for the UFW on the Pico W.  It includes the display libraries used by this code.

Then, just save the two .py files, the pico_version.py one and the wifi_congif.py, to your Pico W using Thonny.  If you want it to run automatically, save the pico_version.py as main.py and it will run at boot and you won't need to have Thonny connected.

Keep in mind that this will save the SSID info (including your password) as a plaintext file on your Pico, so anyone with physical access to your Pico W could read that file easily, so just be careful that it doesn't fall into the wrong hands.

Enjoy, and if you have any questions, requests, or bug reports, hit me up at chris at chrisremboldt dot com.

Please feel free to modify and use as you wish.  License is MIT License.

## M5Stack Cardputer
A version of the script for the M5Stack Cardputer is provided in `cardputer_version.py`. Edit the `WIFI_SSID` and `WIFI_PASS` variables at the top of that file before copying it to your Cardputer. The keyboard uses `/` to select, `,` to go back, `;` for up and `.` for down.
