import streamlit as st
import json
import re
import os
import google.generativeai as genai

# --- Consistent CSS with Resume Parser ---
st.markdown("""
    <style>
    .stApp {
        background-color: #f7fafd;
    }
    .job-matching-container {
        background: #fff;
        border-radius: 16px;
        box-shadow: 0 2px 8px #e0e7ef;
        padding: 1.2rem 1.5rem 1.2rem 1.5rem;
        margin-bottom: 1.2rem;
    }
    .skill-tag {
        background-color: #e6f3ff;
        color: #2563eb;
        border-radius: 12px;
        padding: 3px 10px;
        margin: 2px 4px 2px 0;
        display: inline-block;
        font-size: 0.95rem;
        font-weight: 500;
    }
    .match-score {
        font-size: 1.1rem;
        font-weight: 600;
        color: #059669;
        margin-left: 1rem;
    }
    .stButton>button, .stDownloadButton>button {
        background-color: #2563eb;
        color: white;
        border-radius: 8px;
        padding: 0.4rem 1.2rem;
        font-weight: 500;
        font-size: 1rem;
        height: 40px;
        min-width: 120px;
        text-align: center;
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        transition: background 0.2s;
        white-space: nowrap;
        border: none;
        margin-bottom: 8px;
    }
    .stButton>button:hover, .stDownloadButton>button:hover {
        background-color: #1e40af;
        cursor: pointer;
    }
    .stMarkdown h3, .stMarkdown h4, .stMarkdown h5 {
        color: #1e293b;
        font-family: 'Segoe UI', 'Roboto', sans-serif;
    }
    .stMarkdown {
        font-family: 'Segoe UI', 'Roboto', sans-serif;
        color: #334155;
    }
    </style>
""", unsafe_allow_html=True)

# --- Gemini config ---
api_key = "AIzaSyAiRiy9CNUgu7CrorrSALFoi3016_MvmGM"
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.0-flash")

def render_skill_tags(skills):
    return " ".join([f"<span class='skill-tag'>{s}</span>" for s in skills])

def render_job_matching_page():
    st.subheader("🧩 Job Matching")
    st.markdown("Paste a job description, extract required skills with AI, or enter skills manually. Then see which candidates are the best fit!")

    job_desc = st.text_area("Paste job description:", height=120, key="job_desc")
    extract_skills = st.button("Extract Skills with AI")
    manual_skills = st.text_area("Or enter required skills manually (comma-separated):", key="manual_skills")

    extracted_skills = []
    if extract_skills:
        text = job_desc.strip()
        if not text:
            st.warning("Please paste a job description to extract skills.")
        else:
            prompt = f"""
            Extract a comprehensive list of required skills (as a Python list of strings, no explanations, no extra text) from the following job description. Only output a valid Python list of strings.

            Job Description:
            {text}
            """
            with st.spinner("Extracting skills with AI..."):
                response = model.generate_content(prompt)
                if response and hasattr(response, 'text'):
                    match = re.search(r'\[(.*?)\]', response.text, re.DOTALL)
                    if match:
                        skills_str = match.group(0)
                        try:
                            extracted_skills = json.loads(skills_str.replace("'", '"'))
                        except Exception:
                            extracted_skills = [s.strip().strip('"\'') for s in skills_str.strip('[]').split(',') if s.strip()]
                    else:
                        st.warning("Could not extract skills from AI response.")
                else:
                    st.warning("No response from AI.")
            if extracted_skills:
                st.success(f"Extracted {len(extracted_skills)} skills.")
                st.markdown(render_skill_tags(extracted_skills), unsafe_allow_html=True)
    skills_for_matching = []
    if extracted_skills:
        skills_text = st.text_area("Review/edit extracted skills (comma-separated):", ", ".join(extracted_skills), key="review_skills")
        skills_for_matching = [s.strip().lower() for s in skills_text.split(",") if s.strip()]
        st.markdown(render_skill_tags(skills_for_matching), unsafe_allow_html=True)
    elif manual_skills.strip():
        skills_for_matching = [s.strip().lower() for s in manual_skills.split(",") if s.strip()]
        st.markdown(render_skill_tags(skills_for_matching), unsafe_allow_html=True)

    if st.button("Find Matches"):
        if not skills_for_matching:
            st.warning("Please extract or enter required skills first.")
            return
        if 'all_parsed_resumes' not in st.session_state or not st.session_state.all_parsed_resumes:
            st.warning("No parsed resumes available. Please parse resumes first.")
            return
        results = []
        for resume in st.session_state.all_parsed_resumes:
            candidate_skills = [s.lower() for s in resume.get('Skills', [])]
            overlap = set(skills_for_matching) & set(candidate_skills)
            score = len(overlap) / len(skills_for_matching) if skills_for_matching else 0
            results.append((resume, score, overlap))
        results.sort(key=lambda x: x[1], reverse=True)
        st.markdown("### Candidate Matches")
        for resume, score, overlap in results:
            if score > 0:
                st.markdown(
                    f"""
                    <div class='job-matching-container'>
                        <span style='font-size:1.2rem; font-weight:700;'>{resume.get('Full Name', 'Unknown')}</span>
                        <span class='match-score'>Match: {score*100:.0f}%</span>
                        <div style='margin-top:0.5rem;'>
                            {render_skill_tags(overlap)}
                        </div>
                    </div>
                    """, unsafe_allow_html=True
                )

if __name__ == "__main__" or True:
    render_job_matching_page()
