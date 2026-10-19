# Angle sensor

This project contains code and configuration for an angle sensor to send values to MQTT broker at `sensor/angle` and `sensor/speed`.

## Configuration

1. Create a `settings.toml` file with the necessary configuration for the MQTT broker and sensor settings.

Example `settings.toml`:
MQTT_BROKER = "mqtt://your-broker-address"
MQTT_PORT = 1883
CIRCUITPY_WIFI_SSID = "your-wifi-ssid"
CIRCUITPY_WIFI_PASSWORD = "your-wifi-password"
