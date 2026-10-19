# SPDX-FileCopyrightText: Copyright (c) 2025 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Full library testing example for the Adafruit AS5600 CircuitPython library

This example tests all functionality of the AS5600 magnetic angle sensor
"""

import os
import time
import board
import busio
import wifi
import displayio
import terminalio
import digitalio
from digitalio import DigitalInOut

from adafruit_esp32spi import adafruit_esp32spi
import adafruit_connection_manager
import adafruit_minimqtt.adafruit_minimqtt as mqtt


import adafruit_as5600
from adafruit_display_text import label

# Initialize the board
# spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
# esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)


# Initialize buttons
button1 = DigitalInOut(board.D0)
button1.switch_to_input(pull=digitalio.Pull.UP)
button2 = DigitalInOut(board.D1)
button2.switch_to_input()
button3 = DigitalInOut(board.D2)
button3.switch_to_input()


# Initialize I2C and AS5600
i2c = board.I2C()  # uses board.SCL and board.SDA

# I2C 0x36, shared with battery monitor and neither can be changed
# bms = adafruit_max1704x.MAX17048(i2c)
as5600 = adafruit_as5600.AS5600(i2c)

# Setup the display
BORDER = 20
FONTSCALE = 2
TEXT_COLOR_LINE1 = 0xFFFF00
COLOR_RED = 0xFF0000
COLOR_GREEN = 0x00FF00
COLOR_YELLOW = 0xFFFF00
COLOR_ORANGE = 0xFFA500
COLOR_BLUE = 0x0000FF

BACKGROUND_COLOR = 0x000000

display = board.DISPLAY
splash = displayio.Group()
display.root_group = splash

color_bitmap = displayio.Bitmap(display.width, display.height, 1)
color_palette = displayio.Palette(1)
color_palette[0] = BACKGROUND_COLOR

bg_sprite = displayio.TileGrid(color_bitmap, pixel_shader=color_palette, x=0, y=0)
splash.append(bg_sprite)

text = "Hello world!"
text_height = 15
text_line1 = label.Label(terminalio.FONT, text="", color=COLOR_RED, x=0, y=0)
text_line2 = label.Label(
    terminalio.FONT, text=text, color=COLOR_GREEN, x=0, y=text_height
)
text_line3 = label.Label(
    terminalio.FONT, text="", color=COLOR_ORANGE, x=0, y=text_height * 2
)
text_line4 = label.Label(
    terminalio.FONT, text="", color=COLOR_BLUE, x=0, y=text_height * 3
)
text_width = text_line1.bounding_box[2] * FONTSCALE
text_group = displayio.Group(
    scale=FONTSCALE,
    x=0,
    y=20,
    # x=display.width // 2 - text_width // 2,
    # y=display.height // 2,
)
text_group.append(text_line1)
text_group.append(text_line2)
text_group.append(text_line3)
text_group.append(text_line4)
splash.append(text_group)


def display_magnet_status(detected, strength):
    label = text_line1
    if detected:
        label.text = f"Magnet strength: {strength}"
        label.color = COLOR_GREEN
    else:
        label.text = "Magnet not detected"
        label.color = COLOR_RED


def display_angle(angle):
    label = text_line2
    label.text = f"Angle: {angle:.4f}"


def display_speed(speed):
    label = text_line3
    label.text = f"Speed: {speed:.4f}"


def display_connection_status(connected):
    label = text_line4
    if connected:
        label.text = "MQTT Connected"
        label.color = COLOR_GREEN
    else:
        label.text = "MQTT Disconnected"
        label.color = COLOR_RED


# Connect to WiFi

print(f"My MAC addres: {[hex(i) for i in wifi.radio.mac_address]}")
print("Available WiFi networks:")
for network in wifi.radio.start_scanning_networks():
    print(
        "\t%s\5\5RSSI: %d\tChannel: %d"
        % (str(network.ssid, "utf-8"), network.rssi, network.channel)
    )
wifi.radio.stop_scanning_networks()

print(f"Connecting to {os.getenv('CIRCUITPY_WIFI_SSID')}")
wifi.radio.connect(
    os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD")
)
print(f"Connected to {os.getenv('CIRCUITPY_WIFI_SSID')}")
print(f"My IP address: {wifi.radio.ipv4_address}")


# MQTT setup and callbacks
def onConnect(client, userdata, flags, rc):
    print("Connected to MQTT broker with result code", rc)
    connected = True
    display_connection_status(True)


def onDisconnect(client, userdata, rc):
    print("Disconnected from MQTT broker with result code", rc)
    connected = False
    display_connection_status(False)


def onSubscribe(client, userdata, mid, granted_qos):
    print("Subscribed to topic with mid", mid)


def onUnsubscribe(client, userdata, mid):
    print("Unsubscribed from topic with mid", mid)


def onMessage(client, userdata, message):
    print(f"Received message on topic {message.topic}: {message.payload}")


def onPublish(client, userdata, topic, pid):
    return


pool = adafruit_connection_manager.get_radio_socketpool(wifi.radio)
# pool = adafruit_connection_manager.get_radio_socketpool(esp)

# MQTT topics
mqtt_sensor_angle_topic = "sensor/angle"
mqtt_sensor_speed_topic = "sensor/speed"

# Setup MQTT client
mqtt_client = mqtt.MQTT(
    broker=os.getenv("MQTT_BROKER"),
    port=int(os.getenv("MQTT_PORT", 1883)),
    socket_pool=pool,
)

mqtt_client.on_connect = onConnect
mqtt_client.on_disconnect = onDisconnect
mqtt_client.on_subscribe = onSubscribe
mqtt_client.on_unsubscribe = onUnsubscribe
mqtt_client.on_message = onMessage
mqtt_client.on_publish = onPublish

mqtt_is_connected = False
display_connection_status(mqtt_is_connected)
try:
    print(f"Attempting to connect to {mqtt_client.broker}")
    mqtt_client.connect()
    mqtt_is_connected = True
except Exception as e:
    print("Failed to connect to MQTT broker:", e)

# Angle sensor functions

angle_offset = 0
angleDeg_prev = 0
speed_prev = 0

ANGLE_SENSOR_MAX_ANGLE = 4095
ANGLE_SENSOR_MIN_ANGLE = 0
REPORT_INTERVAL = 0.1
REPORT_RESOLUTION = 1


# 4 - 290 = -286, which should be treated as 74 (360 - 286) for circular angle difference
def get_angle_delta(angle, prev_angle):
    delta = (angle - prev_angle + 180) % 360 - 180
    if abs(delta) < REPORT_RESOLUTION:
        return 0
    # if delta < 0:
    #     delta += 360
    return abs(delta)


def get_angle_degrees(angle):
    return (angle / ANGLE_SENSOR_MAX_ANGLE * 360) % 360


def get_direction(angle, prev_angle):
    if angle < prev_angle:
        return -1
    if angle == prev_angle:
        return 0
    if angle > prev_angle:
        return 1
    return 1 if (angle - prev_angle) > 0 else -1


def get_speed(angle, prev_angle, delta, dt):
    if delta < 2 or dt <= 0:
        return 0
    return delta / dt


def get_speed_delta(speed, speed_prev):
    return abs(speed - speed_prev)


print("Starting angle sensor monitoring...")
print(f"Report interval: {REPORT_INTERVAL}s, Report resolution: {REPORT_RESOLUTION}°")
as5600.max_angle = 4095
print(f"Angle sensor max angle: {as5600.max_angle}")

time_prev = time.monotonic()

# Continuously read and display angle values
while True:
    now = time.monotonic()
    elapsed = now - time_prev
    time_prev = now

    # Get angle readings
    raw_angle = as5600.raw_angle
    angle = as5600.angle

    if not button1.value:
        print("Button 1 pressed")
        angle_offset = angle
        print(f"Offset set to {angle_offset}")

    # Build output string
    output = (
        f"Raw: {raw_angle:4d} (0x{raw_angle:03X}) | Scaled: {angle:4d} (0x{angle:03X})"
    )

    # Check status conditions
    if as5600.magnet_detected:
        output += " | Magnet: YES"
    else:
        output += " | Magnet: NO "

    if as5600.min_gain_overflow:
        output += " | MH: magnet too strong"

    if as5600.max_gain_overflow:
        output += " | ML: magnet too weak"

    # Get AGC and Magnitude values
    agc = as5600.agc
    magnitude = as5600.magnitude
    output += f" | AGC: {agc:3d} | Mag: {magnitude:4d}"
    print(output)

    angleDeg = get_angle_degrees(angle - angle_offset)
    display_magnet_status(as5600.magnet_detected, as5600.magnitude)
    display_angle(angleDeg)

    speed = get_speed(
        angleDeg,
        angleDeg_prev,
        get_angle_delta(angleDeg, angleDeg_prev),
        elapsed,
    )
    display_speed(speed)

    if mqtt_is_connected:
        if as5600.magnet_detected:
            if get_angle_delta(angleDeg, angleDeg_prev) >= REPORT_RESOLUTION:
                mqtt_client.publish("sensor/angle", f"{angleDeg:4f}")

            if get_speed_delta(speed, speed_prev) >= REPORT_RESOLUTION:
                mqtt_client.publish("sensor/speed", f"{speed:4f}")

    print(
        f"Angle: {angleDeg:4f}, AnglePrev: {angleDeg_prev:4f}, AngleDelta: {get_angle_delta(angleDeg, angleDeg_prev):4f}"
    )
    print(
        f"Speed: {speed:4f}, SpeedPrev: {speed_prev:4f}, SpeedDelta: {get_speed_delta(speed, speed_prev):4f}"
    )
    angleDeg_prev = angleDeg
    speed_prev = speed

    time.sleep(REPORT_INTERVAL)
