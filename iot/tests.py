import board
import busio
from digitalio import DigitalInOut
from adafruit_pn532.i2c import PN532_I2C
import pygame
import time

i2c = busio.I2C(board.SCL, board.SDA)
reset_pin = DigitalInOut(board.D6)  # Adjust as per your connection
pn532 = PN532_I2C(i2c, reset=reset_pin)

def test_nfc():
    ic, ver, rev, support = pn532.firmware_version
    print(f"Found PN532 with firmware version: {ver}.{rev}")

    pn532.SAM_configuration()

    print("Waiting for an NFC tag...")
    while True:
        uid = pn532.read_passive_target(timeout=0.5)
        if uid is not None:
            print(f"Found card with UID: {uid.hex()}")
            break


def test_audio():
    # Initialize Pygame Mixer
    pygame.mixer.init()
    pygame.mixer.music.load('/path/to/test.wav')  # Replace with the path to your WAV file

    # Play Audio
    print("Playing Test Audio")
    pygame.mixer.music.play()

    # Wait for the audio to finish playing
    while pygame.mixer.music.get_busy():
        time.sleep(1)

    print("Audio Playback Complete")