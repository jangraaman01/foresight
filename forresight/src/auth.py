"""Simple password login for FORESIGHT.

Users live in .streamlit/secrets.toml as salted PBKDF2 hashes, never as
plain-text passwords. See the README steps for how to create one.
"""

import hashlib
import hmac

import streamlit as st

ITERATIONS = 200_000


def make_hash(password: str, salt_hex: str) -> str:
    """Return the PBKDF2-SHA256 hash of a password as a hex string."""
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        ITERATIONS,
    ).hex()


def _load_users() -> dict:
    try:
        return dict(st.secrets["users"])
    except Exception:
        return {}


def _check_password(username: str, password: str) -> bool:
    stored = _load_users().get(username.strip())
    if not stored or "$" not in stored:
        # Still do the work so timing doesn't reveal valid usernames.
        make_hash(password, "00" * 16)
        return False
    salt_hex, expected = stored.split("$", 1)
    return hmac.compare_digest(make_hash(password, salt_hex), expected)


def initialize_auth() -> None:
    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault("username", "")


def is_authenticated() -> bool:
    return bool(st.session_state.get("authenticated", False))


def show_login() -> None:
    """Render the login screen (hides the sidebar)."""
    st.markdown(
        "<style>[data-testid='stSidebar'],"
        "[data-testid='stSidebarNav'],"
        "[data-testid='collapsedControl']{display:none;}</style>",
        unsafe_allow_html=True,
    )

    _, middle, _ = st.columns([1, 1.2, 1])
    with middle:
        st.markdown("## 📊 FORESIGHT")
        st.caption("Sign in to continue")

        if not _load_users():
            st.error(
                "No users configured. Add a [users] section to "
                ".streamlit/secrets.toml."
            )
            return

        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button(
                "Sign in", use_container_width=True
            )

        if submitted:
            if _check_password(username, password):
                st.session_state["authenticated"] = True
                st.session_state["username"] = username.strip()
                st.rerun()
            else:
                st.error("Incorrect username or password.")


def logout() -> None:
    st.session_state["authenticated"] = False
    st.session_state["username"] = ""
    st.rerun()


def require_login() -> None:
    """Call at the top of app.py and of EVERY file in pages/."""
    initialize_auth()
    if not is_authenticated():
        show_login()
        st.stop()


def sidebar_user() -> None:
    """Show the signed-in user and a logout button in the sidebar."""
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"👤 **{st.session_state.get('username', 'User')}**")
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        logout()