import streamlit as st
import json
import PyPDF2
from google import genai
from google.genai import types
from google.generativeai import GenerativeModel
import os

# --- Gemini Setup ---
os.environ["GOOGLE_API_KEY"] = "AIzaSyAiRiy9CNUgu7CrorrSALFoi3016_MvmGM"

# Initialize the model
model = GenerativeModel(model_name="gemini-2.0-flash")

def ats_extractor(resume_text):
    prompt = f'''
    Extract the following information from the resume below:
    1. Full Name
    2. Email ID
    3. LinkedIn ID
    4. Employment Details
    5. Technical Skills
    6. Soft Skills

    Resume:
    \"\"\"{resume_text}\"\"\"

    Provide the extracted information in JSON format only.
    '''
    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.7,
                "max_output_tokens": 2048
            }
        )
        return response.text or response.parts[0].text
    except Exception as e:
        return f"Error from Gemini: {str(e)}"

def extract_text_from_file(uploaded_file):
    if uploaded_file.name.endswith(".pdf"):
        reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text
    else:
        return uploaded_file.read().decode("utf-8")

st.set_page_config(page_title="Resume Parser", layout="centered")
st.title("📄 Resume Parser")

uploaded_file = st.file_uploader("Upload your resume (.pdf or .txt)", type=["pdf", "txt"])

if uploaded_file:
    resume_text = extract_text_from_file(uploaded_file)

    with st.spinner("Parsing your resume with Gemini..."):
        result = ats_extractor(resume_text)

        if not result:
            st.error("❌ No response received from Gemini.")
        else:
            try:
                parsed = json.loads(result)
                st.success("✅ Successfully Parsed!")
                st.subheader("Extracted Resume Data")
                st.json(parsed)
                st.download_button(
                    "📥 Download JSON",
                    data=json.dumps(parsed, indent=2),
                    file_name="parsed_resume.json",
                    mime="application/json"
                )
            except json.JSONDecodeError:
                st.error("❌ Gemini response is not valid JSON.")
                st.text(result)
