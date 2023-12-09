import requests
import time
import pygame # pip install pygame
import logging
import json
import io
import os
import signal
import sys
import board
import busio
from digitalio import DigitalInOut
from adafruit_pn532.i2c import PN532_I2C # pip install adafruit-blinka adafruit-circuitpython-pn532

# Environment and Configuration
SERVER_NAME = os.getenv('SERVER_NAME', "http://lang.thekao.cloud/generate-speech")
API_TOKEN = os.getenv('API_TOKEN', "test123")
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
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
        return response.content
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

def is_valid_localization_schema(data):
    """ Validate if the data matches the localization schema. """
    if not isinstance(data, dict) or 'localization' not in data:
        return False

    localization_data = data['localization']
    if not isinstance(localization_data, dict):
        return False

    # Check that all keys are strings and all values are also strings
    return all(isinstance(key, str) and isinstance(value, str) for key, value in localization_data.items())

def is_valid_translation_schema(data):
    """ Validate if the data matches the translation schema. """
    required_keys = {"text", "language", "translations"}
    if not isinstance(data, dict) or not required_keys.issubset(data.keys()):
        return False
    
    if not isinstance(data['text'], str) or not isinstance(data['language'], str):
        return False

    if not isinstance(data['translations'], list) or not all(isinstance(item, str) for item in data['translations']):
        return False

    return True

def validate_json_data(hex_data):
    try:
        json_str = bytes.fromhex(hex_data).decode('utf-8')
        data = json.loads(json_str)

        if is_valid_localization_schema(data) or is_valid_translation_schema(data):
            return data
    except (ValueError, json.JSONDecodeError, TypeError):
        logger.error("Invalid JSON data")

    return {"text": "No valid json found", "language": "en", "translations": []}

def parse_tag_data(tag_data):
    try:
        data_hex = ''.join(['{:02x}'.format(x) for x in tag_data])
        logger.info(f"Tag Memory Data: {data_hex}")
        return {"memory_data": data_hex}
    except Exception as e:
        logger.error(f"Error processing tag data: {e}")
        return None

def write_to_nfc_tag(pn532, page, data):
    if not isinstance(page, int) or not (0 <= page <= 134):
        logger.error("Invalid page number for NFC tag write operation.")
        return
    if not isinstance(data, (list, tuple)) or len(data) != 4 or not all(isinstance(x, int) and 0 <= x < 256 for x in data):
        logger.error("Data must be a list or tuple of 4 bytes.")
        return
    
    try:
        pn532.ntag2xx_write_block(page, data)
        logger.info(f"Data written to NFC tag at page {page}")
    except Exception as e:
        logger.error(f"Error writing to NFC tag: {e}")

def read_tag_memory(pn532, uid):
    start_page = 0
    end_page = 134  # NTAG215 has 540 bytes of user memory, organized in 135 pages (4 bytes per page)
    tag_data = []

    for page in range(start_page, end_page + 1):
        try:
            data = pn532.ntag2xx_read_block(page)
            if data is not None:
                tag_data.extend(data)
            else:
                logger.error(f"Failed to read page {page}")
                break
        except Exception as e:
            logger.error(f"Error reading page {page}: {e}")
            break

    return tag_data


def init_nfc_reader():
    i2c = busio.I2C(board.SCL, board.SDA)

    reset_pin_number = int(os.getenv('RESET_PIN', '6'))  # Default to pin 6 if not set
    req_pin_number = int(os.getenv('REQ_PIN', '12'))    # Default to pin 12 if not set

    reset_pin = DigitalInOut(getattr(board, f'D{reset_pin_number}'))
    req_pin = DigitalInOut(getattr(board, f'D{req_pin_number}'))

    pn532 = PN532_I2C(i2c, debug=False, reset=reset_pin, req=req_pin)
    pn532.SAM_configuration()

    return pn532


def check_for_nfc_tag(pn532):
    uid = pn532.read_passive_target(timeout=0.5)
    if uid is not None:
        logger.info("NFC tag detected")
        return uid
    return None

def signal_handler(sig, frame):
    logger.info("Gracefully shutting down")
    pygame.quit()  # Properly quit pygame
    sys.exit(0)

# Main execution
def main():
    pn532 = init_nfc_reader()
    last_uid = None

    while True:
        try:
            nfc_data = check_for_nfc_tag(pn532)
            if nfc_data and nfc_data != last_uid:
                last_uid = nfc_data
                full_memory = read_tag_memory(pn532, nfc_data)
                if full_memory:
                    parsed_data = parse_tag_data(full_memory)
                    if parsed_data:
                        audio_data = perform_http_request(parsed_data)
                        if audio_data:
                            play_audio(audio_data)
            elif not nfc_data:
                last_uid = None  # Reset when no tag is present

        except Exception as e:
            logger.error(f"An error occurred: {e}")
            # Handle specific exceptions as needed

        time.sleep(1)  # Adjust as needed


# Signal handler setup
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    main()
