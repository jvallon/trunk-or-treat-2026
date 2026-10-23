"""
Audio Player - MQTT-based audio playback application
Subscribes to MQTT topics and plays audio based on received messages
"""

import os
import sys
import yaml
import logging
from pathlib import Path
from typing import Callable, Dict, Any
import threading

import paho.mqtt.client as mqtt
import pygame

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AudioPlayer:
    """Handles audio playback"""
    
    def __init__(self, data_dir: str, volume: float = 0.8):
        """
        Initialize the audio player
        
        Args:
            data_dir: Directory containing audio files
            volume: Volume level (0.0 to 1.0)
        """
        self.data_dir = Path(data_dir)
        self.volume = max(0.0, min(1.0, volume))
        
        # Initialize pygame mixer
        pygame.mixer.init()
        pygame.mixer.music.set_volume(self.volume)
        
        logger.info(f"AudioPlayer initialized with data_dir={self.data_dir}, volume={self.volume}")
    
    def play_audio(self, filename: str) -> bool:
        """
        Play an audio file
        
        Args:
            filename: Name of the audio file (must exist in data_dir)
            
        Returns:
            True if playback started successfully, False otherwise
        """
        filepath = self.data_dir / filename
        
        if not filepath.exists():
            logger.error(f"Audio file not found: {filepath}")
            return False
        
        if not filepath.suffix.lower() in ['.wav', '.mp3', '.ogg', '.flac']:
            logger.error(f"Unsupported audio format: {filepath.suffix}")
            return False
        
        try:
            logger.info(f"Playing audio: {filename}")
            pygame.mixer.music.load(str(filepath))
            pygame.mixer.music.play()
            return True
        except Exception as e:
            logger.error(f"Error playing audio file {filename}: {e}")
            return False
    
    def stop_audio(self):
        """Stop current audio playback"""
        pygame.mixer.music.stop()
        logger.info("Audio playback stopped")
    
    def is_playing(self) -> bool:
        """Check if audio is currently playing"""
        return pygame.mixer.music.get_busy()
    
    def set_volume(self, volume: float):
        """Set playback volume (0.0 to 1.0)"""
        self.volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(self.volume)
        logger.info(f"Volume set to {self.volume}")


class MQTTAudioBridge:
    """Connects MQTT topics to audio playback"""
    
    def __init__(self, config_file: str):
        """
        Initialize the MQTT Audio Bridge
        
        Args:
            config_file: Path to configuration YAML file
        """
        self.config_dir = Path(config_file).resolve().parent
        self.config = self._load_config(config_file)
        self.audio_player = self._init_audio_player()
        self.handlers: Dict[str, Callable] = self._setup_handlers()
        self.client = self._init_mqtt_client()
        self.current_angle: float | None = None
        self.current_speed: float | None = None
        self.rotation_was_active = False
    
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"Configuration loaded from {config_file}")
        return config
    
    def _init_audio_player(self) -> AudioPlayer:
        """Initialize the audio player"""
        data_dir = self.config.get('audio', {}).get('data_dir', '/data')
        # Relative paths are resolved against the config file's directory
        data_dir = str((self.config_dir / data_dir).resolve())
        volume = self.config.get('audio', {}).get('default_volume', 0.8)
        return AudioPlayer(data_dir, volume)
    
    def _setup_handlers(self) -> Dict[str, Callable]:
        """Setup topic handlers"""
        return {
            'handle_angle': self.handle_angle,
            'handle_speed': self.handle_speed,
        }
    
    def _init_mqtt_client(self) -> mqtt.Client:
        """Initialize MQTT client"""
        client = mqtt.Client()
        
        client.on_connect = self.on_connect
        client.on_disconnect = self.on_disconnect
        client.on_message = self.on_message
        
        return client
    
    def on_connect(self, client: mqtt.Client, userdata, flags, rc):
        """MQTT on_connect callback"""
        if rc == 0:
            logger.info("Connected to MQTT broker")
            # Subscribe to configured topics
            for topic_config in self.config.get('topics', []):
                topic = topic_config['topic']
                client.subscribe(topic)
                logger.info(f"Subscribed to topic: {topic}")
        else:
            logger.error(f"Failed to connect to MQTT broker with code {rc}")
    
    def on_disconnect(self, client: mqtt.Client, userdata, rc):
        """MQTT on_disconnect callback"""
        if rc != 0:
            logger.warning(f"Unexpected disconnection from MQTT broker with code {rc}")
        else:
            logger.info("Disconnected from MQTT broker")
    
    def on_message(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
        """MQTT on_message callback - routes to topic-specific handlers"""
        topic = msg.topic
        payload = msg.payload.decode('utf-8')
        
        logger.debug(f"Received message on topic {topic}: {payload}")
        
        # Find matching topic config and call its handler
        for topic_config in self.config.get('topics', []):
            if topic_config['topic'] == topic:
                handler_name = topic_config.get('handler')
                if handler_name in self.handlers:
                    try:
                        self.handlers[handler_name](payload)
                    except Exception as e:
                        logger.error(f"Error in handler {handler_name}: {e}")
                break
    
    def handle_angle(self, payload: str):
        """Handler for sensor/angle topic"""
        try:
            angle_value = float(payload)
            logger.info(f"Angle sensor value: {angle_value}")
        except ValueError:
            logger.error(f"Invalid angle value: {payload}")
            return

        self.current_angle = angle_value
        
        if self.audio_player.is_playing():
            return
        
        if self.current_speed is not None:
            self.play_sensor_audio(self.current_angle, self.current_speed)
    
    def handle_speed(self, payload: str):
        """Handler for sensor/speed topic"""
        try:
            speed_value = float(payload)
            logger.info(f"Speed sensor value: {speed_value}")
        except ValueError:
            logger.error(f"Invalid speed value: {payload}")
            return

        self.current_speed = speed_value
        if not self.audio_player.is_playing():
            self.play_sensor_audio(self.current_angle, self.current_speed)

    def play_sensor_audio(self, angle: float | None, speed: float):
        """Play the configured angle audio once rotation transitions to stopped."""
        if speed != 0:
            self.rotation_was_active = True
            return

        if not self.rotation_was_active:
            return

        self.rotation_was_active = False
        if angle is None:
            logger.error("Cannot play angle audio: no angle value has been received")
            return

        angle_mapping = self.config.get('audio', {}).get('mapping', {}).get('sensor/angle', {})
        angle_segment_start = int((angle % 360) // 15) * 15
        angle_segment = f"{angle_segment_start}-{angle_segment_start + 14}"
        filename = angle_mapping.get(angle_segment)

        if filename is None:
            logger.error(f"No audio mapping configured for angle segment {angle_segment}")
            return

        if not self.audio_player.is_playing():
            self.audio_player.play_audio(filename)
            
    
    def connect(self):
        """Connect to MQTT broker"""
        mqtt_config = self.config.get('mqtt', {})
        broker = mqtt_config.get('broker', 'localhost')
        port = mqtt_config.get('port', 1883)
        keepalive = mqtt_config.get('keepalive', 60)
        
        try:
            logger.info(f"Connecting to MQTT broker at {broker}:{port}")
            self.client.connect(broker, port, keepalive)
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            raise
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        self.client.disconnect()
    
    def start(self):
        """Start the MQTT client loop"""
        logger.info("Starting MQTT Audio Bridge")
        self.client.loop_start()
    
    def stop(self):
        """Stop the MQTT client loop"""
        logger.info("Stopping MQTT Audio Bridge")
        self.client.loop_stop()
    
    def run(self):
        """Run the application (blocking)"""
        self.connect()
        self.start()
        
        try:
            logger.info("Audio Player running. Press Ctrl+C to exit.")
            while True:
                threading.Event().wait(1)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            self.stop()
            self.disconnect()
            self.audio_player.stop_audio()
            pygame.mixer.quit()


def main():
    """Main entry point"""
    config_file = os.getenv('CONFIG_FILE', '../config/config.yaml')
    
    if not os.path.exists(config_file):
        logger.error(f"Configuration file not found: {config_file}")
        sys.exit(1)
    
    bridge = MQTTAudioBridge(config_file)
    bridge.run()


if __name__ == '__main__':
    main()
