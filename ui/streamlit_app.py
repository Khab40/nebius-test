import os, json, requests, streamlit as st

st.set_page_config(page_title="Repo Summarizer", page_icon="🧠", layout="centered")

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
DEFAULT_REPO = "https://github.com/psf/requests"

st.title("🧠 GitHub Repo Summarizer")
st.caption("Enter a public GitHub repository URL. The UI calls the FastAPI backend and shows the LLM-generated summary.")

repo_url = st.text_input(
    "GitHub repository URL",
    value=DEFAULT_REPO,
    placeholder="https://github.com/<owner>/<repo>",
)

col1, col2 = st.columns([1, 1])
with col1:
    run = st.button("Summarize", type="primary")
with col2:
    ping = st.button("Ping API")

if ping:
    try:
        r = requests.get(f"{API_BASE_URL}/health", timeout=10)
        st.success(f"API OK: {r.status_code} {r.text}")
    except Exception as e:
        st.error(f"API not reachable: {e}")

if run:
    if not repo_url.strip():
        st.warning("Please enter a GitHub repository URL.")
        st.stop()

    with st.spinner("Summarizing…"):
        try:
            resp = requests.post(
                f"{API_BASE_URL}/summarize",
                json={"github_url": repo_url.strip()},
                timeout=180,
            )
        except Exception as e:
            st.error(f"Request failed: {e}")
            st.stop()

    if resp.status_code >= 400:
        try:
            err = resp.json()
        except Exception:
            err = {"status": "error", "message": resp.text}
        st.error(f"Error {resp.status_code}: {err.get('message', resp.text)}")
        st.stop()

    data = resp.json()

    st.subheader("Summary")
    st.write(data.get("summary", ""))

    st.subheader("Technologies")
    tech = data.get("technologies", []) or []
    st.write(", ".join(tech) if tech else "—")

    st.subheader("Structure")
    st.write(data.get("structure", ""))

    with st.expander("Raw JSON"):
        st.code(json.dumps(data, indent=2), language="json")