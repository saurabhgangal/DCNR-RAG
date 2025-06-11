import streamlit as st
import os

# Clear ALL proxy settings before importing OpenAI
for proxy in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy', 'NO_PROXY', 'no_proxy']:
    if proxy in os.environ:
        del os.environ[proxy]

# Now import OpenAI
from openai import OpenAI
import PyPDF2
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json
import pickle
from typing import Dict, List, Tuple
import time
import threading
import streamlit.components.v1 as components

# Page config
st.set_page_config(page_title="PA DCNR Grant Assistant", page_icon="🌲", layout="wide")

# IMPORTANT: Replace this with your actual OpenAI API key
# For local development, use the hardcoded key
# For Streamlit Cloud, it will use the secret
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", "sk-your-actual-api-key-here")

# Regional Advisors Data
REGIONAL_ADVISORS = {
    "regions": {
        "1": {
            "advisor": "Danielle Guttman",
            "phone": "(717) 884-6908",
            "email": "dguttman@pa.gov",
            "counties": ["philadelphia", "delaware", "chester", "montgomery", "bucks"]
        },
        "2": {
            "advisor": "Jeanne Barrett Ortiz",
            "phone": "(267) 252-2806",
            "email": "jeabarrett@pa.gov",
            "counties": ["northampton", "lehigh", "carbon", "monroe", "pike"]
        },
        "3": {
            "advisor": "Lindsay Baer",
            "phone": "(717) 858-1185",
            "email": "libaer@pa.gov",
            "counties": ["perry", "cumberland", "franklin", "adams", "york", "lancaster", 
                        "lebanon", "dauphin", "juniata", "mifflin", "huntingdon", "blair", 
                        "cambria", "bedford", "fulton", "somerset"]
        },
        "4": {
            "advisor": "Wes Fahringer",
            "phone": "(570) 900-3265",
            "email": "mfahringer@pa.gov",
            "counties": ["centre", "clinton", "lycoming", "union", "snyder", 
                        "northumberland", "montour", "columbia"]
        },
        "5": {
            "advisor": "Adriene Smochek",
            "phone": "(412) 565-7803",
            "email": "asmochek@pa.gov",
            "counties": ["beaver", "allegheny", "washington", "greene", "fayette", 
                        "westmoreland", "indiana", "armstrong", "butler", "lawrence"]
        },
        "6": {
            "advisor": "Adam Mattis",
            "phone": "(412) 770-3774",
            "email": "amattis@pa.gov",
            "counties": ["erie", "crawford", "mercer", "venango", "forest", "warren", 
                        "mckean", "elk", "clarion", "jefferson", "clearfield", "potter", 
                        "tioga", "bradford", "susquehanna", "wayne", "wyoming", "sullivan", 
                        "lackawanna"]
        }
    }
}

def get_regional_advisor(county_name):
    """Get the regional advisor for a given county"""
    county_lower = county_name.lower().strip()
    
    for region_num, region_data in REGIONAL_ADVISORS["regions"].items():
        if county_lower in region_data["counties"]:
            return {
                "region": region_num,
                "advisor_name": region_data["advisor"],
                "phone": region_data["phone"],
                "email": region_data["email"],
                "counties_served": region_data["counties"]
            }
    
    return None

def format_advisor_info(advisor_info):
    """Format advisor information for display"""
    if not advisor_info:
        return "Regional advisor information not found. Please check the county name."
    
    return f"""
**Your Regional Advisor (Region {advisor_info['region']}):**
👤 **{advisor_info['advisor_name']}**
📞 Phone: {advisor_info['phone']}
📧 Email: {advisor_info['email']}

This advisor serves {len(advisor_info['counties_served'])} counties in your region.
Contact them early in your grant planning process for guidance and support!
"""

# Custom CSS for animations and styling
st.markdown("""
<style>
    /* Animated gradient background for header */
    .main-header {
        background: linear-gradient(-45deg, #2E7D32, #4CAF50, #66BB6A, #81C784);
        background-size: 400% 400%;
        animation: gradient 15s ease infinite;
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    
    @keyframes gradient {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    /* Floating animation for icons */
    .floating {
        animation: float 3s ease-in-out infinite;
    }
    
    @keyframes float {
        0% { transform: translateY(0px); }
        50% { transform: translateY(-20px); }
        100% { transform: translateY(0px); }
    }
    
    /* Pulse animation for important info */
    .pulse {
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
    
    /* Slide in animation */
    .slide-in {
        animation: slideIn 0.5s ease-out;
    }
    
    @keyframes slideIn {
        from {
            transform: translateX(-100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    /* Success checkmark animation */
    .checkmark {
        animation: checkmark 0.5s ease-in-out;
    }
    
    @keyframes checkmark {
        0% { transform: scale(0) rotate(0deg); }
        50% { transform: scale(1.2) rotate(180deg); }
        100% { transform: scale(1) rotate(360deg); }
    }
    
    /* Loading dots animation */
    .loading-dots {
        display: inline-block;
        width: 80px;
        height: 20px;
    }
    
    .loading-dots:after {
        content: ' . . .';
        animation: dots 1.5s steps(5, end) infinite;
    }
    
    @keyframes dots {
        0%, 20% { content: '.'; }
        40% { content: '. .'; }
        60% { content: '. . .'; }
        80%, 100% { content: ''; }
    }
    
    /* Chat message animation */
    .chat-message {
        animation: fadeInUp 0.5s ease-out;
    }
    
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    /* Hover effects */
    .stButton > button {
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }
    
    /* Regional advisor card styling */
    .advisor-card {
        background: linear-gradient(135deg, #E3F2FD, #BBDEFB);
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 4px solid #2196F3;
        animation: slideIn 0.5s ease-out;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'documents' not in st.session_state:
    st.session_state.documents = {}
if 'grant_data' not in st.session_state:
    st.session_state.grant_data = {}
if 'client' not in st.session_state:
    st.session_state.client = None
if 'last_update' not in st.session_state:
    st.session_state.last_update = None

def get_openai_client():
    """Get or create OpenAI client with minimal configuration"""
    if 'client' not in st.session_state or st.session_state.client is None:
        try:
            # Double-check no proxy settings exist
            for proxy in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
                if proxy in os.environ:
                    del os.environ[proxy]
            
            # Check if we're on Streamlit Cloud
            if os.environ.get('STREAMLIT_SHARING_MODE'):
                # Use environment variable for API key on Streamlit Cloud
                api_key = st.secrets.get("OPENAI_API_KEY", OPENAI_API_KEY)
            else:
                # Use hardcoded key for local development
                api_key = OPENAI_API_KEY
            
            # Create the most basic client possible
            client = OpenAI(api_key=api_key)
            
            # Store it
            st.session_state.client = client
            return client
            
        except Exception as e:
            st.error(f"Error creating OpenAI client: {str(e)}")
            # Try alternative initialization
            try:
                # Set API key directly and try again
                os.environ['OPENAI_API_KEY'] = api_key
                client = OpenAI()
                st.session_state.client = client
                return client
            except Exception as e2:
                st.error(f"Alternative initialization also failed: {str(e2)}")
                return None
    
    return st.session_state.client

class GrantRAGSystem:
    def __init__(self):
        self.grant_url = "https://www.pa.gov/agencies/dcnr/programs-and-services/grants/community-conservation-partnerships-program-grants.html"
        self.data_file = "grant_data.pkl"
        
    def scrape_grant_data(self):
        """Scrape grant information from PA DCNR website"""
        try:
            response = requests.get(self.grant_url, timeout=30)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            grant_data = {
                'last_updated': datetime.now().isoformat(),
                'grants': [],
                'general_info': '',
                'deadlines': [],
                'eligibility_criteria': {},
                'planning_session_transcript': self.get_planning_session_content(),
                'regional_advisors': REGIONAL_ADVISORS
            }
            
            # Extract general program information
            main_content = soup.find('main') or soup.find('div', class_='content')
            if main_content:
                # Extract paragraphs and lists
                for elem in main_content.find_all(['p', 'ul', 'ol', 'h2', 'h3']):
                    grant_data['general_info'] += elem.get_text(strip=True) + '\n'
            
            # Look for specific grant types
            grant_sections = soup.find_all(['section', 'div'], class_=['grant', 'program'])
            for section in grant_sections:
                grant_info = {
                    'title': section.find(['h2', 'h3']).get_text(strip=True) if section.find(['h2', 'h3']) else '',
                    'description': '',
                    'eligibility': '',
                    'deadline': ''
                }
                
                # Extract grant details
                for p in section.find_all('p'):
                    text = p.get_text(strip=True)
                    if 'eligib' in text.lower():
                        grant_info['eligibility'] += text + ' '
                    elif 'deadline' in text.lower() or 'due' in text.lower():
                        grant_info['deadline'] = text
                    else:
                        grant_info['description'] += text + ' '
                
                if grant_info['title']:
                    grant_data['grants'].append(grant_info)
            
            # Save scraped data
            with open(self.data_file, 'wb') as f:
                pickle.dump(grant_data, f)
            
            return grant_data
            
        except Exception as e:
            st.error(f"Error scraping website: {str(e)}")
            # Return at least the planning session content
            return {
                'last_updated': datetime.now().isoformat(),
                'grants': [],
                'general_info': '',
                'deadlines': [],
                'eligibility_criteria': {},
                'planning_session_transcript': self.get_planning_session_content(),
                'regional_advisors': REGIONAL_ADVISORS
            }
    
    def get_planning_session_content(self):
        """Get the DCNR planning session transcript content"""
        return """DCNR Community Conservation Partnerships Program - Planning Session Information

Important Dates:
- Grant applications accepted: January 21st, 2025 through April 2nd, 2025
- Application deadline: April 2nd, 2025 at 4:00 PM

Eligible Applicants:
- Municipalities
- Municipal authorities
- Council of Governments
- Conservation districts
- School districts
- Nonprofit 501c3 organizations

Note: Municipal applicants are strongly encouraged because they are eligible for Keystone Fund. Nonprofits are only eligible for environmental stewardship funds, which is very limited.

Planning Project Types:
1. Master Site Development Plans
   - Site-specific plan for development, rehabilitation, use, and management
   - Focus on one site owned or controlled by applicant
   - Typical grant award: $25,000 to $75,000

2. Comprehensive Recreation, Park, Open Space & Greenway Plans
   - Long-term development for park recreation systems
   - Can be municipal, county, or regional scale
   - Establishes priorities, actions, costs, and timeline

3. Conservation Management/Stewardship Plans
   - Analyzes conservation of natural areas and critical habitat
   - Includes public access and passive recreation opportunities
   - Requires collaboration with conservancy or land trust

4. Swimming Pool Complex Feasibility Studies
   - Structural assessment of existing features
   - Market analysis and financial capability assessment
   - Public engagement essential

5. Indoor Recreation Facility Feasibility Studies
   - For recreation centers, gymnasiums, indoor ice rinks
   - Includes parking, accessibility, and site amenities
   - Focus on one site only

Grant Requirements:
- Minimum of two quotes from qualified consultants required
- Dollar-for-dollar match requirement
- Detailed scope of work required (not lump sum)
- Public participation required for all plans
- For existing facilities: 25-year minimum lease or ownership

Ready-to-Go Status Requirements:
1. Clear and detailed scope of work uploaded
2. Realistic, detailed budget (no lump sums)
3. Funding commitment letter for match
4. Site control documentation (for site-specific plans)

Budget Categories:
- Contracted professional services
- Donated professional services
- Other project costs (cash and non-cash)

Scoring (100 points maximum):
- Ready-to-go status
- Criteria questions responses
- Consistency with local/regional plans
- Partnerships

Key Tips:
- Contact your bureau regional advisor early
- Review frequently asked questions document
- Involve qualified consultants early
- Obtain detailed cost estimates
- Reference help text in grant application
- Visit apps.dcnr.pa.gov for resources

REGIONAL ADVISORS:
It's important to contact your regional advisor early in the grant planning process. They can provide guidance on your application and help ensure you meet all requirements."""
    
    def load_grant_data(self):
        """Load saved grant data or scrape if needed"""
        if os.path.exists(self.data_file):
            with open(self.data_file, 'rb') as f:
                data = pickle.load(f)
                
            # Check if data is older than 30 days
            last_update = datetime.fromisoformat(data['last_updated'])
            if datetime.now() - last_update > timedelta(days=30):
                return self.scrape_grant_data()
            
            # Ensure regional advisors are included
            if 'regional_advisors' not in data:
                data['regional_advisors'] = REGIONAL_ADVISORS
                
            return data
        else:
            return self.scrape_grant_data()
    
    def check_eligibility(self, user_info: Dict, grant_type: str = None) -> Dict:
        """Check eligibility based on user information"""
        eligibility_results = {
            'eligible_grants': [],
            'ineligible_grants': [],
            'recommendations': [],
            'regional_advisor': None
        }
        
        # Check for regional advisor if county provided
        if 'county' in user_info:
            advisor_info = get_regional_advisor(user_info['county'])
            if advisor_info:
                eligibility_results['regional_advisor'] = advisor_info
        
        # Basic eligibility criteria (to be enhanced with actual DCNR rules)
        criteria = {
            'Recreation and Conservation': {
                'entity_types': ['municipality', 'county', 'council of governments'],
                'requirements': ['public entity', 'matching funds available']
            },
            'Partnership Grants': {
                'entity_types': ['nonprofit', '501c3', 'educational institution'],
                'requirements': ['environmental mission', 'community benefit']
            },
            'Land Trust Grants': {
                'entity_types': ['land trust', 'conservancy'],
                'requirements': ['accredited or working toward accreditation']
            }
        }
        
        # Check each grant type
        for grant_name, grant_criteria in criteria.items():
            if grant_type and grant_type != grant_name:
                continue
                
            is_eligible = True
            reasons = []
            
            # Check entity type
            user_entity = user_info.get('entity_type', '').lower()
            if not any(etype in user_entity for etype in grant_criteria['entity_types']):
                is_eligible = False
                reasons.append(f"Entity type '{user_entity}' may not qualify")
            
            # Add to results
            if is_eligible:
                eligibility_results['eligible_grants'].append({
                    'grant': grant_name,
                    'confidence': 'High',
                    'notes': 'Meets basic criteria'
                })
            else:
                eligibility_results['ineligible_grants'].append({
                    'grant': grant_name,
                    'reasons': reasons
                })
        
        return eligibility_results
    
    def evaluate_grant_application(self, application_info: Dict) -> Dict:
        """Evaluate grant application and provide approval chances"""
        score = 0
        max_score = 100
        feedback = []
        strengths = []
        weaknesses = []
        
        # Entity Type Score (20 points)
        entity_type = application_info.get('entity_type', '').lower()
        if 'municipality' in entity_type or 'county' in entity_type:
            score += 20
            strengths.append("✅ Municipal/County applicants have access to Keystone Fund")
        elif 'council of governments' in entity_type:
            score += 18
            strengths.append("✅ Council of Governments is a strong eligible applicant")
        elif 'school' in entity_type:
            score += 15
            strengths.append("✅ School districts are eligible applicants")
        elif 'nonprofit' in entity_type or '501c3' in entity_type:
            score += 10
            weaknesses.append("⚠️ Nonprofits limited to environmental stewardship funds only")
        else:
            score += 5
            weaknesses.append("❌ Entity type may need partnership with eligible organization")
        
        # Community Impact Score (20 points)
        footfall = application_info.get('footfall', 0)
        population_served = application_info.get('population_served', 0)
        
        if footfall > 0 or population_served > 0:
            impact_number = max(footfall, population_served)
            if impact_number >= 5000:
                score += 20
                strengths.append(f"✅ Strong community impact: {impact_number:,} people served")
            elif impact_number >= 1000:
                score += 15
                strengths.append(f"✅ Good community impact: {impact_number:,} people served")
            elif impact_number >= 100:
                score += 10
                feedback.append(f"📊 Moderate community impact: {impact_number:,} people served")
            else:
                score += 5
                weaknesses.append(f"❌ Low community impact: only {impact_number} people served")
                feedback.append("💡 Consider partnerships to increase community reach")
        
        # Matching Funds Score (20 points)
        has_matching_funds = application_info.get('has_matching_funds', False)
        match_percentage = application_info.get('match_percentage', 0)
        
        if has_matching_funds:
            if match_percentage >= 100:
                score += 20
                strengths.append("✅ Full dollar-for-dollar match secured")
            elif match_percentage >= 50:
                score += 15
                strengths.append(f"✅ {match_percentage}% match identified")
            else:
                score += 10
                weaknesses.append("⚠️ Partial match may need to be increased")
        else:
            weaknesses.append("❌ No matching funds identified - this is required!")
        
        # Project Readiness Score (20 points)
        has_scope = application_info.get('has_detailed_scope', False)
        has_quotes = application_info.get('has_consultant_quotes', False)
        has_site_control = application_info.get('has_site_control', False)
        
        readiness_score = 0
        if has_scope:
            readiness_score += 7
            strengths.append("✅ Detailed scope of work prepared")
        else:
            weaknesses.append("❌ Need detailed scope of work")
            
        if has_quotes:
            readiness_score += 7
            strengths.append("✅ Consultant quotes obtained")
        else:
            weaknesses.append("❌ Need minimum 2 consultant quotes")
            
        if has_site_control:
            readiness_score += 6
            strengths.append("✅ Site control documented")
        elif application_info.get('project_type', '').lower() in ['master site', 'feasibility']:
            weaknesses.append("❌ Site control required for this project type")
            
        score += readiness_score
        
        # Public Support Score (10 points)
        has_public_support = application_info.get('has_public_support', False)
        has_partnerships = application_info.get('has_partnerships', False)
        
        if has_public_support:
            score += 5
            strengths.append("✅ Public support demonstrated")
        else:
            feedback.append("💡 Consider conducting public meetings or surveys")
            
        if has_partnerships:
            score += 5
            strengths.append("✅ Strong partnerships in place")
        else:
            feedback.append("💡 Consider partnering with other organizations")
        
        # Planning Priorities Score (10 points)
        addresses_equity = application_info.get('addresses_equity', False)
        rehabilitation_project = application_info.get('rehabilitation_project', False)
        
        if addresses_equity:
            score += 5
            strengths.append("✅ Addresses recreation for all/equity")
        if rehabilitation_project:
            score += 5
            strengths.append("✅ Focuses on rehabilitation of existing facilities")
        
        # Calculate approval chances
        if score >= 80:
            approval_chance = "Excellent (80-95%)"
            overall_feedback = "Your application appears very strong! Make sure all documentation is complete."
        elif score >= 65:
            approval_chance = "Good (60-80%)"
            overall_feedback = "Your application has good potential. Address the weaknesses to improve chances."
        elif score >= 50:
            approval_chance = "Moderate (40-60%)"
            overall_feedback = "Your application needs improvement. Focus on addressing major weaknesses."
        elif score >= 35:
            approval_chance = "Low (20-40%)"
            overall_feedback = "Significant improvements needed. Consider partnering or waiting until better prepared."
        else:
            approval_chance = "Very Low (<20%)"
            overall_feedback = "Major issues need to be addressed. Consider seeking technical assistance."
        
        # Add regional advisor recommendation if county provided
        if 'county' in application_info:
            advisor_info = get_regional_advisor(application_info['county'])
            if advisor_info:
                feedback.append(f"💡 Contact your regional advisor {advisor_info['advisor_name']} at {advisor_info['phone']} for guidance")
        
        return {
            'score': score,
            'max_score': max_score,
            'approval_chance': approval_chance,
            'strengths': strengths,
            'weaknesses': weaknesses,
            'feedback': feedback,
            'overall_feedback': overall_feedback
        }

# Initialize the system
rag_system = GrantRAGSystem()

def extract_text_from_pdf(file):
    """Extract text from PDF file"""
    text = ""
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
    return text

def search_all_content(query, documents, grant_data):
    """Search in both uploaded documents and grant data"""
    query_words = query.lower().split()
    results = []
    
    # Check if query mentions a county for regional advisor
    county_match = None
    pa_counties = []
    for region_data in REGIONAL_ADVISORS["regions"].values():
        pa_counties.extend(region_data["counties"])
    
    for word in query_words:
        if word in pa_counties:
            county_match = word
            break
    
    # If county mentioned, add regional advisor info to results
    if county_match:
        advisor_info = get_regional_advisor(county_match)
        if advisor_info:
            advisor_snippet = f"Regional Advisor for {county_match.title()} County: {advisor_info['advisor_name']}, Phone: {advisor_info['phone']}, Email: {advisor_info['email']}"
            results.append((10, "DCNR Regional Advisors", advisor_snippet))
    
    # Search in uploaded documents
    for filename, content in documents.items():
        content_lower = content.lower()
        score = sum(1 for word in query_words if word in content_lower)
        
        if score > 0:
            snippet_start = content_lower.find(query_words[0])
            if snippet_start != -1:
                snippet_start = max(0, snippet_start - 100)
                snippet_end = min(len(content), snippet_start + 500)
                snippet = content[snippet_start:snippet_end]
                results.append((score, f"Document: {filename}", snippet))
    
    # Search in grant data
    grant_text = grant_data.get('general_info', '')
    if grant_text:
        grant_lower = grant_text.lower()
        score = sum(1 for word in query_words if word in grant_lower)
        
        if score > 0:
            snippet_start = grant_lower.find(query_words[0])
            if snippet_start != -1:
                snippet_start = max(0, snippet_start - 100)
                snippet_end = min(len(grant_text), snippet_start + 500)
                snippet = grant_text[snippet_start:snippet_end]
                results.append((score, "PA DCNR Website", snippet))
    
    # Search in planning session transcript
    planning_content = grant_data.get('planning_session_transcript', '')
    if planning_content:
        planning_lower = planning_content.lower()
        score = sum(1 for word in query_words if word in planning_lower)
        
        if score > 0:
            snippet_start = planning_lower.find(query_words[0])
            if snippet_start != -1:
                snippet_start = max(0, snippet_start - 100)
                snippet_end = min(len(planning_content), snippet_start + 500)
                snippet = planning_content[snippet_start:snippet_end]
                results.append((score, "DCNR Planning Session", snippet))
    
    # Sort by relevance
    results.sort(key=lambda x: x[0], reverse=True)
    return results[:5]

def main():
    # Animated header
    st.markdown("""
    <div class="main-header">
        <h1 style="color: white; text-align: center; margin: 0;">
            <span class="floating">🌲</span> PA DCNR Grant Assistant <span class="floating">🌲</span>
        </h1>
        <p style="color: white; text-align: center; font-size: 1.2em; margin-top: 0.5rem;">
            Your AI assistant for Pennsylvania DCNR Community Conservation Partnership Program grants
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Debug info (remove this after fixing)
    with st.expander("🔧 Debug Information"):
        import sys
        st.write("Python Version:", sys.version)
        st.write("OpenAI Library Version:", getattr(OpenAI, '__version__', 'Unknown'))
        st.write("Environment Proxies:", {k: v for k, v in os.environ.items() if 'proxy' in k.lower()})
    
    # Initialize OpenAI client
    client = get_openai_client()
    
    if not client:
        st.error("⚠️ Failed to initialize OpenAI client. Please check your API key configuration.")
        st.stop()
    
    # Load grant data with animation
    if 'grant_data' not in st.session_state or not st.session_state.grant_data:
        with st.spinner("Loading grant information..."):
            progress_bar = st.progress(0)
            for i in range(100):
                time.sleep(0.01)
                progress_bar.progress(i + 1)
            st.session_state.grant_data = rag_system.load_grant_data() or {}
            progress_bar.empty()
    
    # Sidebar with slide-in animation
    with st.sidebar:
        st.markdown('<div class="slide-in">', unsafe_allow_html=True)
        st.header("⚙️ Configuration")
        
        # Status indicator
        if client:
            st.success("✅ AI Assistant Ready!")
        else:
            st.warning("⚠️ AI features disabled - Check API key")
        
        st.divider()
        
        # Regional Advisor Lookup
        st.header("🗺️ Find Your Regional Advisor")
        county_input = st.text_input(
            "Enter your county name",
            placeholder="e.g., Lawrence, Chester, Erie",
            help="Find your DCNR regional advisor by county"
        )
        
        if county_input:
            advisor_info = get_regional_advisor(county_input)
            if advisor_info:
                st.markdown(f"""
                <div class="advisor-card">
                    <h4 style="margin-top: 0;">Your Regional Advisor (Region {advisor_info['region']})</h4>
                    <p><strong>👤 {advisor_info['advisor_name']}</strong></p>
                    <p>📞 {advisor_info['phone']}</p>
                    <p>📧 <a href="mailto:{advisor_info['email']}">{advisor_info['email']}</a></p>
                    <p style="font-size: 0.9em; color: #666;">Serves {len(advisor_info['counties_served'])} counties in your region</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error("County not found. Please check the spelling.")
        
        st.divider()
        
        # Grant Data Status with pulse animation
        st.header("📊 Grant Data Status")
        if st.session_state.grant_data:
            last_update = st.session_state.grant_data.get('last_updated', 'Unknown')
            st.markdown(f'<div class="pulse">ℹ️ Last updated: {last_update}</div>', unsafe_allow_html=True)
            
            if st.button("🔄 Force Update", help="Update grant data from website"):
                with st.spinner("Updating grant data..."):
                    new_data = rag_system.scrape_grant_data()
                    if new_data:
                        st.session_state.grant_data = new_data
                        st.success("✅ Grant data updated!")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
        
        st.divider()
        
        # File upload with animation
        st.header("📄 Upload Documents")
        uploaded_files = st.file_uploader(
            "Upload your grant-related documents",
            type=['pdf', 'txt'],
            accept_multiple_files=True,
            help="Upload PDFs or text files related to your grant application"
        )
        
        if uploaded_files and st.button("🚀 Process Documents", type="primary"):
            st.session_state.documents = {}
            
            progress_text = st.empty()
            progress_bar = st.progress(0)
            
            for idx, file in enumerate(uploaded_files):
                progress_text.text(f"Processing {file.name}...")
                progress_bar.progress((idx + 1) / len(uploaded_files))
                
                if file.name.endswith('.pdf'):
                    text = extract_text_from_pdf(file)
                else:
                    file_bytes = file.read()
                    for encoding in ['utf-8', 'latin-1', 'cp1252']:
                        try:
                            text = file_bytes.decode(encoding)
                            break
                        except:
                            continue
                    else:
                        text = file_bytes.decode('latin-1', errors='ignore')
                
                st.session_state.documents[file.name] = text
                time.sleep(0.3)  # Visual effect
            
            progress_text.empty()
            progress_bar.empty()
            st.success(f"✅ Processed {len(uploaded_files)} documents!")
            st.markdown('<div class="checkmark">✓</div>', unsafe_allow_html=True)
        
        # Eligibility Checker with animations
        st.divider()
        st.header("✅ Eligibility Checker")
        
        with st.form("eligibility_form"):
            entity_type = st.selectbox(
                "Organization Type",
                ["Municipality", "County", "Nonprofit 501(c)(3)", "Land Trust", 
                 "Educational Institution", "Other"],
                help="Select your organization type"
            )
            
            county_for_eligibility = st.text_input(
                "Your County",
                placeholder="e.g., Lawrence",
                help="Enter your county to get regional advisor info"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                has_501c3 = st.checkbox("501(c)(3) Status")
            with col2:
                has_matching_funds = st.checkbox("Matching Funds Available")
            
            if st.form_submit_button("🔍 Check Eligibility", type="primary"):
                with st.spinner("Analyzing eligibility..."):
                    time.sleep(1)  # Animation effect
                    
                user_info = {
                    'entity_type': entity_type,
                    'has_501c3': has_501c3,
                    'has_matching_funds': has_matching_funds,
                    'county': county_for_eligibility
                }
                
                results = rag_system.check_eligibility(user_info)
                
                st.subheader("Eligibility Results:")
                
                # Show regional advisor if county provided
                if results.get('regional_advisor'):
                    st.markdown(f"""
                    <div class="advisor-card">
                        {format_advisor_info(results['regional_advisor'])}
                    </div>
                    """, unsafe_allow_html=True)
                
                if results['eligible_grants']:
                    st.success("✅ Potentially Eligible For:")
                    for grant in results['eligible_grants']:
                        st.markdown(f"""
                        <div class="slide-in" style="padding: 10px; background: #E8F5E9; border-radius: 5px; margin: 5px 0;">
                            • <strong>{grant['grant']}</strong> - {grant['notes']}
                        </div>
                        """, unsafe_allow_html=True)
                
                if results['ineligible_grants']:
                    st.warning("❌ May Not Qualify For:")
                    for grant in results['ineligible_grants']:
                        st.write(f"• **{grant['grant']}** - {', '.join(grant['reasons'])}")
                
                if results['recommendations']:
                    st.info("💡 Recommendations:")
                    for rec in results['recommendations']:
                        st.write(f"• {rec}")
        
        # Grant Evaluation Tool
        st.divider()
        st.header("📊 Grant Evaluation Tool")
        st.markdown("*Evaluate your chances of grant approval*")
        
        with st.form("evaluation_form"):
            eval_entity_type = st.selectbox(
                "Organization Type",
                ["Municipality", "County", "School District", "Nonprofit 501(c)(3)", 
                 "Council of Governments", "Conservation District", "Other"],
                help="Your organization type affects funding eligibility"
            )
            
            eval_county = st.text_input(
                "Your County",
                placeholder="e.g., Lawrence",
                help="Enter your county for regional advisor recommendation"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                footfall = st.number_input(
                    "Daily Visitors/Users",
                    min_value=0,
                    help="Average daily footfall at your facility"
                )
            with col2:
                population = st.number_input(
                    "Population Served",
                    min_value=0,
                    help="Total community population served"
                )
            
            project_type = st.selectbox(
                "Project Type",
                ["Master Site Development Plan", "Comprehensive Recreation Plan",
                 "Feasibility Study", "Conservation Management Plan"],
                help="Type of planning project"
            )
            
            st.markdown("**Project Readiness**")
            col3, col4 = st.columns(2)
            with col3:
                has_scope = st.checkbox("Detailed scope of work prepared")
                has_quotes = st.checkbox("Have 2+ consultant quotes")
                has_matching = st.checkbox("Matching funds secured")
            with col4:
                has_site = st.checkbox("Site control (if applicable)")
                has_public = st.checkbox("Public support demonstrated")
                has_partners = st.checkbox("Partnerships established")
            
            if has_matching:
                match_percent = st.slider(
                    "Match percentage secured",
                    min_value=0,
                    max_value=200,
                    value=100,
                    help="DCNR requires dollar-for-dollar (100%) match"
                )
            else:
                match_percent = 0
            
            st.markdown("**Project Priorities**")
            addresses_equity = st.checkbox("Addresses recreation equity/accessibility")
            is_rehabilitation = st.checkbox("Rehabilitation of existing facilities")
            
            if st.form_submit_button("🎯 Evaluate Application", type="primary"):
                with st.spinner("Evaluating your application..."):
                    time.sleep(1)  # Animation effect
                    
                    eval_info = {
                        'entity_type': eval_entity_type,
                        'county': eval_county,
                        'footfall': footfall,
                        'population_served': population,
                        'project_type': project_type,
                        'has_detailed_scope': has_scope,
                        'has_consultant_quotes': has_quotes,
                        'has_site_control': has_site,
                        'has_matching_funds': has_matching,
                        'match_percentage': match_percent,
                        'has_public_support': has_public,
                        'has_partnerships': has_partners,
                        'addresses_equity': addresses_equity,
                        'rehabilitation_project': is_rehabilitation
                    }
                    
                    results = rag_system.evaluate_grant_application(eval_info)
                    
                    # Display results with visual appeal
                    st.subheader("📈 Evaluation Results")
                    
                    # Score gauge
                    score_percentage = (results['score'] / results['max_score']) * 100
                    if score_percentage >= 80:
                        color = "#4CAF50"  # Green
                    elif score_percentage >= 60:
                        color = "#FFC107"  # Amber
                    else:
                        color = "#F44336"  # Red
                    
                    st.markdown(f"""
                    <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, {color}22, {color}11); border-radius: 10px; margin: 10px 0;">
                        <h1 style="margin: 0; color: {color};">{results['score']}/{results['max_score']}</h1>
                        <p style="margin: 5px 0; font-size: 1.2em; font-weight: bold;">Approval Chance: {results['approval_chance']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Progress bar
                    st.progress(score_percentage / 100)
                    
                    # Strengths
                    if results['strengths']:
                        st.success("**Strengths:**")
                        for strength in results['strengths']:
                            st.write(strength)
                    
                    # Weaknesses
                    if results['weaknesses']:
                        st.error("**Areas for Improvement:**")
                        for weakness in results['weaknesses']:
                            st.write(weakness)
                    
                    # Additional feedback
                    if results['feedback']:
                        st.info("**Recommendations:**")
                        for feedback in results['feedback']:
                            st.write(feedback)
                    
                    # Overall feedback
                    st.markdown(f"""
                    <div class="pulse" style="padding: 15px; background: #E3F2FD; border-radius: 5px; margin-top: 10px;">
                        <strong>Overall Assessment:</strong> {results['overall_feedback']}
                    </div>
                    """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Main chat area with animations
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    # Display chat messages with animation
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(f'<div class="chat-message">{message["content"]}</div>', unsafe_allow_html=True)
    
    # Sample questions carousel
    if not st.session_state.messages:
        st.markdown("### 💬 Try asking me about:")
        
        sample_questions = [
            "I'm from Lawrence County, who is my regional advisor?",
            "What types of DCNR grants are available?",
            "What are the eligibility requirements for Recreation and Conservation grants?",
            "When is the 2025 grant application deadline?",
            "How much matching funding is required?",
            "Can nonprofits apply for DCNR grants?",
            "What documents do I need for the application?",
            "What is a master site development plan?",
            "Who should I contact in Chester County for grant help?",
            "What are the ready-to-go requirements for planning applications?",
            "What types of planning projects does DCNR fund?",
            "I need help from my regional advisor in Erie County"
        ]
        
        # Create animated question cards
        cols = st.columns(3)
        for idx, question in enumerate(sample_questions[:6]):
            with cols[idx % 3]:
                if st.button(f"❓ {question[:30]}...", key=f"sample_{idx}"):
                    st.session_state.messages.append({"role": "user", "content": question})
                    st.rerun()
    
    # Chat input
    if prompt := st.chat_input("Ask about DCNR grants, eligibility, deadlines, regional advisors, or application process"):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(f'<div class="chat-message">{prompt}</div>', unsafe_allow_html=True)
        
        # Generate response with animation
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            
            # Show typing animation
            message_placeholder.markdown('<div class="loading-dots">Thinking</div>', unsafe_allow_html=True)
            
            # Search all content
            search_results = search_all_content(
                prompt, 
                st.session_state.documents,
                st.session_state.grant_data
            )
            
            if client:
                # AI-powered response
                if search_results:
                    # Build context
                    context = "\n\n".join([
                        f"[From {source}]\n{snippet}..."
                        for score, source, snippet in search_results
                    ])
                    
                    # Create prompt
                    system_prompt = """You are an expert grant advisor for Pennsylvania DCNR Community Conservation Partnership Program grants. 
                    Help users understand grant opportunities, eligibility requirements, application processes, deadlines, and connect them with their regional advisors.
                    Be specific and helpful, citing sources when possible. Use emojis occasionally to make responses friendlier.
                    
                    When users mention a Pennsylvania county, always provide their regional advisor's contact information.
                    
                    You can also evaluate grant applications based on these scoring criteria:
                    - Entity Type (20 points): Municipalities/counties score highest, nonprofits limited
                    - Community Impact (20 points): Based on population served or facility usage
                    - Matching Funds (20 points): Dollar-for-dollar match required
                    - Project Readiness (20 points): Scope, quotes, site control
                    - Public Support (10 points): Demonstrated support and partnerships
                    - Planning Priorities (10 points): Equity and rehabilitation projects score higher
                    
                    If asked about approval chances, explain that applications scoring:
                    - 80+ points: Excellent chances (80-95%)
                    - 65-79 points: Good chances (60-80%)
                    - 50-64 points: Moderate chances (40-60%)
                    - Below 50: Need significant improvements
                    
                    Always emphasize the importance of contacting regional advisors early in the grant planning process."""
                    
                    user_prompt = f"""Context from documents and website:
{context}

Question: {prompt}

Please provide a helpful answer based on the context. If a Pennsylvania county is mentioned, include the regional advisor's contact information."""
                    
                    # Get response from OpenAI
                    try:
                        response = client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt}
                            ],
                            max_tokens=700,
                            temperature=0.7
                        )
                        
                        answer = response.choices[0].message.content
                        
                        # Add sources
                        sources = list(set([source for _, source, _ in search_results]))
                        answer += f"\n\n📚 **Sources:** {', '.join(sources)}"
                        
                    except Exception as e:
                        answer = f"Error generating response: {str(e)}"
                else:
                    answer = "I couldn't find specific information about that in the uploaded documents or grant data. Try asking about grant types, eligibility requirements, application deadlines, or your regional advisor by mentioning your county."
            else:
                # Non-AI response when API key is not configured
                answer = "🔍 **Search Results:**\n\n"
                if search_results:
                    for score, source, snippet in search_results[:3]:
                        answer += f"**From {source}:**\n{snippet[:200]}...\n\n"
                    answer += "\n💡 *Configure an OpenAI API key in the main area above for AI-powered answers!*"
                else:
                    answer = """I found no specific matches in the available documents. 

Some general information about PA DCNR grants:
• Recreation and Conservation grants for municipalities and counties
• Partnership grants for nonprofits and educational institutions  
• Land Trust grants for conservation organizations
• Most grants require matching funds
• Contact your regional advisor for guidance

💡 *Configure an OpenAI API key in the main area above for detailed AI-powered answers!*"""
            
            # Display answer with typewriter effect
            message_placeholder.markdown(f'<div class="chat-message">{answer}</div>', unsafe_allow_html=True)
            st.session_state.messages.append({"role": "assistant", "content": answer})
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Footer with animation
    st.markdown("""
    <div style="text-align: center; margin-top: 3rem; padding: 1rem; color: #666;">
        <p class="pulse">Made with ❤️ to help Pennsylvania communities access conservation grants</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
