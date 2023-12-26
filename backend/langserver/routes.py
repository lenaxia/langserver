# langserver/routes.py
from googletrans import Translator, LANGUAGES
from gtts import gTTS, lang
import os
import re
import io
import base64
import datetime
import string
import secrets
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from functools import wraps
import logging
from logging.handlers import RotatingFileHandler
from . import app, limiter, db
from .models import APIToken
import hashlib
from flask import current_app
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback


"""
Perform a basic health check.

This function is the endpoint for the '/healthz' route and is triggered by a GET request. It checks the health of the application by performing various tasks, such as making a simple database query, checking if critical services (like external APIs) are reachable, and ensuring basic app functions are working.

Returns:
    A JSON response containing the status of the health check. If the health check is successful, it returns a status of "healthy" and a HTTP status code of 200. If the health check fails, it returns a status of "unhealthy", along with the details of the error, and a HTTP status code of 500.
"""
@app.route('/healthz', methods=['GET'])
def health_check():
    try:
        # Perform a basic health check. For example, you can:
        # - Make a simple database query
        # - Check if critical services (like external APIs) are reachable
        # - Return a simple "OK" if basic app functions are working
        return jsonify({"status": "healthy"}), 200
    except Exception as e:
        current_app.logger.error(f"Health check failed: {e}")
        return jsonify({"status": "unhealthy", "details": str(e)}), 500

"""
Decorator to require an API token for access to the decorated function.

Parameters:
- f: The function to be decorated.

Returns:
- The decorated function.

Raises:
- Unauthorized access error if the token is invalid or missing.
"""
def require_token(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        incoming_token = request.headers.get('Authorization')
        if not incoming_token:
            current_app.logger.warning("Missing Authorization header")
            return jsonify({'error': 'Unauthorized access'}), 401
        
        # Hash the incoming token
        admin_token = current_app.config.get('ADMIN_TOKEN')
        hashed_incoming_token = APIToken.hash_token(incoming_token, admin_token)

        # Check if the provided token is the admin token
        if incoming_token == admin_token:
            return f(*args, **kwargs)

        # Retrieve the token record using the hashed token
        token_record = APIToken.query.filter_by(token=hashed_incoming_token).first()
        if not token_record:
            current_app.logger.warning(f"Invalid token attempted: {incoming_token}")
            return jsonify({'error': 'Unauthorized access'}), 401

        # Apply rate limit based on the token's rate limit setting
        limiter.limit(f"{token_record.rate_limit} per minute")(f)
        return f(*args, **kwargs)
    return decorated_function



react_build_directory = os.path.abspath("/app/web")

@app.route('/admin/static/<path:path>')
def serve_admin_static(path):
    return send_from_directory(os.path.join(react_build_directory, 'static'), path)

@app.route('/admin/<filename>')
def serve_admin_root_files(filename):
    if filename in ['manifest.json', 'favicon.ico', 'logo192.png', 'logo512.png']:
        return send_from_directory(react_build_directory, filename)
    # Forward to the catch-all route for other paths
    return serve_admin(filename)

@app.route('/admin', defaults={'path': ''})
@app.route('/admin/<path:path>')
def serve_admin(path):
    return send_from_directory(react_build_directory, 'index.html')


"""
Adds a new token to the API.

Returns:
    - If the token ID is invalid or missing, returns a JSON response with an error message and a 400 status code.
    - If the token already exists for the given ID, returns a JSON response with the existing token and a 200 status code.
    - If the token is successfully added to the database, returns a JSON response with the new token and a 201 status code.
    - If there is an error adding the token to the database, returns a JSON response with an error message and a 500 status code.
"""
@app.route('/add-token', methods=['POST'])
@limiter.limit("10 per minute")
def add_token():
    data = request.json or {}
    token_id = data.get('id')
    rate_limit_input = data.get('rate_limit')

    # Validate token ID
    if not token_id or not re.match("^[a-zA-Z0-9_-]+$", token_id):
        current_app.logger.error("Invalid token ID format or missing ID")
        return jsonify({'error': 'Invalid ID format'}), 400

    # Validate rate limit as integer
    if isinstance(rate_limit_input, int):
        rate_limit = rate_limit_input
    else:
        rate_limit = int(current_app.config.get('DEFAULT_RATE_LIMIT', 10))

    # Check for existing token
    if existing_token := APIToken.query.filter_by(id=token_id).first():
        current_app.logger.info(f"Token ID {token_id} already exists.")
        return jsonify({'message': 'Token ID already exists. Please use a different ID.'}), 409

    # Generate the new token
    characters = string.ascii_letters + string.digits
    new_token_str = ''.join(secrets.choice(characters) for _ in range(32))

    # Salt and hash the token
    admin_token = current_app.config.get('ADMIN_TOKEN', '')
    salted_hashed_token = APIToken.hash_token(new_token_str, admin_token)

    # Create a new APIToken instance
    new_token = APIToken(id=token_id, token=salted_hashed_token, rate_limit=rate_limit)

    try:
        db.session.add(new_token)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Error adding token: {e}")
        return jsonify({'error': 'Internal Server Error'}), 500

    # Return the original, unsalted, unhashed token
    return jsonify({'token': new_token_str}), 201


"""
Edit a token's rate limit.

Returns:
    JSON: A JSON response with the following keys:
        - 'message': A success message if the token was updated successfully.
        - 'error': An error message if there was an issue with the request.

Raises:
    400: If the token ID format is invalid or missing.
    404: If the token ID is not found.
    500: If there is an internal server error.

"""
@app.route('/edit-token', methods=['POST'])
@limiter.limit("2 per minute")
def edit_token():
    data = request.json or {}
    token_id = data.get('id')
    rate_limit_input = data.get('rate_limit')

    # Validate token ID
    if not token_id or not re.match("^[a-zA-Z0-9_-]+$", token_id):
        app.logger.error("Invalid token ID format or missing ID")
        return jsonify({'error': 'Invalid ID format'}), 400

    # Determine rate limit value
    if rate_limit_input is not None:
        try:
            rate_limit = int(rate_limit_input)
        except ValueError:
            app.logger.error("Rate limit must be an integer")
            return jsonify({'error': 'Rate limit must be an integer'}), 400
    else:
        rate_limit = current_app.config.get('DEFAULT_RATE_LIMIT', 10)

    token = APIToken.query.filter_by(id=token_id).first()
    if not token:
        app.logger.error(f"Token ID not found: {token_id}")
        return jsonify({'error': 'Token ID not found'}), 404

    try:
        # Update the rate limit
        token.rate_limit = rate_limit
        db.session.commit()
        app.logger.info(f"Token updated successfully for ID: {token_id}")
        return jsonify({'message': 'Token updated successfully'}), 200
    except Exception as e:
        app.logger.error(f"Error in edit-token: {e}")
        return jsonify({'error': 'Internal Server Error'}), 500


"""
Revoke a token.

This function is responsible for revoking a token. It takes in a token string as a parameter and checks if the token exists in the database. If the token is found, it is deleted from the database. If the token is not found, an error message is returned. If any exception occurs during the process, an internal server error message is returned.

Parameters:
- None

Returns:
- If the token is successfully revoked, a JSON response with a success message and status code 200.
- If the token is not found, a JSON response with an error message and status code 404.
- If any exception occurs, a JSON response with an error message and status code 500.
"""
@app.route('/revoke-token', methods=['POST'])
@limiter.limit("10 per minute")
def revoke_token():
    try:
        token_str = request.json.get('token')
        if not token_str:
            app.logger.info('Revoke token request with missing token field')
            return jsonify({'error': 'Token is required'}), 400

        token = APIToken.query.filter((APIToken.id == token_str) | (APIToken.token == token_str)).first()
        if not token:
            app.logger.info(f'Token or ID not found for revocation: {token_str}')
            return jsonify({'error': 'Token or ID not found'}), 404

        db.session.delete(token)
        db.session.commit()
        app.logger.info(f'Token revoked successfully: {token_str}')
        return jsonify({'message': 'Token revoked successfully'}), 200
    except Exception as e:
        app.logger.error(f"Error in revoke-token: {e}")
        return jsonify({'error': 'Internal Server Error'}), 500


"""
Generates speech based on the provided input data.

Args:
    None

Returns:
    If successful, returns an audio file containing the generated speech in MP3 format.
    If unsuccessful, returns a JSON response with an error message and details.

Valid payloads:
{"localization": {
    "zh-tw": "馬",
    "en": "horse"}}
Or
{"text": "horse",
"language": "en",
"translations": ["zh-TW", "de"]}  

Example Curl:
 curl -X POST http://localhost:5000/generate-speech -H "Authorization: 1qjEkUygv1QfALZnTk8LLUhHWM2rJfHr" -H "Content-Type: application/json" -d '{"text": "the quick brown fox jumped over the lazy dog","language": "en","translations": ["zh-TW"]}' -o response.mp3
"""
@app.route('/generate-speech', methods=['POST'])
@require_token
@limiter.limit("10 per minute")
def generate_speech():
    data = request.json

    try:
        combined_mp3 = io.BytesIO()
        tasks = []

        with ThreadPoolExecutor() as executor:
            if 'localization' in data:
                for lang_code, text in data['localization'].items():
                    if lang_code in lang.tts_langs():
                        tasks.append(executor.submit(generate_tts, lang_code, text))

            elif 'text' in data and 'language' in data and 'translations' in data:
                original_text = data['text']
                original_lang = data['language']

                if original_lang not in lang.tts_langs():
                    app.logger.info(f"Invalid primary language: {original_lang}")
                    return jsonify({"error": "Primary language is invalid"}), 400

                # Queue TTS task for original language
                tasks.append(executor.submit(generate_tts, original_lang, original_text))

                # Queue translation and subsequent TTS tasks
                for lang_code in data['translations']:
                    if lang_code in lang.tts_langs():
                        tasks.append(executor.submit(translate_and_tts, original_text, original_lang, lang_code))

            # Process completed tasks
            for future in as_completed(tasks):
                try:
                    tts_audio = future.result()
                    tts_audio.write_to_fp(combined_mp3)
                except Exception as e:
                    app.logger.error(f"Error in task: {traceback.format_exc()}")

        combined_mp3.seek(0)
        return send_file(combined_mp3, mimetype='audio/mpeg')

    except Exception as e:
        app.logger.error(f"Error in generate-speech: {e}")
        return jsonify({"error": "Text-to-Speech conversion failed", "details": str(e)}), 500

def generate_tts(language, text):
    try:
        tts = gTTS(text=text, lang=language)
        audio_fp = io.BytesIO()
        tts.write_to_fp(audio_fp)
        audio_fp.seek(0)
        return audio_fp
    except Exception as e:
        raise Exception(f"Failed to generate speech for {language}: {e}")

def translate_and_tts(original_text, original_lang, target_lang):
    try:
        translator = Translator()
        translation = translator.translate(original_text, src=original_lang, dest=target_lang).text
        app.logger.info(f"Translation to {target_lang}: {translation}")
        return generate_tts(target_lang, translation)
    except Exception as e:
        raise Exception(f"Failed in translation or TTS for {target_lang}: {e}")



"""
Retrieves a list of all tokens.

Returns:
    - A JSON response with the list of tokens and their corresponding IDs.
        Example: [{"id": 1, "token": "abc123"}, {"id": 2, "token": "xyz456"}]
    - If an error occurs, a JSON response with an error message and details.
        Example: {"error": "Failed to retrieve tokens", "details": "Database connection error"}
"""
@app.route('/list-tokens', methods=['GET'])
@require_token
@limiter.limit("10 per minute")
def list_tokens():
    try:
        tokens = APIToken.query.all()
        token_list = [
            {
                'id': token.id,
                'token': token.token,  # This is the hashed token
                'rate_limit': token.rate_limit,
                'date_created': token.date_created.strftime('%Y-%m-%d %H:%M') if token.date_created else None
            } for token in tokens
        ]
        return jsonify(token_list), 200
    except Exception as e:
        app.logger.error(f"Error in list-tokens: {e}")
        return jsonify({"error": "Failed to retrieve tokens", "details": str(e)}), 500




