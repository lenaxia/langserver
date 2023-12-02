import requests
import time
import pygame
import logging
import json
import io
import os
import signal
import sys

# Environment and Configuration
os.environ['SDL_AUDIODRIVER'] = 'dummy'
SERVER_NAME = os.getenv('SERVER_NAME', "http://localhost:5000/generate-speech")
API_TOKEN = os.getenv('API_TOKEN', "A3BQEJMGGGDG2JGCKSKwicAQYqYT9k7W")
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": API_TOKEN
}

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# Initialize audio
pygame.init()
pygame.mixer.init()

def perform_http_request(data):
    try:
        response = requests.post(SERVER_NAME, headers=HEADERS, json=data, timeout=10)
        if response.status_code == 200:
            return response.content
        else:
            logger.error(f"HTTP request failed with code: {response.status_code}, response: {response.text}")
            return None
    except requests.ConnectionError:
        logger.error("Failed to connect to server")
        return None
    except requests.Timeout:
        logger.error("Request timed out")
        return None
    except requests.RequestException as e:
        logger.error(f"HTTP request error: {e}")
        return None

def play_audio(audio_data):
    try:
        audio_stream = io.BytesIO(audio_data)
        pygame.mixer.music.load(audio_stream)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(1)
    except Exception as e:
        logger.error(f"Error playing audio: {e}")

def parse_nfc_data(nfc_data):
    try:
        data = json.loads(nfc_data)
        return data
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing NFC data: {e}")
        return None

def check_for_nfc_tag():
    # Mock NFC tag reading
    input("Press Enter to simulate NFC tag detection...")
    return '{"localization":{"zh-tw":"馬","en":"horse"}}'

def signal_handler(sig, frame):
    logger.info("Gracefully shutting down")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

while True:
    nfc_data = check_for_nfc_tag()
    if nfc_data:
        logger.info("NFC tag detected")
        parsed_data = parse_nfc_data(nfc_data)
        if parsed_data:
            audio_data = perform_http_request(parsed_data)
            if audio_data:
                logger.info("Simulating audio playback")
                play_audio(audio_data)
                logger.info("Audio playback simulation complete")
    time.sleep(1)

