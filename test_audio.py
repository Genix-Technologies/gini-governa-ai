import os
import streamlit as st
import openai
import docx
import PyPDF2
from io import BytesIO
import speech_recognition as sr

# Set OpenAI API Key from environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

# ---------- Helper Functions ----------

def load_content(file_name, default_text=""):
    return default_text

# Sample static meeting agenda and content
meeting_agenda_content = """
**Board of Director Meeting Agenda**  
**March 27, 2025 ⋅ 10:30pm**  
We will be meeting via Zoom.

- **10:30pm:** Call to Order & Approvals  
- **10:35pm:** Review Open Pre-Read Comments  
- **11:00pm:** CEO Summary  
- **11:15pm:** Deep Dive 1: Embracing AI in Product Design  
- **11:45pm:** Deep Dive 2: Digital Distribution  
- **Close**
"""

pre_read_info_content = """
**Before the Meeting, Please:**  
- Review the Proposed Meeting Agenda  
- Check the Votes that will be taken and consider pre-voting on key points  
- Read all Pre-Read sections and add your comments in advance (use the Comments button)
"""

voting_info_content = """
Key voting topics include:  
- Pre-Vote on the proposed agenda items  
- Review of key pre-read documents  
Please review the documents and cast your vote accordingly.
"""

# Function to extract context from uploaded documents (PDF, DOCX, TXT)
def get_uploaded_documents_context(uploaded_files):
    context = {}
    if uploaded_files:
        for uploaded_file in uploaded_files:
            file_name = uploaded_file.name.lower()
            file_text = ""
            if file_name.endswith('.docx'):
                try:
                    document = docx.Document(BytesIO(uploaded_file.read()))
                    for para in document.paragraphs:
                        file_text += para.text + "\n"
                except Exception as e:
                    st.warning(f"Could not read {uploaded_file.name}: {e}")
            elif file_name.endswith('.pdf'):
                try:
                    pdf_reader = PyPDF2.PdfReader(uploaded_file)
                    for page in pdf_reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            file_text += page_text + "\n"
                except Exception as e:
                    st.warning(f"Could not read {uploaded_file.name}: {e}")
            else:
                try:
                    file_text = uploaded_file.read().decode("utf-8")
                except Exception as e:
                    st.warning(f"Could not read {uploaded_file.name}. Only text-based files are supported.")
            
            context[file_name] = file_text
    return context

# Function to query OpenAI with the given query and document context
def ask_openai(query, document_context):
    messages = [
        {
            "role": "system", 
            "content": f"You are a board meeting assistant for Governa. Use the following context from uploaded documents to help answer questions:\n\n{document_context}"
        },
        {"role": "user", "content": query}
    ]
    try:
        response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages)
        answer = response['choices'][0]['message']['content']
        return answer
    except Exception as e:
        return f"Error contacting OpenAI: {e}"

# Function for annotating the document content (inline comments or highlighting)
def annotate_document(file_name, document_content):
    st.text_area(f"Annotations for {file_name}", document_content, height=200)

# ---------- Main App UI ----------

def main():
    # Initialize session state variables if not already present
    if "document_context" not in st.session_state:
        st.session_state.document_context = {}
    if "annotations" not in st.session_state:
        st.session_state.annotations = {}
    if "transcript" not in st.session_state:
        st.session_state.transcript = ""  # Initialize transcript as an empty string

    st.set_page_config(page_title="Governa Board Meeting Assistant", layout="wide")

    # Custom CSS for enhanced look
    st.markdown("""
    <style>
    .agenda-item {border: 1px solid #ddd; padding: 10px; margin-bottom: 10px; border-radius: 8px; background-color: #f8f9fa;}
    .agenda-header {font-size: 18px; font-weight: bold; color: #333;}
    .stButton>button {background-color: #007bff; color: white; border: none; padding: 0.5rem 1rem; border-radius: 5px;}
    </style>
    """, unsafe_allow_html=True)
    
    # Display meeting title and agenda
    st.title("Governa Board Meeting Assistant")
    st.header("Upcoming Board Meeting Details")
    st.markdown(meeting_agenda_content)
    st.markdown("---")
    st.subheader("Pre-Reads & Voting Information")
    st.markdown(pre_read_info_content)
    st.markdown(voting_info_content)
    st.markdown("---")
    
    # Use tabs for main functionality
    tabs = st.tabs(["Upload Documents", "Conversation", "Meeting Transcription", "Voting"])

    # ---------- Upload Documents Tab ----------
    with tabs[0]:
        st.subheader("Upload Documents for Meeting Context")
        uploaded_files = st.file_uploader(
            "Upload documents (PDF, DOCX, TXT, etc.)", 
            type=['pdf', 'docx', 'txt'], 
            accept_multiple_files=True
        )
        if uploaded_files:
            context = get_uploaded_documents_context(uploaded_files)
            st.session_state.document_context = context
            st.success("Documents uploaded and context set successfully!")
            
            # Display document content and allow for annotations
            for file_name, content in context.items():
                st.write(f"### {file_name}")
                annotate_document(file_name, content)
        else:
            st.info("No documents uploaded yet.")

    # ---------- Conversation Tab ----------
    with tabs[1]:
        st.subheader("Start a Conversation")
        document_context = st.session_state.get("document_context", "")
        if document_context:
            st.info("Using uploaded documents as conversation context.")
        else:
            st.warning("No document context available. Please upload documents first.")
        
        input_method = st.radio("Choose input method:", options=["Text Input", "Voice Input (Record)"])
        user_query = ""
        if input_method == "Text Input":
            user_query = st.text_input("Enter your query here:")
        
        if st.button("Submit Query"):
            if user_query:
                with st.spinner("Contacting OpenAI..."):
                    answer = ask_openai(user_query, document_context)
                    st.markdown("### Response")
                    st.write(answer)
            else:
                st.error("Please enter a query before submitting.")

    # ---------- Meeting Transcription Tab ----------
    with tabs[2]:
        st.subheader("Meeting Transcription")
        st.markdown("Record short audio clips externally (using your preferred recorder) and upload them (WAV format) to build a meeting transcript. You can then ask for a summary.")
        
        audio_clip = st.file_uploader("Upload an audio clip (WAV) for transcription", type=["wav"])
        if audio_clip is not None:
            recognizer = sr.Recognizer()
            try:
                with sr.AudioFile(audio_clip) as source:
                    audio_data = recognizer.record(source)
                clip_text = recognizer.recognize_google(audio_data)
                st.session_state.transcript += clip_text + "\n"
                st.success("Audio clip processed and added to transcript!")
            except Exception as e:
                st.error(f"Error processing audio clip: {e}")
        
        st.text_area("Meeting Transcript", st.session_state.transcript, height=200)

        if st.button("Summarize Transcript"):
            if st.session_state.transcript.strip():
                summary_query = "Summarize the following meeting transcript: " + st.session_state.transcript
                with st.spinner("Summarizing transcript..."):
                    summary = ask_openai(summary_query, "")
                    st.markdown("### Transcript Summary")
                    st.write(summary)
            else:
                st.error("No transcript available to summarize.")

    # ---------- Voting Tab ----------
    with tabs[3]:
        st.header("Board Voting (Advanced)")
        st.markdown("Please cast your vote on the following questions:")

        questions = [
            {
                "question": "Do you approve the proposed meeting agenda?",
                "options": ["Yes", "No", "Abstain"]
            },
            {
                "question": "Do you support the implementation of AI in Product Design?",
                "options": ["Yes", "No", "Needs more information", "Abstain"]
            },
            {
                "question": "Should we approve the proposed digital distribution strategy?",
                "options": ["Yes", "No", "Abstain"]
            }
        ]
        
        votes = {}
        for q in questions:
            votes[q['question']] = st.radio(q['question'], options=q['options'], key=q['question'])
        
        if st.button("Submit Votes"):
            st.success("Thank you for voting!")
            st.write("### Your Votes:")
            for question, vote in votes.items():
                st.write(f"**{question}**: {vote}")
            
            st.write("### Voting Results:")
            for q in questions:
                st.write(f"{q['question']} - Option {votes[q['question']]}")
                st.progress(50)  # Mock progress to represent voting results

if __name__ == "__main__":
    main()
