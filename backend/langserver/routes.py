# langserver/routes.py
from googletrans import Translator, LANGUAGES
from gtts import gTTS, lang
import os
import re
import io
import base64
import datetime
from flask import Flask, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from functools import wraps
import logging
from logging.handlers import RotatingFileHandler
from . import app, limiter, db
from .models import APIToken

def require_token(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not APIToken.query.filter_by(token=token).first():
            return jsonify({'error': 'Unauthorized access'}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/add-token/<id>', methods=['POST'])
@limiter.limit("2 per minute")
def add_token(id):
    if not re.match("^[a-zA-Z0-9_-]+$", id):
        return jsonify({'error': 'Invalid ID format'}), 400

    existing_token = APIToken.query.filter_by(id=id).first()
    if existing_token:
        return jsonify({'token': existing_token.token}), 200

    random_bytes = os.urandom(24)
    token = base64.b64encode(random_bytes).decode('utf-8')
    new_token = APIToken(id=id, token=token)
    
    db.session.add(new_token)
    db.session.commit()
    return jsonify({'token': token}), 201

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

@app.route('/regenerate-token', methods=['POST'])
@limiter.limit("2 per minute")
def regenerate_token():
    try:
        token_id = request.json.get('id')
        if not token_id:
            app.logger.info('Regenerate token request with missing ID')
            return jsonify({'error': 'Token ID is required'}), 400

        token = APIToken.query.filter_by(id=token_id).first()
        if not token:
            app.logger.info(f'Token ID not found for regeneration: {token_id}')
            return jsonify({'error': 'Token ID not found'}), 404

        db.session.delete(token)
        db.session.commit()

        random_bytes = os.urandom(24)
        new_token_str = base64.b64encode(random_bytes).decode('utf-8')
        new_token = APIToken(id=token_id, token=new_token_str)
        db.session.add(new_token)
        db.session.commit()

        app.logger.info(f'Token regenerated successfully for ID: {token_id}')
        return jsonify({'new_token': new_token_str}), 200
    except Exception as e:
        app.logger.error(f"Error in regenerate-token: {e}")
        return jsonify({'error': 'Internal Server Error'}), 500

## Valid formats:
#{"localization": {
#    "zh-tw": "馬",
#    "en": "horse"}}
#Or
#{"text": "horse",
#"language": "en",
#"translations": ["zh-TW", "de"]}
@app.route('/generate-speech', methods=['POST'])
@require_token
@limiter.limit("10 per minute")
def generate_speech():
    data = request.json
    valid_languages_found = False

    try:
        combined_mp3 = io.BytesIO()

        if 'localization' in data:
            for lang_code, text in data['localization'].items():
                if lang_code in lang.tts_langs():
                    valid_languages_found = True
                    try:
                        tts = gTTS(text=text, lang=lang_code)
                        tts.write_to_fp(combined_mp3)
                    except Exception as e:
                        app.logger.error(f"Failed to generate speech for {lang_code}: {e}")

        elif 'text' in data and 'language' in data and 'translations' in data:
            original_text = data['text']
            original_lang = data['language']

            if original_lang not in lang.tts_langs():
                app.logger.info(f"Invalid primary language: {original_lang}")
                return jsonify({"error": "Primary language is invalid"}), 400

            valid_languages_found = True
            try:
                tts = gTTS(text=original_text, lang=original_lang)
                tts.write_to_fp(combined_mp3)
            except Exception as e:
                app.logger.error(f"Failed to generate speech for primary language {original_lang}: {e}")

            translator = Translator()
            for lang_code in data['translations']:
                if lang_code in lang.tts_langs():
                    try:
                        translation = translator.translate(original_text, src=original_lang, dest=lang_code)
                        translated_text = translation.text
                        app.logger.info(f"Translation to {lang_code}: {translated_text}")
                        tts = gTTS(text=translated_text, lang=lang_code)
                        tts.write_to_fp(combined_mp3)
                    except Exception as e:
                        app.logger.error(f"Failed to generate speech for {lang_code}: {e}")

        else:
            app.logger.error("Invalid JSON format received in generate-speech")
            return jsonify({"error": "Invalid JSON format"}), 400

        if not valid_languages_found:
            app.logger.info("No valid languages found in generate-speech request")
            tts = gTTS(text="No valid languages found", lang='en')
            tts.write_to_fp(combined_mp3)

        combined_mp3.seek(0)
        return send_file(combined_mp3, mimetype='audio/mpeg')

    except Exception as e:
        app.logger.error(f"Error in generate-speech: {e}")
        return jsonify({"error": "Text-to-Speech conversion failed", "details": str(e)}), 500

@app.route('/list-tokens', methods=['GET'])
@require_token
def list_tokens():
    try:
        tokens = APIToken.query.all()
        token_list = [{'id': token.id, 'token': token.token} for token in tokens]
        return jsonify(token_list), 200
    except Exception as e:
        app.logger.error(f"Error in list-tokens: {e}")
        return jsonify({"error": "Failed to retrieve tokens", "details": str(e)}), 500



