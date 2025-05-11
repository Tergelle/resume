import streamlit as st

st.set_page_config(page_title="About", layout="centered")

# --- Consistent CSS, card style ---
st.markdown("""
    <style>
    .stApp { background-color: #f7fafd; }
    .about-card {
        background: #fff;
        border-radius: 18px;
        box-shadow: 0 2px 12px #e0e7ef;
        padding: 2.5rem 2.5rem 2rem 2.5rem;
        margin: 3rem auto 2rem auto;
        max-width: 700px;
        min-width: 350px;
        text-align: center;
    }
    .about-card h1 {
        font-size: 2.2rem;
    }
    .about-list {
        text-align: left;
        margin: 1.5rem auto 0 auto;
        max-width: 500px;
        font-size: 1.1rem;
    }
    .about-list li {
        margin-bottom: 0.7rem;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="about-card">
    <h1>📘 About This App</h1>
    <p style="color:#334155; font-size:1.1rem; margin-bottom:1.5rem;">
        This multi-page app demonstrates the power of AI in resume parsing and job matching.<br>
        Built as a capstone project to help HR professionals and recruiters quickly extract, analyze, and match talent.
    </p>
    <ul class="about-list">
        <li>🚀 <b>Technologies:</b> Streamlit, Gemini AI, Python, Pandas, Plotly</li>
        <li>🤖 <b>Features:</b> Resume parsing, job matching, analytics dashboard, and more</li>
    </ul>
    <p style="margin-top:2rem; color:#64748b;">
        Created by <b>Tergel.B</b> <br>
    </p>
</div>
""", unsafe_allow_html=True)
