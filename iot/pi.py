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
SERVER_NAME = os.getenv('SERVER_NAME', "https://lang.thekao.cloud/generate-speech")
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
        if 'memory_data' in data:
            content = json.loads(data['memory_data'])
            logger.info(f"Content parsed from memory_data: {content}")
        else:
            content = data
            logger.info(f"Using provided data as content: {content}")

        logger.info(f"Sending data to server: {content}")
        response = requests.post(SERVER_NAME, headers=HEADERS, json=content, timeout=10)
        logger.info(f"Response status code: {response.status_code}")
        response.raise_for_status()
        logger.info("Request successful.")
        return response.content
    except requests.RequestException as e:
        logger.error(f"HTTP request error: {e}")
        return None


def play_audio(audio_data):
    try:
        logger.info("Loading audio data into stream.")
        audio_stream = io.BytesIO(audio_data)
        pygame.mixer.music.load(audio_stream)
        logger.info("Audio data loaded, starting playback.")
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(1)
        logger.info("Audio playback finished.")
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
        if isinstance(tag_data, bytearray):
            data_hex = ''.join(['{:02x}'.format(x) for x in tag_data])
        elif isinstance(tag_data, str):
            data_hex = tag_data  # If it's already a string, use it as is
        else:
            logger.error("Unsupported data type for tag data")
            return None

        logger.info(f"Tag Memory Data: {data_hex}")
        return {"memory_data": data_hex}
    except Exception as e:
        logger.error(f"Error processing tag data: {e}")
        return None


def is_valid_json(json_str):
    try:
        json.loads(json_str)
        return True
    except json.JSONDecodeError:
        return False

def write_nfc(pn532, json_str, start_page=4):
    # Check if the string is valid JSON
    if not is_valid_json(json_str):
        logger.error("Invalid JSON string")
        return

    # Convert string to bytes
    byte_data = json_str.encode()

    # Define the page size (typically 4 bytes for NFC tags)
    page_size = 4

    # Calculate the number of pages needed
    num_pages = len(byte_data) // page_size + (len(byte_data) % page_size > 0)

    # Write data to NFC tag
    for i in range(num_pages):
        # Calculate page index
        page = start_page + i

        # Get the byte chunk to write
        chunk = byte_data[i*page_size:(i+1)*page_size]

        # Pad the chunk with zeros if it's less than the page size
        while len(chunk) < page_size:
            chunk += b'\x00'

        # Write the chunk to the tag
        write_to_nfc_tag(pn532, page, list(chunk))

    logger.info("JSON string written to NFC tag")

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


def read_tag_memory(pn532, start_page=4):
    try:
        logger.info("Reading length data from NFC tag.")
        length_data = pn532.ntag2xx_read_block(start_page)
        if length_data is None:
            logger.error("Failed to read length data from NFC tag")
            return None

        length = int.from_bytes(length_data[:2], 'big')
        logger.info(f"Data length: {length}")

        page_size = 4
        total_bytes_to_read = length + 2
        total_pages_to_read = (total_bytes_to_read + page_size - 1) // page_size
        tag_data = bytearray()
        logger.info("Beginning to read tag memory.")
        for i in range(total_pages_to_read):
            data = pn532.ntag2xx_read_block(start_page + i)
            if data is None:
                logger.error(f"Failed to read page {start_page + i}")
                break
            tag_data.extend(data)
        logger.info("Tag memory reading completed.")
        return tag_data[2:2 + length]
    except Exception as e:
        logger.error(f"Error while reading NFC tag memory: {e}")
        return None

def init_nfc_reader():
    i2c = busio.I2C(board.SCL, board.SDA)
    reset_pin = DigitalInOut(board.D6)  # Adjust as per your connection
    pn532 = PN532_I2C(i2c, reset=reset_pin)
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




def main():
    pn532 = init_nfc_reader()
    last_uid = None
    logger.info("Script started, waiting for NFC tag.")
    
    while True:
        try:
            nfc_data = check_for_nfc_tag(pn532)
            if nfc_data and nfc_data != last_uid:
                last_uid = nfc_data
                logger.info("New NFC tag detected, processing.")
                full_memory = read_tag_memory(pn532, start_page=4)
                logger.info("Tag memory read, processing data.")

                if full_memory:
                    parsed_data = parse_tag_data(full_memory.decode('utf-8').rstrip('\x00'))
                    if parsed_data:
                        logger.info(f"Parsed data: {parsed_data}")
                        audio_data = perform_http_request(parsed_data)
                        if audio_data:
                            logger.info("Audio data received, starting playback.")
                            play_audio(audio_data)
            elif not nfc_data:
                last_uid = None
        except Exception as e:
            logger.error(f"An error occurred: {e}")
        time.sleep(1)



if __name__ == "__main__":
    main()