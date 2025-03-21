import os
import streamlit as st
import openai
import docx2txt
import PyPDF2
from io import BytesIO
import random
import time  # For simulating real-time updates
import speech_recognition as sr  # For speech-to-text
from gtts import gTTS  # For text-to-speech
import pandas as pd  # For tabular display

# ------------------ 🌐 Set OpenAI API Key ------------------
openai.api_key = os.getenv("OPENAI_API_KEY")

# ------------------ 🧠 Initialize Session States ------------------
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
    st.session_state.action_items = []

# ------------------ 📂 Extract Text from Files ------------------
def extract_text_from_file(uploaded_file):
    """Extracts text from DOCX, PDF, or TXT files."""
    file_name = uploaded_file.name.lower()
    file_text = ""
    try:
        if file_name.endswith(".docx"):
            file_text = docx2txt.process(uploaded_file)
        elif file_name.endswith(".pdf"):
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            file_text = "\n".join(
                [page.extract_text() for page in pdf_reader.pages if page.extract_text()]
            )
        else:  # TXT file
            file_text = uploaded_file.read().decode("utf-8")
    except Exception as e:
        st.warning(f"⚠ Could not read {uploaded_file.name}: {e}")
    return file_text

# ------------------ 🎙️ Speech-to-Text ------------------
def record_audio():
    """Records audio, processes it, and returns the recognized text."""
    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            st.info("🎙️ Recording... Please speak into your microphone.")
            recognizer.adjust_for_ambient_noise(source, duration=1)
            audio_data = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            st.success("✅ Recording complete. Processing audio...")
        query_text = recognizer.recognize_google(audio_data)
        st.success(f"🎉 You said: {query_text}")
        return query_text
    except sr.UnknownValueError:
        st.warning("🤷 I couldn't understand what you said. Please try again.")
    except sr.RequestError as e:
        st.error(f"⚠ Error contacting Google API: {e}")
    except Exception as e:
        st.error(f"❗ An unexpected error occurred: {e}")
    return ""

# ------------------ 🎤 Text-to-Speech ------------------
def speak_text(text):
    """Converts text to speech and plays it."""
    try:
        tts = gTTS(text=text, lang="en")
        tts.save("response.mp3")
        st.audio("response.mp3", format="audio/mp3")
    except Exception as e:
        st.warning(f"Voice output failed: {e}")

# ------------------ 🔍 AI Research Agent ------------------
def research_agent(query):
    """Processes a research query and returns AI-generated insights."""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an AI research agent assisting board members."},
                {"role": "user", "content": query},
            ],
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        return f"⚠ Error contacting OpenAI: {e}"

# ------------------ 🗳 Voting Simulation ------------------
def simulate_voting_with_user(voting_questions, user_votes, num_simulated=10):
    """Combine user and simulated votes. Returns DataFrame."""
    data = {"You": {q: user_votes.get(q, "Abstain") for q in voting_questions}}
    for i in range(1, num_simulated + 1):
        member_name = f"Board Member {i}"
        data[member_name] = {
            q: random.choice(["Yes", "No", "Abstain"]) for q in voting_questions
        }
    return pd.DataFrame(data).T

def calculate_dashboard_stats(df):
    """Calculate aggregated voting statistics."""
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
            "Final Motion": final_motion,
        }
    return stats

def display_voting_dashboard(df, stats):
    """Display the voting dashboard and statistics."""
    st.subheader("📊 Voting Dashboard")
    st.dataframe(df)
    st.markdown("---")
    st.subheader("🏆 Aggregated Voting Statistics")
    for question, s in stats.items():
        st.write(f"**{question}**")
        st.write(f"- Yes: {s['Yes']} | No: {s['No']} | Abstain: {s['Abstain']}")
        st.write(f"- 🏅 Final Motion: {s['Final Motion']}")
        st.markdown("---")

# ------------------ 📜 Main App ------------------
def main():
    st.set_page_config(page_title="Governa AI - Board Intelligence", layout="wide")
    st.title("📌 Governa AI - Real-time Board Intelligence")
    
    # 🕒 Meeting Agenda
    st.header("📅 Upcoming Board Meeting Details")
    st.markdown("""
    **Board of Director Meeting Agenda**
    **March 27, 2025 ⋅ 10:30 PM**
    - 10:30 PM: Call to Order & Approvals
    - 10:35 PM: Review Open Pre-Read Comments
    - 11:00 PM: CEO Summary
    - 11:15 PM: Deep Dive 1: Embracing AI in Product Design
    - 11:45 PM: Deep Dive 2: Digital Distribution
    - Close
    """)

    # Tabs for features
    tabs = st.tabs(
        [
            "📂 Upload Documents",
            "🔍 AI Research",
            "🗳 Voting",
            "🎙 AI Chat",
            "💬 Comments",
            "⏱️ Live Meeting Analysis",
        ]
    )

    # ---------- 📂 Upload Documents ----------
    with tabs[0]:
        st.subheader("📂 Upload Board Documents")
        uploaded_files = st.file_uploader(
            "Upload meeting documents (PDF, DOCX, TXT)",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True,
        )
        if uploaded_files:
            for uploaded_file in uploaded_files:
                file_text = extract_text_from_file(uploaded_file)
                st.session_state.document_context[uploaded_file.name] = file_text
            st.success("✅ Documents uploaded successfully!")

    # ---------- 🔍 AI Research ----------
    with tabs[1]:
        st.subheader("🔍 AI Research Agent")
        research_query = st.text_input("Enter a research topic or question:")
        if st.button("🔎 Search AI"):
            if research_query:
                response = research_agent(research_query)
                st.write("### 🤖 AI Response:")
                st.write(response)

    # ---------- 🗳 Voting ----------
    with tabs[2]:
        st.subheader("🗳 Board Voting")
        st.markdown("Please cast your vote on key agenda items:")
        voting_questions = [
            "Do you approve the proposed meeting agenda?",
            "Should we implement AI in product design?",
            "Should we approve the new digital distribution strategy?",
            "Should we proceed with stock option grants?",
        ]
        user_votes = {}
        for question in voting_questions:
            user_votes[question] = st.radio(
                question, ["Yes", "No", "Abstain"], key=question
            )
        if st.button("✅ Submit Votes"):
            st.success("🗳 Votes submitted successfully!")
            df_votes = simulate_voting_with_user(voting_questions, user_votes, 10)
            stats = calculate_dashboard_stats(df_votes)
            display_voting_dashboard(df_votes, stats)

    # ---------- 🎙 AI Chat ----------
    with tabs[3]:
        st.subheader("💬 AI-Powered Chat")
        user_query = st.text_input("Ask about the meeting:")
        if st.button("🤖 Ask AI"):
            if user_query:
                response = research_agent(user_query)
                st.write("### 🤖 AI Response:")
                st.write(response)
        st.subheader("🎤 Speak to AI")
        if st.button("🎙 Start Voice Input"):
            user_speech = record_audio()
            if user_speech:
                response = research_agent(user_speech)
                st.write("### 🤖 AI Response:")
                st.write(response)

    # ---------- 💬 Comments ----------
    with tabs[4]:
        st.subheader("💬 Comments by Board Members")
        if st.session_state.comments:
            for file_name, comment_list in st.session_state.comments.items():
                st.write(f"### Comments for {file_name}")
                for comment in comment_list:
                    st.markdown(f"**Section {comment['section']}**: {comment['comment']}")
        else:
            st.info("No comments available yet. Add comments during review.")

    # ---------- ⏱️ Live Meeting Analysis ----------
    with tabs[5]:
        st.subheader("⏱️ Real-time Meeting Transcript")
        st.text_area("📄 Meeting Transcript", st.session_state.meeting_transcript, height=300)
        if st.button("📜 Summarize Transcript"):
            if st.session_state.meeting_transcript:
                summary_query = (
                    "Summarize this meeting transcript and extract key action items."
                )
                summary_response = research_agent(st.session_state.meeting_transcript)
                st.session_state.live_summary = summary_response
                st.write("### 📚 Meeting Summary:")
                st.write(summary_response)
            else:
                st.warning("❗ Please upload a transcript or record audio first.")

# Run Main
if __name__ == "__main__":
    main()
