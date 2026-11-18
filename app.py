import os
import requests
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder='public', static_url_path='')
MAX_TEXT_LENGTH = 5000

@app.get('/')
def home():
    return send_from_directory('public', 'index.html')

@app.get('/api/health')
def health():
    return jsonify({'status': 'ok', 'service': 'language-translation-tool'})

@app.get('/api/languages')
def languages():
    base_url = os.getenv('LIBRETRANSLATE_URL', 'https://libretranslate.com').rstrip('/')
    try:
        response = requests.get(f'{base_url}/languages', timeout=15)
        response.raise_for_status()
        return jsonify(response.json())
    except requests.RequestException:
        return jsonify({'error': 'Could not load languages from the translation provider.'}), 502

@app.post('/api/translate')
def translate():
    data = request.get_json(silent=True) or {}
    text = str(data.get('text', '')).strip()
    source = str(data.get('source', 'auto')).strip()
    target = str(data.get('target', '')).strip()

    if not text:
        return jsonify({'error': 'Please enter some text to translate.'}), 400
    if len(text) > MAX_TEXT_LENGTH:
        return jsonify({'error': f'Please keep the text under {MAX_TEXT_LENGTH} characters.'}), 400
    if not target:
        return jsonify({'error': 'Please choose a target language.'}), 400

    base_url = os.getenv('LIBRETRANSLATE_URL', 'https://libretranslate.com').rstrip('/')
    payload = {'q': text, 'source': source, 'target': target, 'format': 'text'}
    api_key = os.getenv('LIBRETRANSLATE_API_KEY')
    if api_key:
        payload['api_key'] = api_key

    try:
        response = requests.post(
            f'{base_url}/translate', json=payload,
            headers={'Content-Type': 'application/json'}, timeout=25
        )
        if response.status_code == 401 or response.status_code == 403:
            return jsonify({'error': 'The translation provider requires a valid API key. Add LIBRETRANSLATE_API_KEY in Vercel Environment Variables.'}), 502
        response.raise_for_status()
        result = response.json()
        return jsonify({
            'translatedText': result.get('translatedText', ''),
            'detectedLanguage': result.get('detectedLanguage', {}).get('language', source if source != 'auto' else 'Unknown'),
            'confidence': result.get('detectedLanguage', {}).get('confidence')
        })
    except requests.Timeout:
        return jsonify({'error': 'The translation service took too long. Please try again.'}), 504
    except requests.RequestException as exc:
        detail = ''
        if getattr(exc, 'response', None) is not None:
            try:
                detail = exc.response.json().get('error', '')
            except Exception:
                detail = ''
        return jsonify({'error': detail or 'Translation service is temporarily unavailable. Check your API URL and key.'}), 502

if __name__ == '__main__':
    app.run(debug=True)
