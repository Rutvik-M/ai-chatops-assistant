import os
import streamlit as st
try:
    from streamlit_google_auth import Authenticate
except ImportError:
    st.error("❌ CRITICAL: `streamlit-google-auth` is not installed.")
    st.stop()

# Global authenticator instance
_authenticator = None

def get_authenticator():
    """Get or create authenticator instance (singleton pattern)"""
    global _authenticator
    
    creds_file = 'google_credentials.json'
    if not os.path.exists(creds_file):
        st.error(f"❌ FILE MISSING: Could not find '{creds_file}' in the root folder.")
        return None

    if _authenticator is None:
        try:
            # Initialize Google Authenticator
            # We use a unique cookie name to avoid conflicts
            _authenticator = Authenticate(
                secret_credentials_path=creds_file,
                cookie_name='chatbot_google_cookie',
                cookie_key='google_auth_signature_key',
                redirect_uri='http://localhost:8501',
                cookie_expiry_days=30
            )
        except Exception as e:
            st.error(f"❌ ERROR initializing Google Auth: {e}")
            return None
    
    return _authenticator

def google_auth():
    """
    Handle Google SSO authentication
    """
    try:
        authenticator = get_authenticator()
        if authenticator is None:
            return None
        
        # Check cookie status
        authenticator.check_authentification()
        
        # If not connected, show login button
        if not st.session_state.get('connected', False):
            authenticator.login()
            return None
        else:
            # User is authenticated
            user_info = st.session_state.get('user_info', {})
            return {
                'email': user_info.get('email', 'unknown@email.com'),
                'name': user_info.get('name', 'Unknown User'),
                'picture': user_info.get('picture', ''),
                'role': 'general'
            }
    
    except Exception as e:
        st.error(f"❌ Google SSO Execution Error: {e}")
        return None

def logout_button():
    """Handle logout for Google SSO"""
    global _authenticator
    
    # 1. Delete Cookie
    try:
        authenticator = get_authenticator()
        if authenticator:
            authenticator.cookie_manager.delete('chatbot_google_cookie')
    except Exception as e:
        pass

    # 2. Clear Session
    keys_to_clear = ['connected', 'user_info', 'google_auth_initialized']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    _authenticator = None