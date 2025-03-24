import os
from flask import Flask, request, jsonify, send_file, render_template_string
#import speech_recognition as sr
#from pydub import AudioSegment
import openai, json 
import requests
from flask import send_from_directory


openai_api_key = os.getenv("OPENAI_API_KEY")

AUDIO_FOLDER = "audio_files"
if not os.path.exists(AUDIO_FOLDER):
    os.makedirs(AUDIO_FOLDER)

app = Flask(__name__)


@app.route('/upload_audio', methods=['POST'])
def upload_audio():
    """Receive and save audio from frontend."""
    if 'audio' not in request.files:
        return jsonify({"status": "error", "message": "No audio file provided"}), 400
    audio_file = request.files['audio']
    audio_path = os.path.join(AUDIO_FOLDER, "audio.webm")
    # Save audio locally
    audio_file.save(audio_path)
    #recognized_text = process_audio(audio_path)
    transcribed_text = transcribe_audio(audio_path)
    if not transcribed_text:
        return jsonify({"error": "Error transcribing audio"}), 500

    tts_audio_path = generate_audio(transcribed_text, "response.mp3", voice="alloy")
    if not tts_audio_path:
        return jsonify({"error": "Error generating audio"}), 500

    # Step 3: Return HTML with an audio player
    return render_template_string(generate_html(transcribed_text, os.getenv("FLASK_URL")+"/response.mp3"))

 

def transcribe_audio(audio_path):
    try:
        url = "https://api.openai.com/v1/audio/transcriptions"
        headers = {
            "Authorization": f"Bearer {openai_api_key}",
        }
        # Prepare the audio file to be sent
        with open(audio_path, "rb") as audio_file:
            files = {
                "file": audio_file,
                "model": (None, "whisper-1"),
                "language": (None, "en")  # Change language if needed
            }
            response = requests.post(url, headers=headers, files=files)
        print(response.text)
        if response.status_code == 200:
            transcription_result = json.loads(response.text) 
            return transcription_result.get("text", "No transcription available.")
        else:
            print(f"❌ Error transcribing audio. Status: {response.status_code}, Error: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error during audio transcription: {e}")
        return None
    

@app.route('/response.mp3', methods=['GET'])
def get_audio():
    #return send_from_directory(".", "response.mp3")
    return send_file("../response.mp3", mimetype="audio/mp3")

def generate_audio(text, output_path="response.mp3", voice="coral"):
    """Generate audio using OpenAI's TTS API and save as MP3 using requests."""
    #if text is None or len(text) == 0:
    text = "Am not clear about the context."
    try:
        url = "https://api.openai.com/v1/audio/speech"

        headers = {
            "Authorization": f"Bearer {openai_api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "gpt-4o-mini-tts",  # Correct TTS model
            "input": text,
            "voice": voice,  # Voices: alloy, echo, fable, onyx, nova, shimmer, coral
            "instructions": "Speak in a cheerful and positive tone."
        }

        # Make POST request
        response = requests.post(url, headers=headers, data=json.dumps(data))

        # Check if the request was successful
        if response.status_code == 200:
            # Save the audio file as MP3
            with open(output_path, "wb") as audio_file:
                audio_file.write(response.content)
            print(f"✅ Audio successfully generated and saved as {output_path}")
            return output_path
        else:
            print(f"❌ Error generating audio. Status: {response.status_code}, Error: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Error during audio generation: {e}")
        return None


def generate_html(transcribed_text, audio_path):
    return f"""<p><strong>Transcription:</strong> {transcribed_text}</p>
        <div id="audio-container">
            <audio controls>
                <source src="{audio_path}" type="audio/mp3">
                Your browser does not support the audio element.
            </audio>
        </div>"""


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8502, debug=False)
