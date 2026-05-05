import os
import json
import csv
from datetime import datetime
import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
from google.oauth2 import id_token
from google.auth.transport import requests
from google_auth_oauthlib.flow import Flow

# Import your query factory
from query import create_agent_executor, get_pto_balance, is_balance_query

# optional 3rd-party widget you already use
from streamlit_feedback import streamlit_feedback

# --- Page config ---
st.set_page_config(
    page_title="AI ChatOps Assistant", 
    page_icon="🤖", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for Professional Look ---
st.markdown("""
<style>
    /* Main Header Styling */
    h1 { color: #2e4053; font-weight: 700; }
    
    /* Login Form Card Styling */
    .stAuth {
        border: 1px solid #e0e0e0;
        padding: 30px;
        border-radius: 10px;
        background-color: #ffffff;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        max-width: 400px;
        margin: auto;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #243C3E;
    }
    
    /* Chat Message Styling */
    .stChatMessage {
        padding: 10px;
        border-radius: 8px;
    }
    
    /* Google SSO Button Styling */
    .google-sso-btn {
        background-color: #4285f4;
        color: white;
        padding: 12px 24px;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 10px;
        margin: 10px 0;
    }
    .google-sso-btn:hover {
        background-color: #357ae8;
    }
</style>
""", unsafe_allow_html=True)

# --- Google SSO Configuration ---
def load_google_credentials():
    """Load Google OAuth credentials from google_credentials.json"""
    try:
        with open("google_credentials.json", "r") as f:
            credentials = json.load(f)
            return credentials["web"]
    except FileNotFoundError:
        st.error("❌ google_credentials.json not found!")
        return None
    except Exception as e:
        st.error(f"❌ Error loading Google credentials: {e}")
        return None

def get_user_from_email(email, config):
    """Match Google email with config.yaml user"""
    for username, user_data in config["credentials"]["usernames"].items():
        if user_data.get("email", "").lower() == email.lower():
            return username, user_data
    return None, None

def verify_google_token(token, client_id):
    """Verify Google ID token"""
    try:
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), client_id)
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer.')
        return idinfo
    except Exception as e:
        st.error(f"Token verification failed: {e}")
        return None

# --- Logging configuration ---
LOG_JSONL = "chat_log.jsonl"
LOG_CSV = "chat_log.csv"
CSV_FIELDS = ["timestamp", "user", "query", "response", "feedback"]
MAX_LOG_CHARS = 10000 

def _iso_timestamp(ts):
    if isinstance(ts, datetime):
        return ts.isoformat()
    return str(ts)

def _safe_write_jsonl(entry, path=LOG_JSONL):
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "a", encoding="utf8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print("Failed to append to JSONL log:", e)

def _safe_append_csv(entry, path=LOG_CSV):
    try:
        file_exists = os.path.isfile(path)
        with open(path, "a", encoding="utf8", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=CSV_FIELDS, quoting=csv.QUOTE_ALL)
            if not file_exists:
                writer.writeheader()
            row = {k: entry.get(k, "") for k in CSV_FIELDS}
            writer.writerow(row)
    except Exception as e:
        print("Failed to append to CSV log:", e)

def log_interaction(timestamp, user, query, response, feedback=None):
    """
    Robust logging: write newline-delimited JSON (primary) and append a quoted CSV row (secondary).
    """
    entry = {
        "timestamp": _iso_timestamp(timestamp),
        "user": user,
        "query": query,
        "response": response,
        "feedback": feedback if feedback is not None else "N/A"
    }
    _safe_write_jsonl(entry, LOG_JSONL)
    _safe_append_csv(entry, LOG_CSV)

def clean_response_text(s: str) -> str:
    """
    Make simple cleanups to responses.
    """
    if not isinstance(s, str):
        s = str(s)
    s = s.strip()

    # Remove Llama/Mistral chat template tokens if they appear
    template_tokens = ["<|begin_of_text|>", "<|start_header_id|>", "<|end_header_id|>", 
                       "<|eot_id|>", "<|system|>", "<|user|>", "<|assistant|>", "</s>",
                       "system", "user", "assistant", "[INST]", "[/INST]"]
    for token in template_tokens:
        s = s.replace(token, "")
    
    # If prompt-like tokens appear in the output, try to extract text after 'Answer:'
    suspicious = ["Context:", "Question:", "Answer the Question", "Answer:", "Document 1:"]
    if any(tok in s for tok in suspicious):
        # Try to extract just the answer part
        if "Answer:" in s:
            try:
                # Find the last occurrence of "Answer:" and take text after it
                parts = s.split("Answer:")
                if len(parts) > 1:
                    s = parts[-1].strip()
            except Exception:
                pass
        
        # Remove "Document X:" references if they appear at the start
        if s.startswith("Document"):
            try:
                # Remove lines starting with "Document"
                lines = s.split("\n")
                cleaned_lines = [line for line in lines if not line.strip().startswith("Document")]
                if cleaned_lines:
                    s = "\n".join(cleaned_lines).strip()
            except Exception:
                pass

    return s.strip()

# --- Dummy agent for mock mode ---
class DummyAgentExecutor:
    def __init__(self, username):
        self.username = username

    def invoke(self, payload):
        text = (payload.get("input", "") or "").strip().lower()
        if is_balance_query(text): 
            return {"output": get_pto_balance(self.username)}
        return {"output": "Mock mode: agent not loaded. This is a lightweight test response."}

with open("config.yaml") as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"]
)

# Initialize SSO state
if "sso_authenticated" not in st.session_state:
    st.session_state.sso_authenticated = False

# --- Enhanced Login UI with Google SSO ---
if not st.session_state.get("authentication_status") and not st.session_state.sso_authenticated:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🔐 ChatOps Login")
        
        # Traditional login
        authenticator.login("main")
        
        # Divider
        st.markdown("---")
        st.markdown("<p style='text-align: center;'>OR</p>", unsafe_allow_html=True)
        
        # Google SSO Button
        st.markdown("### 🔑 Single Sign-On")
        
        # Load Google credentials
        google_creds = load_google_credentials()
        
        if google_creds:
            # Using query parameters for OAuth callback
            query_params = st.query_params
            
            if "code" in query_params:
                # Handle OAuth callback
                try:
                    code = query_params["code"]
                    
                    # Exchange code for token
                    flow = Flow.from_client_config(
                        {"web": google_creds},
                        scopes=[
                            "https://www.googleapis.com/auth/userinfo.email",
                            "https://www.googleapis.com/auth/userinfo.profile",
                            "openid"
                        ],
                        redirect_uri=google_creds.get("redirect_uris", ["http://localhost:8501"])[0]
                    )
                    flow.fetch_token(code=code)
                    credentials = flow.credentials
                    
                    # Verify token and get user info
                    idinfo = verify_google_token(credentials.id_token, google_creds["client_id"])
                    
                    if idinfo:
                        email = idinfo.get("email")
                        google_name = idinfo.get("name", email)
                        
                        # Match email with config.yaml
                        username, user_data = get_user_from_email(email, config)
                        
                        if username:
                            # Successful SSO login
                            st.session_state.sso_authenticated = True
                            st.session_state.authentication_status = True
                            st.session_state.username = username
                            st.session_state.name = user_data.get("name", google_name)
                            
                            # Clear query params and rerun
                            st.query_params.clear()
                            st.success(f"✅ Logged in via Google as {st.session_state.name}")
                            st.rerun()
                        else:
                            st.error(f"❌ Email {email} is not registered in the system")
                            st.info("Please contact your administrator to add your email to config.yaml")
                            if st.button("Try Again"):
                                st.query_params.clear()
                                st.rerun()
                    else:
                        st.error("❌ Failed to verify Google token")
                        
                except Exception as e:
                    st.error(f"❌ SSO authentication failed: {e}")
                    if st.button("Back to Login"):
                        st.query_params.clear()
                        st.rerun()
            else:
                # Show Google Sign-In button
                if st.button("🔐 Sign in with Google", key="google_sso_btn", use_container_width=True):
                    try:
                        # Create OAuth flow
                        redirect_uri = google_creds.get("redirect_uris", ["http://localhost:8501"])[0]
                        flow = Flow.from_client_config(
                            {"web": google_creds},
                            scopes=[
                                "https://www.googleapis.com/auth/userinfo.email",
                                "https://www.googleapis.com/auth/userinfo.profile",
                                "openid"
                            ],
                            redirect_uri=redirect_uri
                        )
                        
                        # Get authorization URL
                        auth_url, state = flow.authorization_url(prompt="consent")
                        
                        # Redirect to Google
                        st.markdown(f'<meta http-equiv="refresh" content="0;url={auth_url}">', unsafe_allow_html=True)
                        st.info("🔄 Redirecting to Google Sign-In...")
                        
                    except Exception as e:
                        st.error(f"❌ Failed to initialize Google SSO: {e}")
        else:
            st.warning("⚠️ Google SSO is not configured. Please ensure google_credentials.json exists.")

# --- Authentication Status Checks ---
if st.session_state.get("authentication_status") == False:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.error("❌ Username/password is incorrect")
    st.stop()
elif st.session_state.get("authentication_status") is None and not st.session_state.sso_authenticated:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.expander("ℹ️ Login Help"):
            st.info("Available Users: admin, general, it_support, finance, hr, engineering")
            st.info("Or use Google Sign-In with your registered email")
    st.stop()
elif st.session_state.get("authentication_status") == True or st.session_state.sso_authenticated:
    # ✅ Successfully authenticated - continue with app
    name = st.session_state["name"]
    username = st.session_state["username"]
    user_role = config["credentials"]["usernames"].get(username, {}).get("role", "general")
    
    # --- Improved Header ---
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.title("AI ChatOps Assistant 🤖")
        login_method = "🔑 SSO" if st.session_state.sso_authenticated else "🔐 Password"
        st.caption(f"Logged in as: **{name}** | Role: **{user_role.upper()}** | {login_method}")
    with col_h2:
        # Role Badge visualization (Visual only)
        st.markdown(f"""
            <div style="text-align: right; padding: 10px;">
                <span style="background-color: #e0f7fa; color: #006064; padding: 5px 10px; border-radius: 15px; font-weight: bold; border: 1px solid #b2ebf2;">
                    👤 {user_role.upper()}
                </span>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")

    with st.sidebar:
        st.subheader("👤 User Profile")
        st.info(f"**User:** {username}\n\n**Role:** {user_role}")
        
        st.markdown("---")
        
        # Original Logout Function
        if st.session_state.sso_authenticated:
            if st.button("Logout", key="sso_logout"):
                st.session_state.sso_authenticated = False
                st.session_state.authentication_status = None
                st.session_state.clear()
                st.rerun()
        else:
            authenticator.logout(location="main")
        
        # Sidebar menu for API integrations
        st.markdown("---")
        st.subheader("🚀 Quick Actions")
        
        # Lazy load API manager only when needed
        if st.button("🔧 Open API Tools", key="api_tools_btn", use_container_width=True):
            st.session_state.show_api_tools = True
        
        if st.button("📊 View Analytics", key="analytics_btn", use_container_width=True):
            st.info("Run: streamlit run analytics_enhanced.py --server.port 8502")
        
        # ✅ Knowledge Base Re-indexing Feature
        st.markdown("---")
        st.subheader("📚 Admin Tools")
        
        if user_role in ["admin", "hr"]:  # Only admin/HR can re-index
            if st.button("🔄 Re-index DB", key="reindex_btn", use_container_width=True, type="primary"):
                with st.spinner("🔄 Indexing... (1-2 mins)"):
                    try:
                        import subprocess
                        import sys
                        
                        # Run ingest.py using the same Python interpreter
                        result = subprocess.run(
                            [sys.executable, "ingest.py"],
                            capture_output=True,
                            text=True,
                            timeout=300  # 5 minute timeout
                        )
                        
                        if result.returncode == 0:
                            st.toast("✅ Knowledge base re-indexed!", icon="🎉")
                            st.success("New files are now searchable.")
                            
                            # Show output in expandable section
                            if result.stdout:
                                with st.expander("View Logs"):
                                    st.code(result.stdout, language="text")
                        else:
                            st.error("❌ Re-indexing failed!")
                            if result.stderr:
                                st.code(result.stderr, language="text")
                            
                    except subprocess.TimeoutExpired:
                        st.error("❌ Timeout (>5 min)")
                    except Exception as e:
                        st.error(f"❌ Error: {e}")
            
            st.caption("Click after adding files to `knowledge_base/`")
            
            # Show last ingestion time (if DB exists)
            if os.path.exists("db/chroma.sqlite3"):
                try:
                    last_modified = os.path.getmtime("db/chroma.sqlite3")
                    last_time = datetime.fromtimestamp(last_modified)
                    st.caption(f"🕒 Last indexed: {last_time.strftime('%Y-%m-%d %H:%M')}")
                except Exception:
                    pass  # Silently fail if can't read timestamp
        else:
            st.info("🔒 Admin Access Only")

    # --- Create unique session_state key for this user's agent ---
    agent_key = f"agent_executor_{username}"

    # Decide mock mode
    MOCK_AGENT = os.environ.get("MOCK_AGENT", "0") in ("1", "true", "True")
    
    # If the correct user's agent isn't loaded, build it
    if agent_key not in st.session_state:
        # Clear out any stale agents from other users first for security
        for key in list(st.session_state.keys()):
            if key.startswith("agent_executor_"):
                del st.session_state[key]

        if MOCK_AGENT:
            st.info("Running in MOCK_AGENT mode — LLM will not be loaded.")
            st.session_state[agent_key] = DummyAgentExecutor(username)
        else:
            with st.spinner(f"🤖 Loading AI agent for {name}..."):
                try:
                    st.session_state[agent_key] = create_agent_executor(user_role, username)
                    st.success("AI agent loaded successfully!")
                except Exception as e:
                    st.error(f"Failed to load local LLM agent: {e}")
                    st.warning("Falling back to a safe mock agent.")
                    st.session_state[agent_key] = DummyAgentExecutor(username)
    
    # Get the correct agent for the currently logged-in user
    agent_executor = st.session_state[agent_key]

    # --- Chat history state ---
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": f"Hello {name}! 👋 How can I help you with our company knowledge base today?", "message_id": "initial"}
        ]
    
    # Handle suggested query clicks
    if "suggested_query" in st.session_state:
        suggested = st.session_state.suggested_query
        del st.session_state.suggested_query
        # Add to messages and process
        st.session_state.messages.append({"role": "user", "content": suggested, "message_id": f"user_{len(st.session_state.messages)}"})
        # The query will be processed in the normal flow below

    # Render chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if prompt := st.chat_input("Ask a question about your documents..."):
        st.session_state.messages.append({"role": "user", "content": prompt, "message_id": f"user_{len(st.session_state.messages)}"})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            response_placeholder.markdown("Thinking...")

            try:
                # Invoke the correct agent
                response_dict = agent_executor.invoke({"input": prompt})
                raw_answer = response_dict.get("output", "")
                
                # Clean the answer
                cleaned = clean_response_text(raw_answer)
                if not cleaned:
                    cleaned = "I do not have that information in the knowledge base."

                response_placeholder.markdown(cleaned)

                message_id = f"assistant_{len(st.session_state.messages)}"
                st.session_state.messages.append({"role": "assistant", "content": cleaned, "message_id": message_id})

                # --- ADD SUGGESTED FOLLOW-UP PROMPTS ---
                if "do not have that information" not in cleaned.lower():
                    # Generate role-specific suggestions
                    suggestions = []
                    
                    if user_role == "admin":
                        suggestions = [
                            "What is the PTO policy?",
                            "How do I deploy code to production?",
                            "What is the bonus policy?"
                        ]
                    elif user_role == "hr":
                        suggestions = [
                            "What is the PTO policy?",
                            "What are performance reviews?",
                            "What is the bonus policy?"
                        ]
                    elif user_role == "it_support":
                        suggestions = [
                            "How do I troubleshoot the VPN?",
                            "What is the guest WiFi password?",
                            "What is the PTO policy?"
                        ]
                    elif user_role == "finance":
                        suggestions = [
                            "What is the monthly finance approval limit?",
                            "What is the PTO policy?",
                            "What is the leave carry forward policy?"
                        ]
                    elif user_role == "engineering":
                        suggestions = [
                            "How do I deploy code to production?",
                            "What is the PTO policy?",
                            "What is the leave carry forward policy?"
                        ]
                    else:  # general
                        suggestions = [
                            "What is the PTO policy?",
                            "What is the leave carry forward policy?",
                            "What is the company policy?"
                        ]
                    
                    # Display suggestions
                    if suggestions:
                        st.markdown("#### 💡 Suggested Questions:")
                        cols = st.columns(len(suggestions))
                        for idx, suggestion in enumerate(suggestions):
                            with cols[idx]:
                                if st.button(suggestion, key=f"suggest_{message_id}_{idx}"):
                                    # Trigger a rerun with this query
                                    st.session_state.suggested_query = suggestion
                                    st.rerun()
                # --- END SUGGESTED PROMPTS ---

                # --- FIXED REDACTION LOGIC ---
                logged_response = cleaned if len(cleaned) <= MAX_LOG_CHARS else (cleaned[:MAX_LOG_CHARS] + "…[truncated]")
                
                # Define sensitive information patterns and which roles can access them
                sensitive_patterns = {
                    "wifi": ["admin", "it_support"],
                    "password": ["admin", "it_support"],
                    "pass": ["admin", "it_support"],
                    "credentials": ["admin"],
                    "server credentials": ["admin"],
                }
                
                # Check if query contains sensitive terms and if user has access
                should_redact = False
                prompt_lower = prompt.lower()
                
                for sensitive_term, allowed_roles in sensitive_patterns.items():
                    if sensitive_term in prompt_lower:
                        if user_role not in allowed_roles:
                            should_redact = True
                            break
                
                if should_redact:
                    logged_response = "[REDACTED: sensitive information]"
                # --- END OF FIXED REDACTION LOGIC ---

                log_interaction(
                    timestamp=datetime.now(),
                    user=username,
                    query=prompt,
                    response=logged_response,
                    feedback="N/A"
                )

            except Exception as e:
                error_message = f"An error occurred: {e}"
                response_placeholder.error(error_message)
                message_id = f"assistant_{len(st.session_state.messages)}"
                st.session_state.messages.append({"role": "assistant", "content": error_message, "message_id": message_id})
                log_interaction(
                    timestamp=datetime.now(),
                    user=username,
                    query=prompt,
                    response=f"ERROR: {error_message}",
                    feedback="N/A"
                )

    # --- Feedback Widget ---
    last_assistant_message = next((msg for msg in reversed(st.session_state.messages) if msg["role"] == "assistant"), None)
    if last_assistant_message and last_assistant_message["message_id"] != "initial":
        feedback = streamlit_feedback(
            feedback_type="thumbs",
            optional_text_label="[Optional] Provide additional feedback",
            key=f"feedback_{last_assistant_message['message_id']}",
        )

        if feedback:
            log_interaction(
                timestamp=datetime.now(),
                user=username,
                query=f"FEEDBACK for msg_id: {last_assistant_message['message_id']}",
                response=last_assistant_message["content"],
                feedback=feedback.get("score")
            )
            st.toast("Thank you for your feedback!", icon="✅")
    
    # --- API Integration Section (Collapsible Expander at Bottom) ---
    if st.session_state.get("show_api_tools", False):
        st.markdown("---")
        with st.expander("🔗 API Integrations & Tools", expanded=True):
            # Lazy load API manager
            try:
                from api_integrations import APIManager
                
                if "api_manager" not in st.session_state:
                    st.session_state.api_manager = APIManager()
                
                api_manager = st.session_state.api_manager
                
                # FIXED: Properly set API manager in query.py
                try:
                    from query import set_api_manager
                    set_api_manager(api_manager)
                except Exception as e:
                    print(f"Warning: Could not set API manager: {e}")
                
                api_tab1, api_tab2, api_tab3 = st.tabs(["👤 HR System", "🎫 Tickets", "📊 API Stats"])

                with api_tab1:
                    st.subheader("👤 Employee Information")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button("📋 Get My Employee Info", key="get_emp_info_btn", use_container_width=True):
                            emp_result = api_manager.fetch_employee_data(username)
                            if emp_result["status"] == "success":
                                emp = emp_result["data"]
                                st.success(f"✅ Found employee: {emp['name']}")
                                col_emp1, col_emp2 = st.columns(2)
                                with col_emp1:
                                    st.metric("Role", emp["role"])
                                    st.metric("Department", emp["department"])
                                with col_emp2:
                                    st.metric("PTO Balance", f"{emp['pto_balance']} days")
                                    st.metric("Sick Days", f"{emp['sick_days']} days")
                                st.info(f"📧 Email: {emp['email']}")
                            else:
                                st.error(emp_result["message"])
                    
                    with col2:
                        st.markdown("**Update PTO**")
                        pto_days = st.number_input("Days to use:", min_value=0, max_value=30, value=1, key="pto_input")
                        if st.button("✅ Use PTO Days", key="use_pto_btn", use_container_width=True):
                            pto_result = api_manager.hr_api.update_pto(username, pto_days)
                            if pto_result["status"] == "success":
                                st.success(f"✅ PTO Updated!\nOld: {pto_result['old_balance']} → New: {pto_result['new_balance']}")
                            else:
                                st.error(pto_result["message"])

                # ✅ ENHANCED TICKETS TAB WITH SUPPORT TEAM FEATURES
                with api_tab2:
                    st.subheader("🎫 Support Tickets")
                    
                    # Check if user is admin or IT support
                    if user_role in ["admin", "it_support"]:
                        # Support Team View
                        support_tab1, support_tab2 = st.tabs(["📋 All Tickets (Support View)", "🎫 My Tickets"])
                        
                        with support_tab1:
                            st.markdown("**Support Team Dashboard**")
                            
                            # Get ticket statistics
                            stats_result = api_manager.get_ticket_stats()
                            if stats_result["status"] == "success":
                                stats = stats_result["stats"]
                                
                                # Show metrics
                                col1, col2, col3, col4 = st.columns(4)
                                col1.metric("Total Tickets", stats["total"])
                                col2.metric("Open", stats["open"])
                                col3.metric("In Progress", stats["in_progress"])
                                col4.metric("Resolved", stats["resolved"])
                                
                                st.markdown("---")
                            
                            # Filter options
                            col1, col2 = st.columns(2)
                            with col1:
                                filter_status = st.selectbox(
                                    "Filter by Status",
                                    ["All", "open", "in_progress", "resolved", "closed"],
                                    key="support_filter_status"
                                )
                            with col2:
                                filter_priority = st.selectbox(
                                    "Filter by Priority",
                                    ["All", "critical", "high", "medium", "low"],
                                    key="support_filter_priority"
                                )
                            
                            # Get all tickets
                            if st.button("🔄 Refresh Tickets", key="refresh_all_tickets", use_container_width=True):
                                st.rerun()
                            
                            all_tickets_result = api_manager.ticket_api.list_all_tickets()
                            
                            if all_tickets_result["status"] == "success":
                                tickets = all_tickets_result["tickets"]
                                
                                # Apply filters
                                if filter_status != "All":
                                    tickets = [t for t in tickets if t["status"] == filter_status]
                                if filter_priority != "All":
                                    tickets = [t for t in tickets if t["priority"] == filter_priority]
                                
                                if tickets:
                                    st.markdown(f"**Showing {len(tickets)} ticket(s)**")
                                    
                                    for ticket in tickets:
                                        # Color code by priority
                                        priority_colors = {
                                            "critical": "🔴",
                                            "high": "🟠",
                                            "medium": "🟡",
                                            "low": "🟢"
                                        }
                                        priority_icon = priority_colors.get(ticket["priority"], "⚪")
                                        
                                        with st.expander(
                                            f"{priority_icon} [{ticket['status'].upper()}] {ticket['ticket_id']}: {ticket['title']} (by {ticket['reporter']})"
                                        ):
                                            col1, col2 = st.columns(2)
                                            
                                            with col1:
                                                st.write(f"**Reporter:** {ticket['reporter']}")
                                                st.write(f"**Priority:** {ticket['priority']}")
                                                st.write(f"**Status:** {ticket['status']}")
                                                st.write(f"**Created:** {ticket['created_at'][:19]}")
                                                
                                                if ticket.get("assignee"):
                                                    st.write(f"**Assigned to:** {ticket['assignee']}")
                                                if ticket.get("updated_at"):
                                                    st.write(f"**Updated:** {ticket['updated_at'][:19]}")
                                            
                                            with col2:
                                                st.markdown("**Actions:**")
                                                
                                                # Assign ticket
                                                current_assignee = ticket.get("assignee", "Unassigned")
                                                assignee_options = ["Unassigned", "it_support", "admin", "support_team"]
                                                assignee_index = assignee_options.index(current_assignee) if current_assignee in assignee_options else 0
                                                
                                                assignee = st.selectbox(
                                                    "Assign to:",
                                                    assignee_options,
                                                    index=assignee_index,
                                                    key=f"assign_{ticket['ticket_id']}"
                                                )
                                                
                                                if st.button("👤 Assign", key=f"btn_assign_{ticket['ticket_id']}"):
                                                    if assignee != "Unassigned" and assignee != current_assignee:
                                                        result = api_manager.ticket_api.assign_ticket(
                                                            ticket['ticket_id'],
                                                            assignee,
                                                            username
                                                        )
                                                        if result["status"] == "success":
                                                            st.success(result["message"])
                                                            st.rerun()
                                                        else:
                                                            st.error(result["message"])
                                                
                                                # Update status
                                                new_status = st.selectbox(
                                                    "Update Status:",
                                                    ["open", "in_progress", "resolved", "closed"],
                                                    index=["open", "in_progress", "resolved", "closed"].index(ticket["status"]),
                                                    key=f"status_{ticket['ticket_id']}"
                                                )
                                                
                                                if st.button("✅ Update Status", key=f"btn_status_{ticket['ticket_id']}"):
                                                    if new_status != ticket["status"]:
                                                        result = api_manager.ticket_api.update_ticket_status(
                                                            ticket['ticket_id'],
                                                            new_status,
                                                            username
                                                        )
                                                        if result["status"] == "success":
                                                            st.success(result["message"])
                                                            st.rerun()
                                                        else:
                                                            st.error(result["message"])
                                else:
                                    st.info("No tickets match the selected filters")
                            else:
                                st.error("Failed to load tickets")
                        
                        with support_tab2:
                            st.markdown("**My Tickets**")
                            
                            # Create Ticket Section
                            with st.expander("🎫 Create New Ticket", expanded=False):
                                st.markdown("**Submit a support request**")
                                ticket_title = st.text_input("Ticket Title", placeholder="Describe your issue...", key="ticket_title_support")
                                ticket_priority = st.selectbox("Priority", ["low", "medium", "high", "critical"], key="ticket_priority_support")
                                
                                if st.button("🎫 Create Ticket", key="create_ticket_support_btn"):
                                    if ticket_title:
                                        ticket_result = api_manager.create_ticket(
                                            title=ticket_title,
                                            description=f"Ticket created by {name}",
                                            priority=ticket_priority,
                                            reporter=username
                                        )
                                        if ticket_result["status"] == "success":
                                            st.success(ticket_result["message"])
                                            with st.expander("✅ View Created Ticket", expanded=True):
                                                st.json(ticket_result["ticket"])
                                        else:
                                            st.error(ticket_result["message"])
                                    else:
                                        st.warning("Please enter a ticket title")
                            
                            # Divider
                            st.markdown("---")
                            st.markdown("**My Created Tickets**")
                            
                            # List My Tickets
                            if st.button("📋 List My Tickets", key="list_my_tickets_support"):
                                tickets_result = api_manager.list_tickets(username)
                                if tickets_result["status"] == "success" and tickets_result["count"] > 0:
                                    for ticket in tickets_result["tickets"]:
                                        with st.expander(f"🎫 {ticket['ticket_id']}: {ticket['title']}"):
                                            st.write(f"**Status:** {ticket['status']}")
                                            st.write(f"**Priority:** {ticket['priority']}")
                                            st.write(f"**Created:** {ticket['created_at'][:19]}")
                                            if ticket.get("assignee"):
                                                st.write(f"**Assigned to:** {ticket['assignee']}")
                                            if ticket["status"] in ["resolved", "closed"]:
                                                st.success("✅ Ticket has been resolved!")
                                else:
                                    st.info("No tickets found")
                    
                    else:
                        # Regular User View (non-support)
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("**Create New Ticket**")
                            ticket_title = st.text_input("Ticket Title", placeholder="Describe your issue...", key="ticket_title_input")
                            ticket_priority = st.selectbox("Priority", ["low", "medium", "high", "critical"], key="ticket_priority_select")
                            
                            if st.button("🎫 Create Ticket", key="create_ticket_btn"):
                                if ticket_title:
                                    ticket_result = api_manager.create_ticket(
                                        title=ticket_title,
                                        description=f"Ticket created by {name}",
                                        priority=ticket_priority,
                                        reporter=username
                                    )
                                    if ticket_result["status"] == "success":
                                        st.success(ticket_result["message"])
                                        st.json(ticket_result["ticket"])
                                    else:
                                        st.error(ticket_result["message"])
                                else:
                                    st.warning("Please enter a ticket title")
                        
                        with col2:
                            st.markdown("**My Tickets**")
                            if st.button("📋 List My Tickets", key="list_tickets_btn"):
                                tickets_result = api_manager.list_tickets(username)
                                if tickets_result["status"] == "success" and tickets_result["count"] > 0:
                                    for ticket in tickets_result["tickets"]:
                                        with st.expander(f"🎫 {ticket['ticket_id']}: {ticket['title']}"):
                                            st.write(f"**Status:** {ticket['status']}")
                                            st.write(f"**Priority:** {ticket['priority']}")
                                            st.write(f"**Created:** {ticket['created_at'][:19]}")
                                            if ticket.get("assignee"):
                                                st.write(f"**Assigned to:** {ticket['assignee']}")
                                            if ticket["status"] in ["resolved", "closed"]:
                                                st.success("✅ Ticket has been resolved!")
                                else:
                                    st.info("No tickets found")

                with api_tab3:
                    st.subheader("📊 System Statistics")
                    
                    stats = api_manager.get_api_stats()
                    
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Total API Calls", stats["total_calls"])
                    col2.metric("Successful", stats["successful"])
                    col3.metric("Failed", stats["failed"])
                    col4.metric("Success Rate", f"{stats['success_rate']:.1f}%")
                    
                    if stats["recent_calls"]:
                        st.markdown("**Recent API Calls**")
                        for call in reversed(stats["recent_calls"][-5:]):
                            status_emoji = "✅" if call["status"] == "success" else "❌"
                            st.write(f"{status_emoji} `{call['service']}` → `{call['method']}` at {call['timestamp']}")
            
            except ImportError:
                st.warning("⚠️ API integrations module not found. This is optional and doesn't affect core functionality.")
            except Exception as e:
                st.error(f"Error loading API tools: {e}")