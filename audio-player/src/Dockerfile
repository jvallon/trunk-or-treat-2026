FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for audio playback
# alsa-utils: ALSA (Advanced Linux Sound Architecture) utilities
# libsdl2-2.0-0: SDL2 library required by pygame for audio
# libsdl2-mixer-2.0-0: SDL2 mixer for audio playback
RUN apt-get update && apt-get install -y --no-install-recommends \
    alsa-utils \
    libpulse0 \
    pulseaudio-utils \
    libsdl2-2.0-0 \
    libsdl2-mixer-2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set environment variable for SDL2 audio driver
# Use dummy driver by default; can be overridden at runtime
ENV SDL_AUDIODRIVER=dummy

CMD ["python", "main.py"]