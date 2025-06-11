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
OPENAI_API_KEY = "sk-your-actual-api-key-here"  # <-- PUT YOUR API KEY HERE

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
                'eligibility_criteria': {}
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
            return None
    
    def load_grant_data(self):
        """Load saved grant data or scrape if needed"""
        if os.path.exists(self.data_file):
            with open(self.data_file, 'rb') as f:
                data = pickle.load(f)
                
            # Check if data is older than 30 days
            last_update = datetime.fromisoformat(data['last_updated'])
            if datetime.now() - last_update > timedelta(days=30):
                return self.scrape_grant_data()
            return data
        else:
            return self.scrape_grant_data()
    
    def check_eligibility(self, user_info: Dict, grant_type: str = None) -> Dict:
        """Check eligibility based on user information"""
        eligibility_results = {
            'eligible_grants': [],
            'ineligible_grants': [],
            'recommendations': []
        }
        
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
        
        # Generate recommendations
        if not eligibility_results['eligible_grants']:
            eligibility_results['recommendations'].append(
                "Consider partnering with an eligible organization"
            )
        
        return eligibility_results

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
    
    # Check if API key is properly set
    if OPENAI_API_KEY == "sk-your-actual-api-key-here":
        st.error("⚠️ OpenAI API key not configured! Please update the OPENAI_API_KEY variable in the code.")
        st.info("Replace 'sk-your-actual-api-key-here' with your actual OpenAI API key at the top of the code.")
        st.stop()
    
    if not client:
        st.error("⚠️ Failed to initialize OpenAI client. Please check your API key and internet connection.")
        
        # Provide troubleshooting steps
        st.info("""
        **Troubleshooting Steps:**
        1. Make sure you have the latest OpenAI library: `pip install "openai>=1.0.0"`
        2. Check that your API key is valid
        3. Try running this in your terminal to test:
        ```python
        from openai import OpenAI
        client = OpenAI(api_key="your-key-here")
        ```
        """)
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
                    'has_matching_funds': has_matching_funds
                }
                
                results = rag_system.check_eligibility(user_info)
                
                st.subheader("Eligibility Results:")
                
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
            "What types of DCNR grants are available?",
            "What are the eligibility requirements for Recreation and Conservation grants?",
            "When are the grant application deadlines?",
            "How much matching funding is required?",
            "Can nonprofits apply for DCNR grants?",
            "What documents do I need for the application?",
            "How can land trusts qualify for funding?"
        ]
        
        # Create animated question cards
        cols = st.columns(3)
        for idx, question in enumerate(sample_questions[:6]):
            with cols[idx % 3]:
                if st.button(f"❓ {question[:30]}...", key=f"sample_{idx}"):
                    st.session_state.messages.append({"role": "user", "content": question})
                    st.rerun()
    
    # Chat input
    if prompt := st.chat_input("Ask about DCNR grants, eligibility, deadlines, or application process"):
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
                    Help users understand grant opportunities, eligibility requirements, application processes, and deadlines.
                    Be specific and helpful, citing sources when possible. Use emojis occasionally to make responses friendlier."""
                    
                    user_prompt = f"""Context from documents and website:
{context}

Question: {prompt}

Please provide a helpful answer based on the context. If discussing eligibility, be specific about requirements."""
                    
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
                    answer = "I couldn't find specific information about that in the uploaded documents or grant data. Try asking about grant types, eligibility requirements, or application deadlines."
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
