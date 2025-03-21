import os
import streamlit as st
import openai
import docx2txt
import PyPDF2
from io import BytesIO
import random
import time  # For simulating real-time updates
import speech_recognition as sr  # For speech-to-text
from gtts import gTTS          # For text-to-speech
import pandas as pd            # For tabular display

# Set OpenAI API Key
openai.api_key = os.getenv("OPENAI_API_KEY")

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
    st.session_state.action_items = []

# ---------- 📂 Function to Process Documents ----------
def extract_text_from_file(uploaded_file):
    """Extracts text from DOCX, PDF, or TXT files"""
    file_name = uploaded_file.name.lower()
    file_text = ""
    try:
        if file_name.endswith('.docx'):
            file_text = docx2txt.process(uploaded_file)
        elif file_name.endswith('.pdf'):
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            file_text = "\n".join([page.extract_text() for page in pdf_reader.pages if page.extract_text()])
        else:  # TXT file
            file_text = uploaded_file.read().decode("utf-8")
    except Exception as e:
        st.warning(f"⚠ Could not read {uploaded_file.name}: {e}")
    return file_text

# ---------- 🎙️ Speech-to-Text Functionality ----------
def record_audio():
    """Records audio and returns the recognized text"""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("Recording... Please speak into your microphone.")
        audio_data = recognizer.listen(source, phrase_time_limit=10)
    try:
        query_text = recognizer.recognize_google(audio_data)
        st.success(f"You said: {query_text}")
        return query_text
    except Exception as e:
        st.error(f"⚠ Could not process the audio. Please try again. Error: {e}")
        return ""

# ---------- 🎤 Text-to-Speech Functionality ----------
def speak_text(text):
    """Converts text to speech using gTTS and plays it"""
    try:
        tts = gTTS(text=text, lang='en')
        tts.save("response.mp3")
        os.system("mpg321 response.mp3")  # You might need mpg321 or an alternative player
    except Exception as e:
        st.warning(f"Voice output failed: {e}")

# ---------- 📝 Function for Highlighting and Adding Comments ----------
def annotate_document(file_name, document_content, start_idx, end_idx):
    """Allows users to highlight text and add annotations for a section of the document"""
    st.subheader(f"🖍 Annotate Document: {file_name}")
    paragraphs = document_content.split("\n")
    display_section = paragraphs[start_idx:end_idx]
    for idx, para in enumerate(display_section):
        st.write(f"**Section {start_idx + idx + 1}:** {para}")
        highlight_key = f"highlight_{file_name}_{start_idx + idx}"
        comment_key = f"comment_{file_name}_{start_idx + idx}"
        if st.button(f"Highlight Section {start_idx + idx + 1}", key=highlight_key):
            st.session_state.annotations[file_name] = st.session_state.annotations.get(file_name, [])
            st.session_state.annotations[file_name].append({
                "section": start_idx + idx + 1,
                "highlighted_text": para
            })
            st.success(f"Highlighted: Section {start_idx + idx + 1}")
        comment_text = st.text_area(f"Add comment for Section {start_idx + idx + 1}", key=comment_key)
        if comment_text:
            if file_name not in st.session_state.comments:
                st.session_state.comments[file_name] = []
            st.session_state.comments[file_name].append({
                "section": start_idx + idx + 1,
                "comment": comment_text
            })
            st.success(f"📝 Comment added for Section {start_idx + idx + 1}")
    st.subheader("📌 Saved Highlights and Comments")
    if file_name in st.session_state.annotations:
        for ann in st.session_state.annotations[file_name]:
            st.markdown(f"**Section {ann['section']}**: {ann['highlighted_text']} (Highlighted)")
    return start_idx + len(display_section)

# ---------- 🔍 Research Agent Function ----------
def research_agent(query):
    """Processes a research query and returns AI-generated insights"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an AI research agent assisting board members."},
                {"role": "user", "content": query}
            ]
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        return f"⚠ Error contacting OpenAI: {e}"

# ---------- 🗳 Voting Dashboard Functions ----------
def simulate_voting_with_user(voting_questions, user_votes, num_simulated=10):
    """
    Create a dictionary with board member votes.
    The user is "You", and the rest are simulated.
    """
    data = {}
    data["You"] = {q: user_votes.get(q, "Abstain") for q in voting_questions}
    for i in range(1, num_simulated + 1):
        member_name = f"Board Member {i}"
        data[member_name] = {q: random.choice(["Yes", "No", "Abstain"]) for q in voting_questions}
    df = pd.DataFrame(data).T  # Transpose so that rows are board members and columns are questions
    return df

def calculate_dashboard_stats(df):
    """
    Calculate statistics per voting question from the DataFrame.
    Returns a dictionary with question as key and stats as value.
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
    st.dataframe(df)  # Display the main voting table
    st.markdown("---")
    st.subheader("🏆 Aggregated Voting Statistics")
    for question, s in stats.items():
        st.write(f"**{question}**")
        st.write(f"  - Yes: {s['Yes']}")
        st.write(f"  - No: {s['No']}")
        st.write(f"  - Abstain: {s['Abstain']}")
        st.write(f"  - Final Motion: {s['Final Motion']}")
        st.markdown("---")

# ---------- 📜 Main App ----------
def main():
    st.set_page_config(page_title="Governa AI - Real-time Board Intelligence", layout="wide")
    st.title("📌 Governa AI - Real-time Board Intelligence")
    st.header("📅 Upcoming Board Meeting Details")
    st.markdown("""
    **Board of Director Meeting Agenda**
    **March 27, 2025 ⋅ 10:30pm**
    - 10:30pm: Call to Order & Approvals
    - 10:35pm: Review Open Pre-Read Comments
    - 11:00pm: CEO Summary
    - 11:15pm: Deep Dive 1: Embracing AI in Product Design
    - 11:45pm: Deep Dive 2: Digital Distribution
    - Close
    """)
    
    tabs = st.tabs(["📂 Upload Documents", "📝 Annotate & Review", "🔍 Research Agent", "🎙 AI Chat", "🗳 Voting", "💬 Comments", "⏱️ Live Meeting Analysis"])

    # ---------- 📂 Upload Documents ----------
    with tabs[0]:
        st.subheader("📂 Upload Board Documents")
        uploaded_files = st.file_uploader("Upload meeting documents (PDF, DOCX, TXT)", 
                                          type=['pdf', 'docx', 'txt'], accept_multiple_files=True)
        if uploaded_files:
            for uploaded_file in uploaded_files:
                file_text = extract_text_from_file(uploaded_file)
                st.session_state.document_context[uploaded_file.name] = file_text
            st.success("✅ Documents uploaded successfully!")

    # ---------- 📝 Annotate & Review ----------
    with tabs[1]:
        st.subheader("📝 Annotate Meeting Documents")
        if st.session_state.document_context:
            for file_name, content in st.session_state.document_context.items():
                start_idx = 0
                end_idx = 10  # Show 10 sections per page
                while start_idx < len(content.split("\n")):
                    start_idx = annotate_document(file_name, content, start_idx, end_idx)
                    end_idx = start_idx + 10
                    if start_idx < len(content.split("\n")):
                        st.button("Next Page", key=f"next_page_{file_name}_{start_idx}")
        else:
            st.warning("⚠ No documents uploaded. Please upload files first.")

    # ---------- 🔍 Research Agent ----------
    with tabs[2]:
        st.subheader("🔍 AI Research Assistant")
        research_query = st.text_input("Enter a research topic or question:")
        if st.button("🔎 Search AI"):
            if research_query:
                response = research_agent(research_query)
                st.session_state.research_answers = response
                st.write("### Research Agent Response:")
                st.write(response)

    # ---------- 🎙 AI Chat ----------
    with tabs[3]:
        st.subheader("💬 AI-Powered Chat")
        user_query = st.text_input("Ask about the meeting:")
        if st.button("🤖 Ask AI"):
            if user_query:
                context = f"Meeting Transcript (so far):\n{st.session_state.meeting_transcript}\n\n" if st.session_state.meeting_transcript else ""
                enhanced_query = f"{context}Question: {user_query}"
                response = research_agent(enhanced_query)
                st.write("### 🤖 AI Response:")
                st.write(response)
        st.subheader("🎤 Speak to AI")
        if st.button("🎙 Start Voice Input"):
            user_speech = record_audio()
            if user_speech:
                st.write(f"🎤 You said: {user_speech}")
                response = research_agent(user_speech)
                st.write("🤖 AI Response:")
                st.write(response)

    # ---------- 🗳 Voting ----------
    with tabs[4]:
        st.subheader("🗳 Board Voting")
        st.markdown("Please cast your vote on key agenda items:")
        voting_questions = [
            "Do you approve the proposed meeting agenda?",
            "Should we implement AI in product design?",
            "Should we approve the new digital distribution strategy?",
            "Should we proceed with stock option grants?"
        ]
        # Collect user votes
        user_votes = {}
        for question in voting_questions:
            user_votes[question] = st.radio(question, ["Yes", "No", "Abstain"], key=question)
        if st.button("✅ Submit Votes"):
            st.success("🗳 Votes submitted successfully!")
            # Simulate votes including user's vote
            df_votes = simulate_voting_with_user(voting_questions, user_votes, num_simulated=10)
            # Calculate aggregated statistics
            stats = calculate_dashboard_stats(df_votes)
            # Display the voting dashboard
            display_voting_dashboard(df_votes, stats)

    # ---------- 💬 Comments ----------
    with tabs[5]:
        st.subheader("💬 Comments by Board Members")
        if st.session_state.comments:
            for file_name, comment_list in st.session_state.comments.items():
                st.write(f"### Comments for {file_name}")
                for comment in comment_list:
                    st.markdown(f"**Section {comment['section']}**: {comment['comment']}")
    
    # ---------- ⏱️ Live Meeting Analysis ----------
    with tabs[6]:
        st.subheader("⏱️ Real-time Meeting Analysis")
        st.markdown("### Live Meeting Transcript")
        new_speech = st.text_area("Enter new speech:", key="live_speech_input")
        if st.button("Add to Transcript"):
            if new_speech:
                # For simulation, append new speech to transcript
                st.session_state.meeting_transcript += f"{new_speech}\n"
                # (In a real app, call transcribe_audio(new_speech))
                # Generate live summary and extract action items as needed
                # generate_live_summary(st.session_state.meeting_transcript)
                # extract_action_items(st.session_state.meeting_transcript)
                st.session_state["live_speech_input"] = ""  # Clear input
        st.text_area("Meeting Transcript:", st.session_state.meeting_transcript, height=300, disabled=True)
        st.markdown("### Live Summary")
        st.info(st.session_state.live_summary)
        st.markdown("### Action Items")
        if st.session_state.action_items:
            for item in st.session_state.action_items:
                st.markdown(f"- 📌 {item}")
        else:
            st.info("No action items identified yet.")

# ---------- Functions for Voting Dashboard (New) ----------
def simulate_voting_with_user(voting_questions, user_votes, num_simulated=10):
    """
    Combine the user's vote with simulated votes from other board members.
    Returns a DataFrame with board members as rows and questions as columns.
    """
    data = {}
    # Add user's vote as "You"
    data["You"] = {q: user_votes.get(q, "Abstain") for q in voting_questions}
    # Simulate votes for other board members
    for i in range(1, num_simulated + 1):
        member_name = f"Board Member {i}"
        data[member_name] = {q: random.choice(["Yes", "No", "Abstain"]) for q in voting_questions}
    df = pd.DataFrame(data).T  # Transpose: rows are board members, columns are questions
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
    """Display the voting dashboard: a table of votes and aggregated statistics."""
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

if __name__ == "__main__":
    main()
