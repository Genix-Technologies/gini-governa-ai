import os
import streamlit as st
import openai
import docx2txt
import PyPDF2
from io import BytesIO
import random
import pandas as pd  # For tabular representation

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

# ---------- 📝 Function for Highlighting and Adding Comments ----------
def annotate_document(file_name, document_content, start_idx, end_idx):
    """Allows users to highlight text and add annotations for a section of the document"""
    st.subheader(f"🖍 Annotate Document: {file_name}")

    # Split document into sections (paragraphs or lines)
    paragraphs = document_content.split("\n")

    # Display document content for the specific section
    display_section = paragraphs[start_idx:end_idx]

    for idx, para in enumerate(display_section):
        st.write(f"**Section {start_idx + idx + 1}:** {para}")

        # Highlight option (simulate by adding a comment button)
        highlight_key = f"highlight_{file_name}_{start_idx + idx}"
        comment_key = f"comment_{file_name}_{start_idx + idx}"

        # Add highlight (simulate)
        if st.button(f"Highlight Section {start_idx + idx + 1}", key=highlight_key):
            st.session_state.annotations[file_name] = st.session_state.annotations.get(file_name, [])
            st.session_state.annotations[file_name].append({
                "section": start_idx + idx + 1,
                "highlighted_text": para
            })
            st.success(f"Highlighted: Section {start_idx + idx + 1}")

        # Add comment for each section
        comment_text = st.text_area(f"Add comment for Section {start_idx + idx + 1}", key=comment_key)
        if comment_text:
            # Store comment
            if file_name not in st.session_state.comments:
                st.session_state.comments[file_name] = []
            st.session_state.comments[file_name].append({
                "section": start_idx + idx + 1,
                "comment": comment_text
            })
            st.success(f"📝 Comment added for Section {start_idx + idx + 1}")

    # Display saved annotations
    st.subheader("📌 Saved Highlights and Comments")
    if file_name in st.session_state.annotations:
        for ann in st.session_state.annotations[file_name]:
            st.markdown(f"**Section {ann['section']}**: {ann['highlighted_text']} (Highlighted)")

    # Return the updated index
    return start_idx + len(display_section)  # Return the updated index

# ---------- 🗳 Enhanced Voting Tab ----------
def simulate_random_votes(voting_questions):
    """Simulate random votes from 10 board members for each question"""
    votes_data = []
    board_members = [f"Board Member {i+1}" for i in range(10)]
    
    for question in voting_questions:
        # Simulate 10 random votes for each question
        random_votes = [random.choice(["Yes", "No", "Abstain"]) for _ in range(10)]
        for i, vote in enumerate(random_votes):
            votes_data.append({
                "Board Member": board_members[i],
                "Voting Question": question,
                "Vote": vote
            })
    return votes_data

def calculate_vote_statistics(votes_data):
    """Calculate the vote statistics for each question"""
    vote_stats = {}
    question_groups = pd.DataFrame(votes_data).groupby('Voting Question')
    
    for question, group in question_groups:
        yes_count = group['Vote'].value_counts().get("Yes", 0)
        no_count = group['Vote'].value_counts().get("No", 0)
        abstain_count = group['Vote'].value_counts().get("Abstain", 0)
        
        # Determine the final motion
        final_motion = "Motion Passed" if yes_count > no_count else "Motion Failed"
        
        vote_stats[question] = {
            "Yes": yes_count,
            "No": no_count,
            "Abstain": abstain_count,
            "Final Motion": final_motion
        }
    return vote_stats

def display_vote_statistics(vote_stats, votes_data):
    """Display the vote statistics and final motion in a single table"""
    st.subheader("🗳 Voting Results")
    
    # Create a DataFrame from the votes_data
    vote_df = pd.DataFrame(votes_data)

    # Display the vote table
    st.dataframe(vote_df)

    st.markdown("---")
    st.subheader("🏆 Final Voting Statistics")
    
    # Display the statistics and final motion for each question
    for question, stats in vote_stats.items():
        st.write(f"**Voting Results for: {question}**")
        st.write(f"  - **Yes**: {stats['Yes']}")
        st.write(f"  - **No**: {stats['No']}")
        st.write(f"  - **Abstain**: {stats['Abstain']}")
        st.write(f"  - **Final Motion**: {stats['Final Motion']}")
        st.markdown("---")

# ---------- 🔍 Research Agent Function ----------
def research_agent(query):
    """Processes a research query and returns AI-generated insights"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are an AI research agent assisting board members."},
                      {"role": "user", "content": query}]
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        return f"⚠ Error contacting OpenAI: {e}"

# ---------- 🎙 AI Chat Function ----------
def ai_chat(query, transcript=""):
    """Simulate AI interaction with meeting context"""
    try:
        context = f"Meeting Transcript (so far):\n{transcript}\n\n" if transcript else ""
        enhanced_query = f"{context}Question: {query}"
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are an AI assistant helping with board meeting questions."},
                      {"role": "user", "content": enhanced_query}]
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        return f"⚠ Error contacting OpenAI: {e}"

# ---------- 📜 Main App ----------
def main():
    st.set_page_config(page_title="Governa AI - Real-time Board Intelligence", layout="wide")

    st.title("📌 Governa AI - Real-time Board Intelligence")
    st.header("📅 Upcoming Board Meeting Details")
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

    tabs = st.tabs(["📂 Upload Documents", "📝 Annotate & Review", "🔍 Research Agent", "🎙 AI Chat", "🗳 Voting", "💬 Comments", "⏱️ Live Meeting Analysis"])

    # ---------- 📂 Upload Documents ----------
    with tabs[0]:
        st.subheader("📂 Upload Board Documents")
        uploaded_files = st.file_uploader(
            "Upload meeting documents (PDF, DOCX, TXT)", type=['pdf', 'docx', 'txt'], accept_multiple_files=True
        )

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
                # Paginated Annotation
                while start_idx < len(content.split("\n")):
                    start_idx = annotate_document(file_name, content, start_idx, end_idx)
                    end_idx = start_idx + 10  # Next 10 sections

                    # Add unique key to "Next Page" button
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
                response = ai_chat(user_query, st.session_state.meeting_transcript)
                st.write("### 🤖 AI Response:")
                st.write(response)

    # ---------- 🗳 Voting ----------
    with tabs[4]:
        st.subheader("🗳 Board Voting")
        st.markdown("Please cast your vote on key agenda items:")

        voting_questions = [
            "📜 Do you approve the proposed meeting agenda?",
            "🤖 Should we implement AI in product design?",
            "📢 Should we approve the new digital distribution strategy?",
            "💰 Should we proceed with stock option grants?"
        ]

        # Collect user votes
        for question in voting_questions:
            st.session_state.votes[question] = st.radio(question, ["Yes", "No", "Abstain"], key=question)

        if st.button("✅ Submit Votes"):
            st.success("🗳 Votes submitted successfully!")

            # Simulate random votes from 10 board members
            vote_data = simulate_random_votes(voting_questions)

            # Calculate statistics and final motion
            vote_stats = calculate_vote_statistics(vote_data)

            # Display statistics and final motion
            display_vote_statistics(vote_stats, vote_data)

if __name__ == "__main__":
    main()
