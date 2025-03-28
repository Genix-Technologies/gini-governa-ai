import os
from flask import Flask, request, jsonify, send_file
#import speech_recognition as sr
#from pydub import AudioSegment
import openai, json 
import requests
from flask import send_from_directory, render_template
import csv
import pandas as pd   

openai_api_key = os.getenv("OPENAI_API_KEY")

AUDIO_FOLDER = "audio_files"
#os.environ["OPENAI_API_KEY"] = openai_api_key
CSV_FILE_LIST = "file_dataset.csv"
VSTORE_ID = "vs_67e31b2e9d608191873d419b483bc1af"
VSTORE_NAME="GovernaAI"
ASSISTANT_ID = "asst_p5K27rbqbduOsrcadJtFDgkB"
UPLOAD_FOLDER = "uploaded_files/"
CSV_VOICE_FILE = "voice_records.csv"
CSV_FILE = "file_dataset.csv"
THREAD_FILE = "thread.json"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

if not os.path.exists(AUDIO_FOLDER):
    os.makedirs(AUDIO_FOLDER)

if not os.path.exists(CSV_VOICE_FILE):
    with open(CSV_VOICE_FILE, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["username", "transcribed_text", "filename", "timestamp"])

app = Flask(__name__,static_folder='static',template_folder='templates')

@app.route('/')
def home():
    # Renders index.html from the "templates" folder
    return render_template('index.html')

@app.route('/search-ai-input', methods=["POST"])
def searchAIInput():
    # Renders index.html from the "templates" folder
    try:
        data = request.json
        user_qry = data.get("user_query", "")
        if not user_qry:
            return jsonify({"status": "error", "message": "No query provided"}), 400
        
        #response_data = f"Searching for: {user_qry}" 
        response_data = get_openai_reply(user_qry)
        print(response_data)
        return jsonify({"status": "success", "data": response_data})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    

def load_uploaded_files():
    """Load and return the file list from the CSV."""
    if os.path.exists(CSV_FILE_LIST):
        try:
            filedf = pd.read_csv(CSV_FILE_LIST)
            filedf.columns = filedf.columns.str.strip()

            # Return the list if valid columns exist and the file is not empty
            if {"file_name", "file_id"}.issubset(filedf.columns) and not filedf.empty:
                return filedf[["file_name", "file_id"]].to_dict(orient="records")
        except Exception as e:
            print(f"Error reading CSV: {str(e)}")

    # Return empty list if no file or error
    return []

@app.route('/list_all_file', methods=['GET'])
def list_all_file():
    return jsonify({"status": "success", "data": load_uploaded_files()}), 200

@app.route('/upload_audio', methods=['POST'])
def upload_audio():
    if 'audio' not in request.files:
        return jsonify({"status": "error", "message": "No audio file provided"}), 400
    audio_file = request.files['audio']
    timestamp = int(time.time())
    audio_path = os.path.join(AUDIO_FOLDER, f"audio_{timestamp}.webm")
    # Save audio locally
    audio_file.save(audio_path)
    #recognized_text = process_audio(audio_path)
    transcribed_text = transcribe_audio(audio_path)
    if not transcribed_text:
        return jsonify({"error": "Error transcribing audio"}), 500
    
    openai_response = get_openai_reply(transcribed_text)
    print("Open AI response", openai_response)

    #timestamp = int(time.time())
    #unique_filename = f"{AUDIO_FOLDER}/response_{timestamp}.mp3"
    fileName = f"response_{timestamp}.mp3"
    unique_filename = os.path.join(AUDIO_FOLDER, fileName)
    tts_audio_path = generate_audio(str(openai_response), unique_filename, voice="alloy")
    if not tts_audio_path:
        return jsonify({"error": "Error generating audio"}), 500
    #save_record_to_csv("mainadmin", str(openai_response), unique_filename, timestamp)
    return jsonify({"status": True, "filename":fileName, "output_transcription":str(openai_response), "input_transcription":transcribed_text}), 200


def get_thread_id():
    if os.path.exists(THREAD_FILE):
        with open(THREAD_FILE, "r") as f:
            thread_data = json.load(f)
            return thread_data.get("thread_id")
    return None

def get_openai_reply(user_query):
    thread_id = get_thread_id()
    if user_query:
        #assistantid = create_assistant()
        #print(assistantid)
        #return assistantid
        #thread_id = create_thread(user_query)
        #print(threadid)
        #return threadid
        #return {}
        #Adds the user query to the thread.
        message_id = create_message(user_query,thread_id )
        #1. Run the Assistant After Adding a Message
        run_id = run_assistant( thread_id, ASSISTANT_ID)
        #2. Check Run Status Until Completion
        run_status = check_run_status( thread_id, run_id)
        #3. Retrieve Assistant’s Response
        if run_status:
            recent_messages = get_all_messages_from_thread(thread_id)
            
            msg_object = recent_messages
        if msg_object:
            return msg_object
        else:
            return None
    else:
        return None

def save_record_to_csv(username, transcribed_text, filename, timestamp):
    with open(CSV_FILE, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([username, transcribed_text, filename, timestamp])

def generate_audio(text, output_path, voice="coral"):
    """Generate audio using OpenAI's TTS API and save as MP3 using requests."""
    if text is None or len(text) == 0:
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
            #print(f"❌ Error generating audio. Status: {response.status_code}, Error: {response.text}")
            return None

    except Exception as e:
        #print(f"❌ Error during audio generation: {e}")
        return None
    

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
    audio_path = request.args.get("aud_path", None)
    
    if audio_path:
        audio_file_path = os.path.join(AUDIO_FOLDER, audio_path)
        print(audio_file_path)
        if os.path.exists(audio_file_path):
            return send_file(audio_file_path, mimetype="audio/mp3")
        else:
            return "❌ Audio file not found.", 404
    else:
        return "❗ Missing 'aud_path' parameter.", 400

import time

def create_message(query, thread_id):
    url = f"https://api.openai.com/v1/threads/{thread_id}/messages"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai_api_key}",
        "OpenAI-Beta": "assistants=v2"
    }
    # Message content to be added
    payload = {
        "role": "user",
        "content": query
    }
    try:
        # Send POST request to add the message
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response_data = response.json()

        if response.status_code == 200:
            print("✅ Message added successfully!")
            return response_data["id"] # Return the message ID
        else:
            print(f"❌ Failed to add message. Error: {response_data}")
            return None

    except Exception as e:
        print(f"⚠️ Error: {e}")
        return {"error": str(e)}
    


def run_assistant(thread_id, assistant_id):
    url = f"https://api.openai.com/v1/threads/{thread_id}/runs"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai_api_key}",
        "OpenAI-Beta": "assistants=v2"
    }
    payload = {
        "assistant_id": assistant_id
    }
    try:
        # Send POST request to run the assistant
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response_data = response.json()

        if response.status_code == 200:
            print("✅ Assistant run initiated successfully!")
            return response_data["id"]  # Return the run ID
        else:
            print(f"❌ Failed to run assistant. Error: {response_data}")
            return None

    except Exception as e:
        print(f"⚠️ Error while running assistant: {e}")
        return {"error": str(e)}
    
def check_run_status(thread_id, run_id):
    """
    Checks the status of the assistant run until it's completed.
    """
    url = f"https://api.openai.com/v1/threads/{thread_id}/runs/{run_id}"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai_api_key}",
        "OpenAI-Beta": "assistants=v2"
    }

    while True:
        response = requests.get(url, headers=headers)
        response_data = response.json()

        if response.status_code == 200:
            status = response_data["status"]
            print(f"⏳ Run Status: {status}")

            if status == "completed":
                print("✅ Run completed successfully!")
                return True
            elif status in ["failed", "cancelled"]:
                print(f"❌ Run failed or was cancelled. Status: {status}")
                return False
            else:
                time.sleep(2)  # Wait and check again
        else:
            print(f"⚠️ Failed to check run status. Error: {response_data}")
            return False
        
def get_all_messages_from_thread(thread_id):
    """
    Retrieves all messages from the thread after run completion.
    """
    url = f"https://api.openai.com/v1/threads/{thread_id}/messages?limit=3&order=desc"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai_api_key}",
        "OpenAI-Beta": "assistants=v2"
    }

    response = requests.get(url, headers=headers)
    response_data = response.json()

    if response.status_code == 200:
        messages = response_data["data"]
        # Extract latest assistant message
        assistant_response = [
            msg["content"] for msg in messages if msg["role"] == "assistant"
        ]
        if assistant_response:
            # Print raw assistant response for debugging
            print("Full Assistant Response:", assistant_response[0])
            # Check if assistant_response is a list and contains messages
                    # Call extract_assistant_response to get the actual text content
            for msg in assistant_response[0]:
                print("Single message ",msg)
                if msg["type"] == "text" and "text" in msg:
                    return msg["text"]["value"]
        else:
            return "❌ No response received from the assistant."
        
    else:
        print(f"⚠️ Failed to retrieve messages. Error: {response_data}")
        return None
    

def get_message_from_thread(openai_api_key, thread_id, message_id):

    #url = f"https://api.openai.com/v1/threads/{thread_id}/messages/{message_id}"
    url = f"https://api.openai.com/v1/threads/{thread_id}/messages"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai_api_key}",
        "OpenAI-Beta": "assistants=v2"
    }
    try: 
        # Send GET request to retrieve the message
        response = requests.get(url, headers=headers)
        response_data = response.json()

        if response.status_code == 200:
            print("✅ Message retrieved successfully!")
            return response_data
        else:
            print(f"❌ Failed to retrieve message. Error: {response_data}")
            return response_data

    except Exception as e:
        print(f"⚠️ Error: {e}")
        return {"error": str(e)}
    
#def research_agent(query):
#    doc_context = "\n---\n".join(st.session_state.document_context.values()) if st.session_state.document_context else ""
 #   enhanced_query = f"Based on the following documents:\n{doc_context}\n\nAnswer the following question:\n{query}"
  #  try:
   #     response = openai.ChatCompletion.create(
    #        model="gpt-3.5-turbo",
     #       messages=[
      #          {"role": "system", "content": "You are an AI research agent assisting board members. Use the provided document context to inform your answer."},
       #         {"role": "user", "content": enhanced_query}
        #    ]
        #)
        #return response["choices"][0]["message"]["content"]
    #except Exception as e:
     #   return f"⚠ Error contacting OpenAI: {e}"

#---Create assistant
def update_thread_id(thread_id):
    thread_data = {"thread_id": thread_id}
    with open(THREAD_FILE, "w") as f:
        json.dump(thread_data, f, indent=4)
    print(f"✅ Thread ID updated in thread.json: {thread_id}")

def create_thread(user_qry):
    url = "https://api.openai.com/v1/threads"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai_api_key}",
        "OpenAI-Beta": "assistants=v2"
    }
    initial_message = {
        "role": "user",
        "content": user_qry
    }
    tool_resources = {
        "file_search": {
            "vector_store_ids": [VSTORE_ID]
        }
    }
    payload = {
        "messages": [initial_message],
        "tool_resources": tool_resources
    }

    try:
        # Sending an empty payload to create a thread
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response_data = response.json()
        if response.status_code == 200:
            thread_id = response_data.get("id")
            print(f"✅ Thread created successfully. Thread ID: {thread_id}")
            update_thread_id(thread_id)
            return thread_id
        else:
            print(f"❌ Failed to create thread. Error: {response_data}")
            return None

    except Exception as e:
        print(f"⚠️ Error: {e}")
        return {"error": str(e)}



def create_assistant():
   
    url = "https://api.openai.com/v1/assistants"
    
    headers = {
        "Authorization": f"Bearer {openai_api_key}",
        "Content-Type": "application/json",
        "OpenAI-Beta": "assistants=v2"
    }

    assistant_data = {
        "name": "Boardroom Research Assistant",
        "instructions": (
            "Give only text content that needs to be works in voice input, do not add any special characters or emojis or html codes."
            "You are an AI assistant that helps board members by answering questions "
            "based on uploaded meeting documents. Retrieve relevant information from the vector store "
            "and provide concise, accurate responses."
            "Also consider this -- Board of Director Meeting Agenda March 27, 2025 ⋅ 10:30pm --10:30pm: Call to Order & Approvals"
            "--10:35pm: Review Open Pre-Read Comments"
            "--11:00pm: CEO Summary"
            "--11:15pm: Deep Dive 1: Embracing AI in Product Design"
            "--11:45pm: Deep Dive 2: Digital Distribution"
        ),
        "model": "gpt-4o-mini",  # You can use gpt-3.5-turbo if needed
        "tools": [{"type": "file_search"}] #, "vector_store_ids": [VSTORE_ID]}
    }

    # Send POST request to create the assistant
    response = requests.post(url, headers=headers, json=assistant_data)
    response_json = response.json()

    if response.status_code == 200:
        assistant_id = response_json["id"]
        print(f"✅ Assistant created successfully! Assistant ID: {assistant_id}")
        return assistant_id
    else:
        print(f"❌ Failed to create assistant. Error: {response_json}")
        return None
    

@app.route('/upload_file', methods=['POST'])
def process_upload():
    try:
        if "file" not in request.files:
            return jsonify({"status": "error", "message": "No file part"})
        files = request.files.getlist("file")

        for file in files:
            if file.filename == "":
                return jsonify({"status": "error", "message": "No selected file"})
            file_path = os.path.join(UPLOAD_FOLDER,  file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, file.filename))
        
     
            # --- Upload File to OpenAI ---
            upload_url = "https://api.openai.com/v1/files"
            headers = {
                "Authorization": f"Bearer {openai_api_key}"
            }
            with open(file_path, "rb") as file_to_upload:
                files = {
                    "file": (os.path.basename(file_path), open(file_path, "rb")),
                    "purpose": (None, "assistants")
                }
                upload_response = requests.post(upload_url, headers=headers, files=files)
            upload_response_json = upload_response.json()

            if upload_response.status_code != 200:
                return jsonify({"status": "error", "message": f"Failed to upload file to OpenAI: {upload_response_json.get('error', 'Unknown error')}"})
            
            file_id = upload_response_json.get("id")
            save_to_csv( file.filename, file_id)
            #time.sleep(2)
            # --- Link File to Vector Store ---
            link_url = f"https://api.openai.com/v1/vector_stores/{VSTORE_ID}/files"
            link_data = {"file_id": file_id}
            link_headers = {
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json",
                "OpenAI-Beta": "assistants=v2"
            }

            link_response = requests.post(link_url, headers=link_headers, json=link_data)
            link_response_json = link_response.json()
            if link_response.status_code == 200 :
                create_thread("Hi")
                return jsonify({"status": "success", "message": "📚 Files uploaded and linked to KE successfully!"})
            else:
                return jsonify({"status": "failure", "message": "⚠️ Failed to link file to KE."})

    except Exception as e:
        return None


@app.route("/delete_file/<file_id>", methods=["DELETE"])
def delete_file(file_id):
    """Delete a file using its file ID."""
    if not file_id:
        return jsonify({"error": "File ID is required."}), 400

    document_context = load_uploaded_files()
    file_name_to_delete = None

    # ✅ Find the file name by its file_id
    for item in document_context:
        if item["file_id"] == file_id:
            file_name_to_delete = item["file_name"]
            break

    # ✅ If file not found
    if not file_name_to_delete:
        return jsonify({"status":False, "message": "File not found in document context."}), 404

    # ✅ Try to delete file from OpenAI
    if delete_from_openai(file_id):
        update_csv_after_delete(file_name_to_delete)
        create_thread("Hi")
        return jsonify({"status":True, "message": f"❌ Deleted file: {file_name_to_delete}"})

    return jsonify({"status":False, "message": "⚠️ Unable to delete file from OpenAI. Please try again."}), 500
    

def update_csv_after_delete(file_name_to_delete):
    """Update CSV after file deletion."""
    df = pd.read_csv(CSV_FILE)
    df = df[df["file_name"] != file_name_to_delete]
    df.to_csv(CSV_FILE, index=False)

def delete_from_openai(file_id):
    """Delete a file from OpenAI vector store using file_id."""
    try:
        #st.info(f"⏳ Deleting file from OpenAI: {file_id}")
        delete_url = f"https://api.openai.com/v1/files/{file_id}"
        headers = {
            "Authorization": f"Bearer {openai_api_key}"
        }
        #st.info(delete_url)
        response = requests.delete(delete_url, headers=headers)
        if response.status_code == 200:
            print(f"✅ File successfully reemoved from KE.")
            return True
        else:
            print(f"❌ Failed to remove file from OpenAI. Error: {response.json()}")
            return False
    except Exception as e:
        print(f"❌ Error removing file from KE: {str(e)}")
        return False

def save_to_csv(file_name, file_id):
    file_exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, mode="a", newline="") as csv_file:
        csv_writer = csv.writer(csv_file)
        if not file_exists:
            writer.writerow(["file_name", "file_id","modified"])
        csv_writer.writerow([file_name, file_id, time.strftime("%Y-%m-%d %H:%M:%S")])

    print(f"✅ File info saved to CSV: {file_name} | File ID: {file_id}")


def check_file_status(file_id):
    for _ in range(10):  # Check status for 10 seconds
        file_info = openai.File.retrieve(file_id)
        status = file_info["status"]
        print(f"⏳ File status: {status}")

        if status == "processed":
            print("✅ File processed and ready!")
            return True
        time.sleep(1)
    print("❌ File not processed in time. Try again.")
    return False


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8501, debug=True)
