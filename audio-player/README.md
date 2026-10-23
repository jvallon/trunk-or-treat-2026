# Audio Player - MQTT-Based Audio Playback

A Python-based application that subscribes to MQTT topics and plays audio files based on received sensor data. Configured for Docker deployment on WSL2 Windows.

## Features

- **MQTT Topic Subscription**: Subscribes to configurable MQTT topics
- **Audio Playback**: Plays WAV, MP3, OGG, and FLAC audio files
- **Event-Driven**: Triggers audio playback based on sensor data
- **Docker Support**: Optimized for WSL2 Windows audio output
- **Configurable**: YAML-based configuration for topics and handlers

## Project Structure

```
audio-player/
├── config/
│   └── config.yaml          # MQTT and topic configuration
├── data/
│   └── *.wav                # Audio files
├── src/
│   ├── main.py              # Main application
│   ├── requirements.txt      # Python dependencies
│   └── Dockerfile           # Container image definition
└── docker-compose.yml       # Docker Compose configuration
```

## Configuration

### config.yaml

Edit `audio-player/config/config.yaml` to configure MQTT broker, topics, and audio settings:

```yaml
mqtt:
  broker: mqtt              # MQTT broker hostname
  port: 1883                # MQTT port
  client_id: audio-player   # MQTT client ID
  keepalive: 60
  reconnect_delay: 5

topics:
  - topic: sensor/angle
    handler: handle_angle
  - topic: sensor/speed
    handler: handle_speed

audio:
  data_dir: /data           # Audio files directory
  default_volume: 0.8       # Volume level (0.0-1.0)
```

## Running Locally (Without Docker)

### Prerequisites

- Python 3.11+ (Python 3.12+ supported via pygame-ce)
- Audio device with ALSA or PulseAudio support
- MQTT broker running (e.g., Mosquitto)

### Installation

```bash
cd audio-player/src
pip install -r requirements.txt
```

**Note for Python 3.12+**: The project uses `pygame-ce` (Community Edition) for compatibility with Python 3.12+ where `distutils` was removed. This is a 100% drop-in replacement for pygame with better modern Python support.

### Running

```bash
export CONFIG_FILE=../config/config.yaml
python main.py
```

## Running with Docker (WSL2 Windows)

### Prerequisites

- Docker Desktop with WSL2 backend
- WSL2 with audio support configured
- MQTT broker accessible from container

### Building

```bash
docker-compose build
```

### Running

```bash
docker-compose up -d
```

### Viewing Logs

```bash
docker-compose logs -f audio-player
```

### Stopping

```bash
docker-compose down
```

## WSL2 Audio Configuration

The Docker setup uses ALSA for audio output. To enable audio in WSL2:

### Option 1: Using Default Audio Driver (Dummy/Silent)
The default configuration uses the dummy driver, which won't produce sound but won't error:
```bash
SDL_AUDIODRIVER=dummy
```

### Option 2: Using PulseAudio (Recommended for WSL2)
To use PulseAudio from your Windows host:

1. Install PulseAudio on Windows (or use WSL2 native PulseAudio)
2. Uncomment the PulseAudio volume mount in `docker-compose.yml`
3. Update the environment variable:
```yaml
SDL_AUDIODRIVER: pulse
PULSE_SERVER: unix:/run/user/1000/pulse/native
```

### Option 3: Using ALSA Directly
Connect directly to ALSA devices (requires privileged mode):
```yaml
SDL_AUDIODRIVER: alsa
```

## MQTT Message Format

### /sensor/angle Topic
Send numeric angle values (0-360 degrees):
```
mosquitto_pub -h localhost -t /sensor/angle -m "45.5"
```

### /sensor/speed Topic
Send numeric speed values:
```
mosquitto_pub -h localhost -t /sensor/speed -m "15.2"
```

## Handlers

### handle_angle(payload: str)
Stores the latest angle from the sensor. The configured angle audio is played once
when the speed sensor reports that rotation has stopped. Angle-to-file ranges are
configured under `audio.mapping.sensor/angle` in `config.yaml`.

### handle_speed(payload: str)
Tracks whether the sensor is rotating and triggers the angle audio when speed
transitions from a nonzero value to zero. Speed-based audio mapping is not used.

## Adding Custom Handlers

To add a new MQTT topic:

1. Add to `config.yaml`:
```yaml
topics:
  - topic: /sensor/new_topic
    handler: handle_new_topic
```

2. Add handler method to `MQTTAudioBridge` class in `main.py`:
```python
def handle_new_topic(self, payload: str):
    """Handler for /sensor/new_topic topic"""
    # Your logic here
    self.audio_player.play_audio("filename.wav")
```

## Audio Files

Place audio files (WAV, MP3, OGG, FLAC) in the `audio-player/data/` directory. Files are accessible by filename in handlers.

## Troubleshooting

### No audio output in Docker (WSL2)
1. Check that audio device is accessible: `docker exec audio-player arecord -l`
2. Verify ALSA configuration: `docker exec audio-player cat /etc/asound.conf`
3. Try changing `SDL_AUDIODRIVER` in `docker-compose.yml` (pulse, alsa, dummy)

### MQTT Connection Failed
1. Verify MQTT broker is running: `docker exec mqtt mosquitto_sub -h localhost -t "#" -u test -P test`
2. Check broker hostname in `config.yaml` (use service name `mqtt` in Docker)
3. Verify network connectivity between containers

### Audio File Not Found
- Ensure audio files are in `audio-player/data/` directory
- Check file permissions: files should be readable by container
- Verify exact filename in handler code (case-sensitive on Linux)

## Development

### Logging
The application logs to stdout. Set `logging.basicConfig(level=logging.DEBUG)` in `main.py` for verbose output.

### Testing Handlers Locally
```python
from src.main import AudioPlayer, MQTTAudioBridge

player = AudioPlayer('./audio-player/data', 0.8)
player.play_audio('phm.rocky.01.why teacher in space.wav')
```

## License

See root project LICENSE file.
