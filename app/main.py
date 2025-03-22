import os
import streamlit as st
import openai
import docx2txt
import PyPDF2
from io import BytesIO
import random
import time
import speech_recognition as sr  # For speech-to-text
from gtts import gTTS           # For text-to-speech
import pandas as pd             # For tabular display

# ------------------- CONFIGURATION & SESSION INITIALIZATION ------------------- #

openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    st.error("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
    st.stop()  # Stop execution if API key is missing
os.environ["OPENAI_API_KEY"] = openai_api_key

# Initialize session states
if "document_context" not in st.session_state:
    st.session_state.document_context = {}
if "annotations" not in st.session_state:
    st.session_state.annotations = {}
if "comments" not in st.session_state:
    st.session_state.comments = {}
if "votes" not in st.session_state:
    st.session_state.votes = {}
if "meeting_transcript" not in st.session_state:
    st.session_state.meeting_transcript = ""
if "live_summary" not in st.session_state:
    st.session_state.live_summary = ""
if "action_items" not in st.session_state:
    st.session_state.action_items = []  # Initialize as an empty list
if "selected_annotation" not in st.session_state:
    st.session_state.selected_annotation = None

# ---------- Document Processing ----------
def extract_text_from_file(uploaded_file):
    """Extracts text from DOCX, PDF, or TXT files."""
    file_name = uploaded_file.name.lower()
    file_text = ""
    try:
        if file_name.endswith('.docx'):
            file_text = docx2txt.process(uploaded_file)
        elif file_name.endswith('.pdf'):
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            file_text = "\n".join(
                [page.extract_text() for page in pdf_reader.pages if page.extract_text()]
            )
        else:
            file_text = uploaded_file.read().decode("utf-8")
    except Exception as e:
        st.warning(f"⚠ Could not read {uploaded_file.name}: {e}")
    return file_text

# ---------- Speech-to-Text ----------
def record_audio():
    """Records audio and returns the recognized text."""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("🎙️ Recording... Please speak into your microphone.")
        recognizer.adjust_for_ambient_noise(source)  # Optional to improve accuracy
        #audio_data = recognizer.listen(source)
        audio_data = recognizer.listen(source, phrase_time_limit=30)
    try:
        st.info(audio_data)
        query_text = recognizer.recognize_google(audio_data)
        st.success(f"You said: {query_text}")
        return query_text
    except Exception as e:
        st.error(f"⚠ Could not process the audio: {e}")
        return ""

# ---------- Text-to-Speech ----------
def speak_text(text):
    """
    Converts text to speech using gTTS and plays it in the browser.
    This uses a BytesIO buffer and st.audio (which uses JavaScript in the browser).
    """
    try:
        tts = gTTS(text=text, lang='en')
        audio_bytes = BytesIO()
        tts.write_to_fp(audio_bytes)
        audio_bytes.seek(0)
        st.audio(audio_bytes, format='audio/mp3')
    except Exception as e:
        st.warning(f"Voice output failed: {e}")

# ---------- Document Annotation (HTML based) ----------
def display_annotated_document(file_name, document_content):
    """
    Displays the document content (paragraphs) with an option to highlight
    and add comments for each paragraph. Layout is vertical to avoid nested columns.
    """
    st.subheader(f"📖 Document: {file_name}")
    paragraphs = document_content.split("\n")

    # Build HTML representation for display
    annotated_html = []
    for i, para in enumerate(paragraphs):
        section_number = i + 1
        is_highlighted = False
        if file_name in st.session_state.annotations:
            for ann in st.session_state.annotations[file_name]:
                if ann["section"] == section_number:
                    is_highlighted = True
                    break

        annotation_id = f"{file_name}_section_{section_number}"
        if is_highlighted:
            annotated_html.append(f'<mark id="{annotation_id}">{para}</mark>')
        else:
            annotated_html.append(f'<p id="{annotation_id}">{para}</p>')

    # Display the full text with any highlights
    st.markdown("".join(annotated_html), unsafe_allow_html=True)

    # Now provide vertical controls for each paragraph
    for i, para in enumerate(paragraphs):
        section_number = i + 1
        st.markdown("---")
        st.write(f"**Paragraph {section_number}:** {para}")

        # Check if paragraph is currently highlighted
        current_highlight = False
        if file_name in st.session_state.annotations:
            for ann in st.session_state.annotations[file_name]:
                if ann["section"] == section_number:
                    current_highlight = True
                    break

        # Retrieve current comment if any
        current_comment = ""
        if file_name in st.session_state.comments:
            for com in st.session_state.comments[file_name]:
                if com["section"] == section_number:
                    current_comment = com["comment"]
                    break

        # Let the user highlight/unhighlight
        highlight_label = "Remove Highlight" if current_highlight else "Highlight"
        if st.button(highlight_label, key=f"btn_highlight_{file_name}_{i}"):
            if current_highlight:
                # Remove the existing highlight
                st.session_state.annotations[file_name] = [
                    a for a in st.session_state.annotations[file_name] 
                    if a["section"] != section_number
                ]
            else:
                # Add a new highlight
                if file_name not in st.session_state.annotations:
                    st.session_state.annotations[file_name] = []
                st.session_state.annotations[file_name].append({
                    "section": section_number,
                    "highlighted_text": para
                })
            st.experimental_rerun()

        # Let the user add/edit comments
        comment_label = f"Add/Update Comment for Paragraph {section_number}"
        new_comment = st.text_area(comment_label, value=current_comment, key=f"comment_area_{file_name}_{i}")
        if st.button("Save Comment", key=f"btn_save_comment_{file_name}_{i}"):
            if file_name not in st.session_state.comments:
                st.session_state.comments[file_name] = []
            st.session_state.comments[file_name] = [
                c for c in st.session_state.comments[file_name] 
                if c["section"] != section_number
            ]
            if new_comment.strip():
                st.session_state.comments[file_name].append({
                    "section": section_number,
                    "comment": new_comment.strip()
                })
            st.experimental_rerun()

# ---------- Annotation Summary ----------
def display_annotation_summary(file_name):
    """Displays a summary of annotations for the given file."""
    st.subheader("📝 Annotation Summary")
    if file_name in st.session_state.annotations or file_name in st.session_state.comments:
        all_annotations = []  # Initialize list
        # Gather highlight info
        if file_name in st.session_state.annotations:
            for ann in st.session_state.annotations[file_name]:
                all_annotations.append({
                    "type": "Highlight",
                    "section": ann["section"],
                    "text": ann["highlighted_text"],
                    "comment": ""
                })
        # Gather comment info
        if file_name in st.session_state.comments:
            for comment in st.session_state.comments[file_name]:
                is_highlighted = any(
                    ann["section"] == comment["section"] for ann in st.session_state.annotations.get(file_name, [])
                )
                if not is_highlighted:
                    document_content = st.session_state.document_context.get(file_name, "")
                    paragraphs = document_content.split("\n")
                    if comment["section"] - 1 < len(paragraphs):
                        section_text = paragraphs[comment["section"] - 1]
                    else:
                        section_text = "N/A"
                    all_annotations.append({
                        "type": "Comment",
                        "section": comment["section"],
                        "text": section_text,
                        "comment": comment["comment"]
                    })
                else:
                    for ann in all_annotations:
                        if ann["type"] == "Highlight" and ann["section"] == comment["section"]:
                            ann["comment"] = comment["comment"]
                            break

        if all_annotations:
            df_annotations = pd.DataFrame(all_annotations)
            st.dataframe(df_annotations)
        else:
            st.info("No annotations or comments yet.")
    else:
        st.info("No annotations or comments yet for this document.")

# ---------- Research Agent ----------
def research_agent(query):
    """
    Processes a research query and returns AI-generated insights.
    The query is enhanced with the content of all uploaded documents to provide context.
    """
    # Combine all document texts as context
    doc_context = "\n---\n".join(st.session_state.document_context.values()) if st.session_state.document_context else ""
    enhanced_query = f"Based on the following documents:\n{doc_context}\n\nAnswer the following question:\n{query}"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an AI research agent assisting board members. Use the provided document context to inform your answer."},
                {"role": "user", "content": enhanced_query}
            ]
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        return f"⚠ Error contacting OpenAI: {e}"

# ---------- Voting Dashboard Functions ----------
def simulate_voting_with_user(voting_questions, user_votes, num_simulated=10):
    """
    Combine the user's vote with simulated votes from other board members.
    Returns a DataFrame with board members as rows and questions as columns.
    """
    data = {}
    data["You"] = {q: user_votes.get(q, "Abstain") for q in voting_questions}
    for i in range(1, num_simulated + 1):
        member_name = f"Board Member {i}"
        data[member_name] = {q: random.choice(["Yes", "No", "Abstain"]) for q in voting_questions}
    df = pd.DataFrame(data).T
    return df

def calculate_dashboard_stats(df):
    """
    Calculate aggregated statistics for each voting question from the DataFrame.
    Returns a dictionary mapping question -> stats.
    """
    stats = {}
    for question in df.columns:
        counts = df[question].value_counts().to_dict()
        yes_count = counts.get("Yes", 0)
        no_count = counts.get("No", 0)
        abstain_count = counts.get("Abstain", 0)
        final_motion = "Motion Passed" if yes_count > no_count else "Motion Failed"
        stats[question] = {
            "Yes": yes_count,
            "No": no_count,
            "Abstain": abstain_count,
            "Final Motion": final_motion
        }
    return stats

def display_voting_dashboard(df, stats):
    """Display the voting dashboard including the DataFrame and aggregated statistics."""
    st.subheader("📊 Voting Dashboard")
    st.dataframe(df)
    st.markdown("---")
    st.subheader("🏆 Aggregated Voting Statistics")
    for question, s in stats.items():
        st.write(f"**{question}**")
        st.write(f"  - Yes: {s['Yes']}")
        st.write(f"  - No: {s['No']}")
        st.write(f"  - Abstain: {s['Abstain']}")
        st.write(f"  - Final Motion: {s['Final Motion']}")
        st.markdown("---")

# ---------- Live Meeting Analysis (Simulated) ----------
def transcribe_audio(new_text):
    """Simulates transcription by appending new speech to the meeting transcript."""
    st.session_state.meeting_transcript += f"{new_text}\n"

def generate_live_summary(transcript):
    """Simulates live summary generation by taking the first 200 characters of the transcript."""
    st.session_state.live_summary = transcript[:200] + "..."

def extract_action_items(transcript):
    """Simulates action item extraction from the transcript."""
    items = [line.strip() for line in transcript.split("\n") if "action" in line.lower()]
    st.session_state.action_items = items

# ---------- Main App with Board Portal Layout ----------
def main():
    st.set_page_config(page_title="Governa Board Portal", layout="wide")
    st.title("Governa Board Portal")
    if "mic_permission" not in st.session_state:
        mic_access = request_microphone_permission()
        st.session_state.mic_permission = mic_access
        
    # Two-column layout: Main Workspace and Insights Panel
    main_col, insights_col = st.columns([3, 1])

    with main_col:
        st.header("Meeting Dashboard")
        st.markdown("### Meeting Agenda")
        st.markdown("""
**Board of Director Meeting Agenda**
**March 27, 2025 ⋅ 10:30pm**
- **10:30pm:** Call to Order & Approvals
- **10:35pm:** Review Open Pre-Read Comments
- **11:00pm:** CEO Summary
- **11:15pm:** Deep Dive 1: Embracing AI in Product Design
- **11:45pm:** Deep Dive 2: Digital Distribution
- **Close**
        """)

        dashboard_tabs = st.tabs([
            "📂 Upload Documents", 
            "📝 Annotate & Review", 
            "🔍 Research Agent", 
            "🎙 AI Chat", 
            "🗳 Voting", 
            "💬 Comments", 
            "⏱️ Live Meeting Analysis"
        ])

        # --- Upload Documents ---
        with dashboard_tabs[0]:
            st.subheader("Upload Board Documents")
            uploaded_files = st.file_uploader(
                "Upload meeting documents (PDF, DOCX, TXT)",
                type=['pdf', 'docx', 'txt'],
                accept_multiple_files=True
            )
            if uploaded_files:
                for uploaded_file in uploaded_files:
                    file_text = extract_text_from_file(uploaded_file)
                    st.session_state.document_context[uploaded_file.name] = file_text
                st.success("Documents uploaded successfully!")

        # --- Annotate & Review ---
        with dashboard_tabs[1]:
            st.subheader("Annotate Meeting Documents")
            if st.session_state.document_context:
                selected_file = st.selectbox(
                    "Select a document to annotate:", 
                    list(st.session_state.document_context.keys())
                )
                if selected_file:
                    doc_content = st.session_state.document_context[selected_file]
                    display_annotated_document(selected_file, doc_content)
                    display_annotation_summary(selected_file)
            else:
                st.warning("No documents uploaded. Please upload files first.")

        # --- Research Agent ---
        with dashboard_tabs[2]:
            st.subheader("AI Research Assistant")
            research_query = st.text_input("Enter a research topic or question:")
            if st.button("Search AI"):
                if research_query:
                    response = research_agent(research_query)
                    st.session_state.research_answers = response
                    st.write("Research Agent Response:")
                    st.write(response)

        # --- AI Chat ---
        with dashboard_tabs[3]:
            st.subheader("AI-Powered Chat")
            user_query = st.text_input("Ask about the meeting:")
            if st.button("Ask AI"):
                if user_query:
                    context = ""
                    if st.session_state.meeting_transcript:
                        context = f"Meeting Transcript (so far):\n{st.session_state.meeting_transcript}\n\n"
                    enhanced_query = f"{context}Question: {user_query}"
                    response = research_agent(enhanced_query)
                    st.write("AI Response:")
                    st.write(response)
            st.subheader("Speak to AI")
            if st.button("Start Voice Input"):
                user_speech = record_audio()
                if user_speech:
                    st.write(f"You said: {user_speech}")
                    response = research_agent(user_speech)
                    st.write("AI Response:")
                    st.write(response)
                    # Optionally, also speak the response
                    speak_text(response)

        # --- Voting ---
        with dashboard_tabs[4]:
            st.subheader("Board Voting")
            st.markdown("Please cast your vote on key agenda items:")
            voting_questions = [
                "Do you approve the proposed meeting agenda?",
                "Should we implement AI in product design?",
                "Should we approve the new digital distribution strategy?",
                "Should we proceed with stock option grants?"
            ]
            user_votes = {}
            for question in voting_questions:
                user_votes[question] = st.radio(question, ["Yes", "No", "Abstain"], key=question)
            if st.button("Submit Votes"):
                st.success("Votes submitted successfully!")
                df_votes = simulate_voting_with_user(voting_questions, user_votes, num_simulated=10)
                stats = calculate_dashboard_stats(df_votes)
                display_voting_dashboard(df_votes, stats)

        # --- Comments ---
        with dashboard_tabs[5]:
            st.subheader("Comments by Board Members")
            if st.session_state.comments:
                for file_name, comment_list in st.session_state.comments.items():
                    st.write(f"Comments for **{file_name}**:")
                    for comment in comment_list:
                        st.markdown(f"**Section {comment['section']}**: {comment['comment']}")
                    st.markdown("---")
            else:
                st.info("No comments available.")

        # --- Live Meeting Analysis ---
        with dashboard_tabs[6]:
            st.subheader("Real-time Meeting Analysis")
            st.markdown("### Live Meeting Transcript")
            new_speech = st.text_area("Enter new speech:", key="live_speech_input")
            if st.button("Add to Transcript"):
                if new_speech:
                    transcribe_audio(new_speech)
                    generate_live_summary(st.session_state.meeting_transcript)
                    extract_action_items(st.session_state.meeting_transcript)
                    st.session_state["live_speech_input"] = ""
            st.text_area("Meeting Transcript:", st.session_state.meeting_transcript, height=300, disabled=True)
            st.markdown("### Live Summary")
            st.info(st.session_state.live_summary)
            st.markdown("### Action Items")
            if st.session_state.action_items:
                for item in st.session_state.action_items:
                    st.markdown(f"- {item}")
            else:
                st.info("No action items identified yet.")

    with insights_col:
        st.header("Insights")
        st.write("Latest insights from HLS Corporate Governance blog:")
        st.markdown("### AI in Governance")
        st.write("A concise summary highlighting how AI can transform decision-making in boardrooms.")
        st.markdown("[Read More](https://corpgov.law.harvard.edu)")
        st.markdown("---")
        st.markdown("### Regulatory Compliance Trends")
        st.write("An overview of the latest compliance challenges and best practices.")
        st.markdown("[Read More](https://corpgov.law.harvard.edu)")


def request_microphone_permission():
    """Request microphone permission and check if the microphone is accessible."""
    try:
        with sr.Microphone() as source:
            st.success("🎙️ Microphone is ready! You may proceed with voice features.")
            return True
    except Exception as e:
        st.warning("⚠ Microphone permission is required to use voice features. Please allow microphone access.")
        return False
    
if __name__ == "__main__":
    main()