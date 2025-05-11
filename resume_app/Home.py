import streamlit as st

st.set_page_config(page_title="ATS AI", layout="centered")

# --- CSS ---
st.markdown("""
    <style>
    .stApp {
        background-color: #f7fafd;
    }
    .welcome-card {
        background: #fff;
        border-radius: 18px;
        box-shadow: 0 2px 12px #e0e7ef;
        padding: 2.5rem 2.5rem 2rem 2.5rem;
        margin: 3rem auto 2rem auto;
        max-width: 800px;
        min-width: 400px;
        text-align: center;
    }
    .feature-list {
        text-align: left;
        margin: 1.5rem auto 0 auto;
        max-width: 600px;
        font-size: 1.18rem;
    }
    .feature-list li {
        margin-bottom: 0.9rem;
    }
    .welcome-card h1 {
        font-size: 2.5rem;
    }
    .cta-btn {
        background-color: #2563eb;
        color: white;
        border-radius: 8px;
        padding: 0.7rem 2rem;
        font-weight: 600;
        font-size: 1.1rem;
        border: none;
        margin-top: 2rem;
        margin-bottom: 0.5rem;
        transition: background 0.2s;
        cursor: pointer;
        display: inline-block;
        text-decoration: none;
    }
    .cta-btn:hover {
        background-color: #1e40af;
        color: #fff;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="welcome-card">
    <img src="https://cdn-icons-png.flaticon.com/512/3135/3135715.png" width="100" style="margin-bottom:1rem;" />
    <h1 style="margin-bottom:0.5rem;">👋 Welcome to ATS Resume Parser</h1>
    <p style="color:#334155; font-size:1.1rem; margin-bottom:1.5rem;">
        This app uses <b>Gemini AI</b> to extract structured data from resumes and help match candidates with job descriptions.
    </p>
    <ul class="feature-list">
        <li>📄 <b>Resume Parsing</b> — Upload PDF or DOCX resumes and extract key info</li>
        <li>🤖 <b>Job Description Matching</b> — Instantly find the best-fit candidates</li>
        <li>🧠 <b>AI-Powered Skill Extraction</b> — Extract skills from any job description</li>
        <li>📊 <b>Analytics Dashboard</b> — Visualize your talent pool</li>
    </ul>
</div>
""", unsafe_allow_html=True)

# Navigation button (not inside HTML)
st.page_link("pages/1_Resume_Parser.py", label="🚀 Get Started")
