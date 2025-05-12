# 🧠 ATS Resume Parser & Job Matcher

A multi-page Streamlit application powered by **Gemini AI** (Google Generative AI) that extracts structured data from resumes, matches candidates to job descriptions, and visualizes your talent pool using interactive analytics.

---

## 🚀 Features

- **📄 Resume Parsing** – Upload PDF or DOCX resumes and extract key details (skills, education, experience, etc.)
- **🤖 Job Description Matching** – Instantly find the best-fit candidates for any job description using AI
- **🧠 AI-Powered Skill Extraction** – Automatically extract skills from job descriptions using Gemini AI
- **📊 Analytics Dashboard** – Visualize your talent pool with interactive charts (skills, locations, experience, etc.)
- **🔎 Advanced Search & Filtering** – Filter candidates by skill, seniority, location, and more
- **📁 Export Options** – Download candidate data in CSV or JSON format

---

## 🛠️ Technologies Used

- [Streamlit](https://streamlit.io/)
- [Gemini AI (Google Generative AI)](https://ai.google.dev/)
- Python Libraries:
  - `pandas`
  - `plotly`
  - `pdfplumber`
  - `python-docx`

---

## 📦 Installation

### 1. Clone the repository

```bash
git clone https://github.com/Tergelle/resume.git
cd resume_app
```

### 2. Install dependencies
``` bash
pip install -r requirements.txt
```
### 3. Set up Gemini API Key
Get your API key from [Google AI Studio](https://(https://aistudio.google.com/))

## ▶️ Run the App
```bash
streamlit run Home.py
```
## 📄 Usage Overview
- Home – Welcome page and app overview

- Resume Parser – Upload resumes to extract structured data

- Job Matching – Paste job descriptions to find top-matching candidates

- Analytics – Visual insights on your candidate pool

- About – Project information and background


