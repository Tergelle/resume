import streamlit as st
import json
from google import genai
import PyPDF2

API_KEY = "AIzaSyAiRiy9CNUgu7CrorrSALFoi3016_MvmGM"
client = genai.Client(api_key= API_KEY)

def extract_text_from_pdf(uploaded_file):
    """
    Extracts text from each page of the uploaded PDF file.
    """
    pdf_reader = PyPDF2.PdfReader(uploaded_file)
    text = ""
    for page in pdf_reader.pages:
        page_text = page.extract_text()
        if page_text:  # Check if text extraction is successful
            text += page_text + "\n"
    return text

def extract_resume_data(resume_text):
    prompt = f"""
    Extract detailed information from the following resume:
    - Full Name
    - Email ID
    - LinkedIn Profile
    - List of Skills
    - Employment History

    Resume:
    \"\"\"{resume_text}\"\"\"
    """
    
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=prompt,
        config={
            'response_mime_type': 'application/json',
        },
    )

    print("DEBUG - Response Object:", response)
    print("DEBUG - Response Object Attributes:", dir(response))

    try:
        # Parsing the JSON response if the response is a JSON string
        response_data = json.loads(response.result)  # Adjust based on actual attribute
        return response_data
    except AttributeError:
        print("Error: The expected attribute does not exist in the response object.")
        return None
    except json.JSONDecodeError:
        print("Error: Failed to decode JSON from response.")
        return None

# Streamlit UI
st.set_page_config(page_title="Resume Parser", layout="wide")
st.title("Resume Parser Using Gemini")

uploaded_file = st.file_uploader("Upload your resume (.txt, .pdf)", type=["txt", "pdf"])

if uploaded_file:
    if uploaded_file.name.endswith(".pdf"):
        # If a PDF is uploaded, extract text from it
        resume_text = extract_text_from_pdf(uploaded_file)
    else:
        # Assume it's a text file and read it directly
        resume_text = uploaded_file.getvalue().decode("utf-8")

    if resume_text:
        with st.spinner("Parsing your resume..."):
            extracted_data = extract_resume_data(resume_text)  # Ensure this function is defined
            if extracted_data:
                st.success("Resume parsed successfully!")
                st.json(extracted_data)
            else:
                st.error("Failed to parse the resume.")
else:
    st.info("Please upload a resume in PDF or text format.")
