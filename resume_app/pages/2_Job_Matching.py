import streamlit as st
import os
import google.generativeai as genai

# --- CONFIG ---
api_key = "AIzaSyAiRiy9CNUgu7CrorrSALFoi3016_MvmGM"
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.0-flash")


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
            client = init_gemini_client()
            prompt = f"""
            Extract a comprehensive list of required skills (as a Python list of strings, no explanations, no extra text) from the following job description. Only output a valid Python list of strings.

            Job Description:
            {text}
            """
            with st.spinner("Extracting skills with AI..."):
                response = client.generate_content(prompt)
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
    skills_for_matching = []
    if extracted_skills:
        skills_text = st.text_area("Review/edit extracted skills (comma-separated):", ", ".join(extracted_skills), key="review_skills")
        skills_for_matching = [s.strip().lower() for s in skills_text.split(",") if s.strip()]
    elif manual_skills.strip():
        skills_for_matching = [s.strip().lower() for s in manual_skills.split(",") if s.strip()]

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
            st.markdown(f"**{resume.get('Full Name', 'Unknown')}** — Match: {score*100:.0f}%")
            if overlap:
                st.markdown("Matching skills: " + ", ".join(overlap))
            st.markdown("---")

if __name__ == "__main__" or True:
    render_job_matching_page()
