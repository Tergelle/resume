import streamlit as st
import pdfplumber
import docx
from google import genai
import os
import json
import re
import time
import google.generativeai as genai
import pandas as pd
from collections import Counter
import uuid
import hashlib
from datetime import datetime
import plotly.express as px
import logging
logging.basicConfig(level=logging.INFO)




def get_api_key():
    """Get API key from secrets or environment variables"""
    # In production, use Streamlit secrets
    if 'GEMINI_API_KEY' in st.secrets:
        return st.secrets["GEMINI_API_KEY"]
    # For local development or if set in environment
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        # Fallback to hardcoded key (not recommended for production)
        api_key = "AIzaSyAiRiy9CNUgu7CrorrSALFoi3016_MvmGM"
        
    return api_key

# Initialize Gemini client
def init_gemini_client():
    """Initialize Gemini client with API key, only once per session"""
    if 'gemini_client' not in st.session_state:
        api_key = get_api_key()
        st.session_state['gemini_client'] = genai.Client(api_key=api_key)
    return st.session_state['gemini_client']
# --- HELPER FUNCTIONS ---
def init_session_state():
    """Initialize session state variables"""
    if 'all_parsed_resumes' not in st.session_state:
        st.session_state['all_parsed_resumes'] = []
    if 'processing' not in st.session_state:
        st.session_state['processing'] = False
    if 'current_page' not in st.session_state:
        st.session_state['current_page'] = 0
    if 'items_per_page' not in st.session_state:
        st.session_state['items_per_page'] = 5
    if 'search_results' not in st.session_state:
        st.session_state['search_results'] = []
    if 'last_search_query' not in st.session_state:
        st.session_state['last_search_query'] = ""

# --- HELPER FUNCTIONS ---
def extract_text(file):
    """Extract text from PDF or DOCX files"""
    try:
        file_size = file.size
        # Check file size (limit to 10MB)
        if file_size > 10 * 1024 * 1024:
            st.error(f"File {file.name} is too large (max 10MB)")
            return None
            
        if file.name.endswith('.pdf'):
            with pdfplumber.open(file) as pdf:
                text = ''.join(page.extract_text() + '\n' for page in pdf.pages if page.extract_text())
                if not text.strip():
                    st.error(f"Could not extract text from {file.name}. The PDF might be scanned or protected.")
                    return None
                return text
        elif file.name.endswith('.docx'):
            doc = docx.Document(file)
            text = '\n'.join(para.text for para in doc.paragraphs)
            if not text.strip():
                st.error(f"Could not extract text from {file.name}")
                return None
            return text
        else:
            st.error(f"Unsupported file format: {file.name}")
            return None
    except Exception as e:
        st.error(f"Error extracting text from {file.name}: {e}")
        return None

def safe_generate_content(client, prompt, retries=3, delay=2):
    """Make API calls with retry logic"""
    for attempt in range(retries):
        try:
            return client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        except errors.ServerError as e:
            if attempt < retries - 1:
                st.warning(f"Server overloaded (attempt {attempt + 1}/{retries}). Retrying in {delay} seconds...")
                time.sleep(delay * (attempt + 1))  # Exponential backoff
            else:
                st.error(f"Failed after {retries} retries: {e}")
                return None
        except Exception as e:
            st.error(f"Error calling Gemini API: {e}")
            return None

def parse_resume_with_gemini(text, client):
    """Parse resume text using Gemini AI"""
    prompt = f"""
    You are an expert multilingual HR assistant. The following resume text may be in English or Mongolian. Please automatically detect the language and extract the information into **only valid JSON**. No explanations, no extra text, only JSON starting with {{ and ending with }}. 

Use the English field labels exactly as listed below, even if the resume is in Mongolian.

    Fields:
    - Full Name (string)
    - Email (string)
    - Phone Number (string)
    - Location (string)
    - LinkedIn URL (string)
    - Github URL (string)
    - Skills (array of strings)
    - Education (string with details of education history)
    - Work Experience (string with details of work history)
    - Certifications (string with details of certifications)
    - Seniority Level (string: "Junior", "Mid-level", "Senior", "Lead", "Manager", or "Executive")
    - Years of Experience (float, estimate from the resume)
    - Primary Programming Languages (array of strings, if applicable)
    - Primary Industry (string, the main industry the candidate works in)

    For the Skills field, extract a comprehensive list of all technical and soft skills mentioned.
    For Seniority Level, infer from job titles and responsibilities.
    
    Resume Text:
    {text}
    """
    
    with st.spinner("Analyzing resume with AI..."):
        response = safe_generate_content(client, prompt)
        if not response:
            return None

        raw_reply = response.candidates[0].content.parts[0].text.strip()

        # Try to extract JSON from the response using regex
        match = re.search(r'({.*})', raw_reply, re.DOTALL)
        if match:
            json_str = match.group(1)
            try:
                # Try to parse the JSON
                parsed_json = json.loads(json_str)
                return json_str
            except json.JSONDecodeError as e:
                st.warning("Initial JSON parsing failed. Attempting to clean and retry...")
                logging.exception(f"JSONDecodeError on initial parse: {e}")
                cleaned_json = re.sub(r',\s*}', '}', json_str)  # Remove trailing commas
                try:
                    json.loads(cleaned_json)
                    return cleaned_json
                except json.JSONDecodeError as e2:
                    logging.exception(f"JSONDecodeError after cleaning: {e2}")
                    st.error(f"Failed to parse JSON even after cleaning: {type(e2).__name__}: {e2}")
                    return None
        else:
            st.error("Could not extract JSON from the AI response")
            return None

def generate_unique_id():
    """Generate a unique ID for each resume"""
    return str(uuid.uuid4())

def search_resumes(resumes, filters):
    """Search resumes based on multiple filters"""
    results = resumes.copy()
    
    # Filter by skills
    if filters.get('skills'):
        skill_list = [skill.strip().lower() for skill in filters['skills'].split(',') if skill.strip()]
        if skill_list:
            results = [
                resume for resume in results 
                if all(any(search_skill in skill.lower() for skill in resume.get('Skills', [])) 
                    for search_skill in skill_list)
            ]
    
    # Filter by location
    if filters.get('location'):
        location_terms = [loc.strip().lower() for loc in filters['location'].split(',') if loc.strip()]
        if location_terms:
            results = [
                resume for resume in results
                if resume.get('Location') and any(term in resume.get('Location', '').lower() for term in location_terms)
            ]
    
    # Filter by seniority
    if filters.get('seniority'):
        seniority_levels = [level.strip().lower() for level in filters['seniority'].split(',') if level.strip()]
        if seniority_levels:
            results = [
                resume for resume in results
                if resume.get('Seniority Level') and any(level in resume.get('Seniority Level', '').lower() for level in seniority_levels)
            ]
    
    # Filter by name
    if filters.get('name'):
        name_query = filters['name'].lower()
        if name_query:
            results = [
                resume for resume in results
                if resume.get('Full Name') and name_query in resume.get('Full Name', '').lower()
            ]
    
    return results

def export_to_csv(resumes):
    """Export resumes to CSV format"""
    if not resumes:
        return None
    
    # Extract relevant fields for the CSV
    data = []
    for resume in resumes:
        data.append({
            'Full Name': resume.get('Full Name', ''),
            'Email': resume.get('Email', ''),
            'Phone Number': resume.get('Phone Number', ''),
            'Location': resume.get('Location', ''),
            'LinkedIn URL': resume.get('LinkedIn URL', ''),
            'Github URL': resume.get('Github URL', ''),
            'Skills': ', '.join(resume.get('Skills', [])),
            'Seniority Level': resume.get('Seniority Level', ''),
            'Years of Experience': resume.get('Years of Experience', ''),
            'Primary Industry': resume.get('Primary Industry', '')
        })
    
    df = pd.DataFrame(data)
    return df.to_csv(index=False).encode('utf-8')

def paginate(items, page, items_per_page):
    """Paginate a list of items"""
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    return items[start_idx:end_idx]

def calculate_similarity_score(resume1, resume2):
    """Calculate similarity score between two resumes based on skills"""
    skills1 = set(skill.lower() for skill in resume1.get('Skills', []))
    skills2 = set(skill.lower() for skill in resume2.get('Skills', []))
    
    if not skills1 or not skills2:
        return 0
    
    # Jaccard similarity coefficient
    intersection = len(skills1.intersection(skills2))
    union = len(skills1.union(skills2))
    
    return intersection / union if union > 0 else 0

def find_similar_resumes(target_resume, all_resumes, threshold=0.3):
    """Find resumes similar to the target resume"""
    similar_resumes = []
    
    for resume in all_resumes:
        if resume.get('id') == target_resume.get('id'):
            continue
        
        similarity = calculate_similarity_score(target_resume, resume)
        if similarity >= threshold:
            similar_resumes.append((resume, similarity))
    
    # Sort by similarity score
    similar_resumes.sort(key=lambda x: x[1], reverse=True)
    return similar_resumes

def calculate_resume_score(resume):
    """Calculate a simple resume score based on various factors"""
    score = 0
    
    # Skills count (max 30 points)
    skills_count = len(resume.get('Skills', []))
    score += min(skills_count * 2, 30)
    
    # Education (max 20 points)
    education = resume.get('Education', '').lower()
    if 'phd' in education or 'doctorate' in education:
        score += 20
    elif 'master' in education:
        score += 15
    elif 'bachelor' in education or 'bs' in education or 'ba' in education:
        score += 10
    elif education:
        score += 5
    
    # Experience (max 30 points)
    years = resume.get('Years of Experience', 0)
    if isinstance(years, str):
        try:
            years = float(years)
        except ValueError:
            years = 0
    
    if years >= 10:
        score += 30
    elif years >= 7:
        score += 25
    elif years >= 5:
        score += 20
    elif years >= 3:
        score += 15
    elif years >= 1:
        score += 10
    
    # Certifications (max 10 points)
    certifications = resume.get('Certifications', '')
    cert_count = certifications.count(',') + 1 if certifications else 0
    score += min(cert_count * 2, 10)
    
    # LinkedIn & Github (max 10 points)
    if resume.get('LinkedIn URL'):
        score += 5
    if resume.get('Github URL'):
        score += 5
    
    return score

def normalize_years(years):
    """Convert years of experience to float, or 0 if invalid."""
    try:
        return float(years)
    except (ValueError, TypeError):
        return 0.0

# --- UI COMPONENTS ---
def render_header():
    """Render the application header"""
    st.set_page_config(page_title="Smart HR Resume Parser", layout="wide")
    
    # Header with logo and title
    col1, col2 = st.columns([1, 5])
    with col1:
        st.markdown("")
    with col2:
        st.title("👩‍💼 Smart HR Resume Assistant")
        st.caption("Powered by Gemini AI")

def render_upload_tab():
    """Render the upload tab UI"""
    st.subheader("Upload Resumes")
    
    # Instructions
    with st.expander("ℹ️ Instructions", expanded=False):
        st.markdown("""
        1. Upload one or more resume files (PDF or DOCX format)
        2. The AI will extract information such as:
           - Personal details (name, contact info)
           - Skills and qualifications
           - Education and work history
           - Certifications and more
        3. Processed resumes will be available in the 'View & Search Candidates' tab
        """)
    
    # Uploader
    col1, col2 = st.columns([3, 1])
    with col1:
        uploaded_files = st.file_uploader(
            "Upload Resumes (PDF/DOCX)",
            type=["pdf", "docx"],
            accept_multiple_files=True,
            help="Maximum file size: 10MB"
        )
    
    with col2:
        st.markdown("### Options")
        overwrite = st.checkbox("Overwrite existing files", value=False)
        
    # Process button
    if uploaded_files:
        if st.button("🚀 Process Resumes", disabled=st.session_state.processing):
            process_uploaded_files(uploaded_files, init_gemini_client(), overwrite)
    
    # Display processing history if available
    if st.session_state.all_parsed_resumes:
        st.success(f"Total resumes processed: {len(st.session_state.all_parsed_resumes)}")
        # Allow clearing all resumes
        if st.button("❌ Clear All Resumes"):
            st.session_state.all_parsed_resumes = []
            st.experimental_rerun()

def process_uploaded_files(files, client, overwrite=False):
    """Process uploaded resume files"""
    try:
        st.session_state.processing = True
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        existing_filenames = [resume.get('File Name') for resume in st.session_state.all_parsed_resumes]
        processed_count = 0
        skipped_count = 0
        
        for i, uploaded_file in enumerate(files):
            progress = (i + 1) / len(files)
            progress_bar.progress(progress)
            status_text.text(f"Processing file {i+1} of {len(files)}: {uploaded_file.name}")
            
            # Check if file already exists and overwrite is not enabled
            if not overwrite and uploaded_file.name in existing_filenames:
                st.info(f"Skipping {uploaded_file.name} (already processed)")
                skipped_count += 1
                continue
                
            try:
                resume_text = extract_text(uploaded_file)
                if not resume_text:
                    continue
                    
                parsed_data = parse_resume_with_gemini(resume_text, client)
                if parsed_data:
                    try:
                        parsed_info = json.loads(parsed_data)
                        # Add metadata
                        parsed_info['File Name'] = uploaded_file.name
                        parsed_info['id'] = generate_unique_id()
                        parsed_info['processed_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        parsed_info['score'] = calculate_resume_score(parsed_info)
                        parsed_info['Years of Experience'] = normalize_years(parsed_info.get('Years of Experience', 0))
                        
                        # Remove existing entry if overwrite is enabled
                        if overwrite:
                            st.session_state.all_parsed_resumes = [
                                resume for resume in st.session_state.all_parsed_resumes 
                                if resume.get('File Name') != uploaded_file.name
                            ]
                            
                        st.session_state.all_parsed_resumes.append(parsed_info)
                        processed_count += 1
                    except json.JSONDecodeError as e:
                        st.error(f"Failed to parse JSON for {uploaded_file.name}: {e}")
                else:
                    st.error(f"Failed to get parsed data from Gemini for {uploaded_file.name}")
            except Exception as e:
                st.error(f"An error occurred while processing {uploaded_file.name}: {e}")
                
        status_text.text("All files processed!")
        progress_bar.empty()
        
        if processed_count > 0:
            st.success(f"✅ Successfully processed {processed_count} resume(s)!")
        if skipped_count > 0:
            st.info(f"ℹ️ Skipped {skipped_count} already processed file(s)")
            
    except Exception as e:
        st.error(f"An error occurred during processing: {e}")
    finally:
        st.session_state.processing = False

def render_view_tab():
    """Render the view and search tab UI"""
    st.subheader("View and Search Candidates")
    
    if not st.session_state.all_parsed_resumes:
        st.info("No resumes uploaded yet. Please upload resumes from the Upload tab.")
        return
    
    # Search filters
    with st.expander("🔍 Advanced Search", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            search_name = st.text_input("Search by name", "")
            search_skills = st.text_input("Search by skills (comma-separated)", "")
        with col2:
            search_location = st.text_input("Search by location", "")
            search_seniority = st.text_input("Search by seniority level", "")
        
        # Skills autocompletion suggestions
        if st.session_state.all_parsed_resumes:
            all_skills = []
            for resume in st.session_state.all_parsed_resumes:
                all_skills.extend(resume.get('Skills', []))
            top_skills = Counter([skill.lower() for skill in all_skills]).most_common(10)
            if top_skills:
                st.caption("Top skills for quick search: " + ", ".join([skill for skill, _ in top_skills]))
        
        # Apply search filters
        filters = {
            'name': search_name,
            'skills': search_skills,
            'location': search_location,
            'seniority': search_seniority
        }
        
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("🔍 Apply Filters"):
                st.session_state.search_results = search_resumes(st.session_state.all_parsed_resumes, filters)
                st.session_state.last_search_query = filters
                st.session_state.current_page = 0
        with col2:
            if st.button("🔄 Reset Filters"):
                st.session_state.search_results = []
                st.session_state.last_search_query = ""
                st.session_state.current_page = 0
        with col3:
            if st.session_state.search_results:
                st.markdown(f"**Found {len(st.session_state.search_results)} matching candidates**")
    
    # Export functionality
    with st.expander("📤 Export Data", expanded=False):
        st.markdown("Export your candidate data to CSV format")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📄 Export All Resumes"):
                csv_data = export_to_csv(st.session_state.all_parsed_resumes)
                st.download_button(
                    label="💾 Download CSV",
                    data=csv_data,
                    file_name=f"all_resumes_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
        with col2:
            if st.session_state.search_results:
                csv_data = export_to_csv(st.session_state.search_results)
                st.download_button(
                    label="💾 Download Filtered Results",
                    data=csv_data,
                    file_name=f"filtered_resumes_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
    
    # Sort options
    sort_col1, sort_col2 = st.columns([3, 1])
    with sort_col1:
        sort_options = ["Relevance Score (High to Low)", "Name (A-Z)", "Name (Z-A)", 
                        "Experience (High to Low)", "Recently Added"]
        sort_by = st.selectbox("Sort by:", sort_options)
    
    # Display resumes
    display_resumes = st.session_state.search_results if st.session_state.search_results else st.session_state.all_parsed_resumes
    
    # Sort resumes
    if sort_by == "Name (A-Z)":
        display_resumes = sorted(display_resumes, key=lambda x: x.get('Full Name', '').lower())
    elif sort_by == "Name (Z-A)":
        display_resumes = sorted(display_resumes, key=lambda x: x.get('Full Name', '').lower(), reverse=True)
    elif sort_by == "Experience (High to Low)":
        display_resumes = sorted(display_resumes, key=lambda x: x.get('Years of Experience', 0), reverse=True)
    elif sort_by == "Recently Added":
        display_resumes = sorted(display_resumes, key=lambda x: x.get('processed_date', ''), reverse=True)
    elif sort_by == "Relevance Score (High to Low)":
        display_resumes = sorted(display_resumes, key=lambda x: x.get('score', 0), reverse=True)
    
    # Pagination
    items_per_page = st.session_state.items_per_page
    total_pages = (len(display_resumes) - 1) // items_per_page + 1
    
    if total_pages > 1:
        col1, col2, col3 = st.columns([1, 3, 1])
        with col1:
            if st.button("◀️ Previous", disabled=st.session_state.current_page == 0):
                st.session_state.current_page = max(0, st.session_state.current_page - 1)
                st.experimental_rerun()
        with col2:
            st.markdown(f"### Page {st.session_state.current_page + 1} of {total_pages}")
        with col3:
            if st.button("Next ▶️", disabled=st.session_state.current_page >= total_pages - 1):
                st.session_state.current_page = min(total_pages - 1, st.session_state.current_page + 1)
                st.experimental_rerun()
    
    # Get current page items
    current_items = paginate(display_resumes, st.session_state.current_page, items_per_page)
    
    # Display candidates
    for resume in current_items:
        render_candidate_card(resume)

def render_candidate_card(resume):
    """Render a candidate card for resume details"""
    unique_id = resume.get('id', '').replace('-', '_')
    
    # Calculate match score if this is from search results
    match_score = resume.get('score', 0)
    
    # Card header with name and match score
    header_col1, header_col2 = st.columns([3, 1])
    with header_col1:
        full_name = resume.get('Full Name', 'Unknown')
        seniority = resume.get('Seniority Level', 'Not Detected')
        years_exp = normalize_years(resume.get('Years of Experience', 0)),
        exp_text = f", {years_exp} years" if years_exp else ""
        
        st.markdown(f"### 👤 {full_name} ({seniority}{exp_text})")
    with header_col2:
        st.markdown(f"**Match Score: {match_score}/100**")
    
    # Main card content
    with st.expander("View Details", expanded=False):
        # Basic information section
        st.markdown("#### 📋 Basic Information")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"**Email:** {resume.get('Email', 'N/A')}")
            st.markdown(f"**Phone:** {resume.get('Phone Number', 'N/A')}")
        
        with col2:
            st.markdown(f"**Location:** {resume.get('Location', 'N/A')}")
            st.markdown(f"**Industry:** {resume.get('Primary Industry', 'N/A')}")
        
        with col3:
            linkedin = resume.get('LinkedIn URL', '')
            github = resume.get('Github URL', '')
            
            if linkedin:
                st.markdown(f"**LinkedIn:** [Profile]({linkedin})")
            else:
                st.markdown("**LinkedIn:** N/A")
                
            if github:
                st.markdown(f"**GitHub:** [Profile]({github})")
            else:
                st.markdown("**GitHub:** N/A")
        
        # Skills section
        st.markdown("#### 🛠️ Skills")
        skills = resume.get('Skills', [])
        if skills:
            # Display skills as pills/tags
            html_skills = []
            for skill in skills:
                html_skills.append(f'<span style="background-color:#e6f3ff; padding:3px 8px; border-radius:10px; margin:2px; display:inline-block">{skill}</span>')
            
            st.markdown(' '.join(html_skills), unsafe_allow_html=True)
        else:
            st.markdown("No skills detected")
        
        # Education and Experience tabs
        tab1, tab2, tab3 = st.tabs(["Education", "Work Experience", "Certifications"])
        
        with tab1:
            st.markdown(resume.get('Education', 'No education information detected'))
        
        with tab2:
            st.markdown(resume.get('Work Experience', 'No work experience detected'))
        
        with tab3:
            st.markdown(resume.get('Certifications', 'No certifications detected'))
        
        # Action buttons
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("💾 Download JSON", key=f"json_{unique_id}"):
                json_data = json.dumps(resume, indent=4)
                st.download_button(
                    label="Save JSON File",
                    data=json_data,
                    file_name=f"{resume.get('Full Name', 'resume').replace(' ', '_')}.json",
                    mime="application/json",
                    key=f"download_{unique_id}"
                )
        with col2:
            if st.button("✏️ Edit Resume", key=f"edit_{unique_id}"):
                st.session_state[f"edit_mode_{unique_id}"] = True
        with col3:
            if st.button("🔍 Find Similar Candidates", key=f"similar_{unique_id}"):
                st.session_state[f"show_similar_{unique_id}"] = True
        
        # Edit mode
        if st.session_state.get(f"edit_mode_{unique_id}", False):
            st.markdown("### Edit Resume")
            
            # Editable fields
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Full Name", value=resume.get('Full Name', ''), key=f"name_{unique_id}")
                email = st.text_input("Email", value=resume.get('Email', ''), key=f"email_{unique_id}")
                phone = st.text_input("Phone Number", value=resume.get('Phone Number', ''), key=f"phone_{unique_id}")
                location = st.text_input("Location", value=resume.get('Location', ''), key=f"location_{unique_id}")
            
            with col2:
                linkedin = st.text_input("LinkedIn URL", value=resume.get('LinkedIn URL', ''), key=f"linkedin_{unique_id}")
                github = st.text_input("Github URL", value=resume.get('Github URL', ''), key=f"github_{unique_id}")
                seniority = st.text_input("Seniority Level", value=resume.get('Seniority Level', ''), key=f"seniority_{unique_id}")
                years_exp = st.text_input("Years of Experience", value=str(resume.get('Years of Experience', '')), key=f"years_{unique_id}")
                industry = st.text_input("Primary Industry", value=resume.get('Primary Industry', ''), key=f"industry_{unique_id}")
            
            skills_text = st.text_area("Skills (comma-separated)", value=', '.join(resume.get('Skills', [])), key=f"skills_{unique_id}")
            education = st.text_area("Education", value=resume.get('Education', ''), key=f"education_{unique_id}")
            experience = st.text_area("Work Experience", value=resume.get('Work Experience', ''), key=f"experience_{unique_id}")
            certifications = st.text_area("Certifications", value=resume.get('Certifications', ''), key=f"certifications_{unique_id}")
            
            # Save or cancel buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Save Changes", key=f"save_{unique_id}"):
                    try:
                        # Update resume with edited values
                        corrected_resume = resume.copy()
                        corrected_resume.update({
                            "Full Name": name,
                            "Email": email,
                            "Phone Number": phone,
                            "Location": location,
                            "LinkedIn URL": linkedin,
                            "Github URL": github,
                            "Seniority Level": seniority,
                            "Years of Experience": years_exp,
                            "Primary Industry": industry,
                            "Skills": [skill.strip() for skill in skills_text.split(",") if skill.strip()],
                            "Education": education,
                            "Work Experience": experience,
                            "Certifications": certifications,
                        })
                        
                        # Update resume in session state
                        for i, saved_resume in enumerate(st.session_state.all_parsed_resumes):
                            if saved_resume.get('id') == resume.get('id'):
                                st.session_state.all_parsed_resumes[i] = corrected_resume
                                break
                        
                        st.success("Changes saved successfully!")
                        st.session_state[f"edit_mode_{unique_id}"] = False
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Error saving changes: {e}")
            
            with col2:
                if st.button("❌ Cancel", key=f"cancel_{unique_id}"):
                    st.session_state[f"edit_mode_{unique_id}"] = False
                    st.experimental_rerun()
        
        # Similar candidates view
        if st.session_state.get(f"show_similar_{unique_id}", False):
            st.markdown("### Similar Candidates")
            similar_candidates = find_similar_resumes(resume, st.session_state.all_parsed_resumes)
            
            if similar_candidates:
                st.write(f"Found {len(similar_candidates)} candidates with similar skills")
                
                for similar_resume, similarity in similar_candidates[:3]:  # Show top 3
                    similarity_percentage = int(similarity * 100)
                    st.markdown(f"**{similar_resume.get('Full Name', 'Unknown')}** - {similarity_percentage}% match")
                    
                    # Show matching skills
                    skills1 = set(skill.lower() for skill in resume.get('Skills', []))
                    skills2 = set(skill.lower() for skill in similar_resume.get('Skills', []))
                    matching_skills = skills1.intersection(skills2)
                    
                    if matching_skills:
                        st.markdown("**Matching skills:** " + ", ".join(matching_skills))
                    
                    if st.button("View Profile", key=f"view_{similar_resume.get('id', '')}"):
                        # This would ideally navigate to that resume, but for now just toggle state
                        st.session_state[f"show_similar_{unique_id}"] = False
                        st.experimental_rerun()
            else:
                st.info("No similar candidates found")
            
            if st.button("Close", key=f"close_similar_{unique_id}"):
                st.session_state[f"show_similar_{unique_id}"] = False
                st.experimental_rerun()

def render_analytics_tab():
    """Render a practical, easy-to-understand analytics tab."""
    st.subheader("📊 Resume Analytics Dashboard")

    resumes = st.session_state.all_parsed_resumes
    if not resumes:
        st.info("No resumes uploaded yet. Please upload resumes from the Upload tab.")
        return

    # Extract data
    skills = []
    locations = []
    seniorities = []
    industries = []
    years_exp = []
    processed_dates = []

    for r in resumes:
        skills.extend(r.get('Skills', []))
        if r.get('Location'): locations.append(r['Location'])
        if r.get('Seniority Level'): seniorities.append(r['Seniority Level'])
        if r.get('Primary Industry'): industries.append(r['Primary Industry'])
        try:
            years_exp.append(float(r.get('Years of Experience', 0)))
        except Exception:
            pass
        if r.get('processed_date'): processed_dates.append(r['processed_date'][:10])

    # Summary stats
    skill_counter = Counter([s.strip().lower() for s in skills if s.strip()])
    location_counter = Counter([l.strip() for l in locations if l.strip()])
    seniority_counter = Counter([s.strip() for s in seniorities if s.strip()])
    industry_counter = Counter([i.strip() for i in industries if i.strip()])
    date_counter = Counter(processed_dates)

    top_skill = skill_counter.most_common(1)[0][0].title() if skill_counter else "N/A"
    top_location = location_counter.most_common(1)[0][0] if location_counter else "N/A"
    avg_exp = sum(years_exp)/len(years_exp) if years_exp else 0

    st.markdown("#### 📋 Summary")
    col1, col2, col3 = st.columns(3)
    col1.metric("Top Skill", top_skill)
    col2.metric("Top Location", top_location)
    col3.metric("Avg Experience", f"{avg_exp:.1f} yrs")

    st.divider()

    # Top Skills
    st.markdown("### 🏆 Top 10 Skills")
    if skill_counter:
        skill_df = pd.DataFrame(skill_counter.most_common(10), columns=["Skill", "Count"])
        st.bar_chart(skill_df.set_index("Skill"))
    else:
        st.info("No skill data available.")

    # Seniority Level Distribution
    st.markdown("### 🏅 Seniority Level Distribution")
    if seniority_counter:
        sen_df = pd.DataFrame(seniority_counter.most_common(), columns=["Seniority", "Count"])
        st.bar_chart(sen_df.set_index("Seniority"))
    else:
        st.info("No seniority data available.")

    # Location Distribution
    st.markdown("### 🌍 Top 10 Locations")
    if location_counter:
        loc_df = pd.DataFrame(location_counter.most_common(10), columns=["Location", "Count"])
        st.bar_chart(loc_df.set_index("Location"))
    else:
        st.info("No location data available.")


    # Industry Distribution
    st.markdown("### 🏭 Top 10 Industries")
    if industry_counter:
        ind_df = pd.DataFrame(industry_counter.most_common(10), columns=["Industry", "Count"])
        st.bar_chart(ind_df.set_index("Industry"))
    else:
        st.info("No industry data available.")

    # Candidate Count Over Time (optional)
    if date_counter and len(date_counter) > 1:
        st.markdown("### 📈 Candidates Processed Over Time")
        date_df = pd.DataFrame(sorted(date_counter.items()), columns=["Date", "Count"])
        st.line_chart(date_df.set_index("Date"))



# --- MAIN APP ---
def main():
    """Main application entry point"""
    # Initialize session state
    init_session_state()
    
    # Render header
    render_header()
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["📥 Upload & Parse", "👥 View & Search Candidates", "📊 Resume Analytics"])
    
    with tab1:
        render_upload_tab()
        
    with tab2:
        render_view_tab()
        
    with tab3:
        render_analytics_tab()

if __name__ == "__main__":
    main()
