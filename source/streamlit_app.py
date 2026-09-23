"""mini-RAG demo UI.

Talks to the FastAPI backend over HTTP, so start the API first:
    uvicorn main:app --reload --port 8000
    streamlit run streamlit_app.py
"""
import os
import re
import requests
import streamlit as st

DEFAULT_API_URL = os.getenv("MINIRAG_API_URL", "http://localhost:8000")
SAMPLE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples", "story.txt")
MIME_TYPES = {"txt": "text/plain", "pdf": "application/pdf"}

st.set_page_config(page_title="mini-RAG", page_icon="🔎", layout="wide")

# --------------------------------------------------------------------------- API helpers

def api(method: str, path: str, **kwargs):
    """Call the backend. Returns (ok, json_or_error_message)."""
    url = st.session_state.api_url.rstrip("/") + path
    try:
        response = requests.request(method, url, timeout=kwargs.pop("timeout", 300), **kwargs)
    except requests.RequestException as e:
        return False, f"Cannot reach the API at {url}: {e}"
    try:
        body = response.json()
    except ValueError:
        body = {"signal": response.text}
    if response.ok:
        return True, body
    return False, body.get("signal") or body.get("detail") or str(body)

def upload_file(project_id: str, name: str, data: bytes):
    mime_type = MIME_TYPES.get(name.rsplit(".", 1)[-1].lower(), "application/octet-stream")
    return api("POST", f"/api/v1/data/upload/{project_id}", files={"file": (name, data, mime_type)})

def ingest(project_id: str, files: list, chunk_size: int, overlap: int, do_reset: bool):
    """upload -> process -> index, with a live status box."""
    with st.status("Building the knowledge base…", expanded=True) as status:
        for name, data in files:
            st.write(f"⬆️ Uploading **{name}**")
            ok, body = upload_file(project_id, name, data)
            if not ok:
                status.update(label=f"Upload failed: {body}", state="error")
                return

        st.write("✂️ Splitting documents into chunks")
        ok, body = api("POST", f"/api/v1/data/process/{project_id}",
                       json={"chunk_size": chunk_size, "overlap": overlap, "do_reset": int(do_reset)})
        if not ok:
            status.update(label=f"Processing failed: {body}", state="error")
            return
        st.write(f"→ {body['inserted_chunks']} chunks from {body['processed_files']} file(s)")

        st.write("🧮 Embedding chunks into the vector index")
        ok, body = api("POST", f"/api/v1/nlp/index/push/{project_id}", json={"do_reset": 1})
        if not ok:
            status.update(label=f"Indexing failed: {body}", state="error")
            return
        st.write(f"→ {body['inserted_items_count']} vectors indexed")

        status.update(label="Knowledge base ready — ask a question in the Chat tab.", state="complete")

def render_sources(documents: list):
    for i, doc in enumerate(documents, start=1):
        meta = doc.get("metadata") or {}
        source = meta.get("source", "unknown")
        page = f" · page {meta['page']}" if meta.get("page") else ""
        with st.expander(f"[{i}] {source}{page} — score {doc['score']:.3f}"):
            st.progress(min(max(doc["score"], 0.0), 1.0))
            st.write(doc["text"])

# --------------------------------------------------------------------------- Sidebar

if "api_url" not in st.session_state:
    st.session_state.api_url = DEFAULT_API_URL
if "chats" not in st.session_state:
    st.session_state.chats = {}

with st.sidebar:
    st.title("🔎 mini-RAG")
    st.caption("Upload documents, then chat with them.")

    st.text_input("API URL", key="api_url")
    health_ok, health = api("GET", "/api/v1/", timeout=5)

    if health_ok:
        st.success(f"API online · v{health['app_version']}")
        col1, col2 = st.columns(2)
        col1.metric("Generation", health["generation_backend"])
        col2.metric("Embeddings", health["embedding_backend"])
        st.caption(f"Model: `{health['generation_model'] or 'extractive'}` · "
                   f"Embeddings: `{health['embedding_model']}` · DB: {health['database']}")
        for warning in health.get("warnings", []):
            st.warning(warning)
    else:
        st.error(health)
        st.info("Start the backend from the `source/` folder:\n\n`uvicorn main:app --reload --port 8000`")
        st.stop()

    st.divider()
    _, projects_body = api("GET", "/api/v1/projects", timeout=10)
    existing = projects_body.get("projects", []) if isinstance(projects_body, dict) else []

    new_project = st.text_input("New project ID", placeholder="letters and digits only")
    options = sorted(set(existing) | ({new_project} if new_project else set())) or ["demo"]
    default_index = options.index(new_project) if new_project in options else 0
    project_id = st.selectbox("Project", options, index=default_index)

    if not re.fullmatch(r"[A-Za-z0-9]+", project_id):
        st.error("Project ID must be alphanumeric.")
        st.stop()

    top_k = st.slider("Chunks to retrieve (top-k)", 1, 10, 4)
    show_prompt = st.toggle("Show the full LLM prompt", value=False)

    if st.button("🧹 Clear chat", width="stretch"):
        st.session_state.chats[project_id] = []

chat_history = st.session_state.chats.setdefault(project_id, [])
question = st.chat_input(f"Ask about the documents in '{project_id}'…")

# --------------------------------------------------------------------------- Tabs

tab_chat, tab_docs, tab_search = st.tabs(["💬 Chat", "📄 Documents", "🔍 Search"])

with tab_docs:
    st.subheader(f"Documents in `{project_id}`")

    uploads = st.file_uploader("Upload .txt or .pdf files", type=["txt", "pdf"], accept_multiple_files=True)

    col1, col2, col3 = st.columns(3)
    chunk_size = col1.number_input("Chunk size (characters)", 100, 4000, 800, step=100)
    overlap = col2.number_input("Chunk overlap", 0, 1000, 100, step=25)
    do_reset = col3.checkbox("Rebuild from scratch", value=True,
                             help="Delete existing chunks for this project before re-processing.")

    col_a, col_b = st.columns(2)
    if col_a.button("🚀 Upload & index", type="primary", disabled=not uploads, width="stretch"):
        ingest(project_id, [(f.name, f.getvalue()) for f in uploads], chunk_size, overlap, do_reset)

    if col_b.button("📘 Load the sample story", width="stretch", disabled=not os.path.exists(SAMPLE_FILE)):
        # don't upload a second copy if the project already has it; just re-process and re-index
        ok_current, current = api("GET", f"/api/v1/data/assets/{project_id}")
        has_sample = ok_current and any(a["file_id"].endswith("_story.txt") for a in current["assets"])
        with open(SAMPLE_FILE, "rb") as f:
            ingest(project_id, [] if has_sample else [("story.txt", f.read())], chunk_size, overlap, do_reset)

    st.divider()
    ok_assets, assets = api("GET", f"/api/v1/data/assets/{project_id}")
    ok_info, info = api("GET", f"/api/v1/nlp/index/info/{project_id}")
    collection = (info or {}).get("collection_info") if ok_info else None

    m1, m2, m3 = st.columns(3)
    m1.metric("Files", len(assets["assets"]) if ok_assets else "—")
    m2.metric("Chunks (MongoDB)", assets["chunks_count"] if ok_assets else "—")
    m3.metric("Vectors (Qdrant)", collection["points_count"] if collection else 0)

    if ok_assets and assets["assets"]:
        st.dataframe(
            [{"File ID": a["file_id"], "Size (KB)": round((a["size"] or 0) / 1024, 1), "Uploaded": a["pushed_at"][:19]}
             for a in assets["assets"]],
            width="stretch", hide_index=True,
        )
    elif ok_assets:
        st.info("No files yet — upload some, or load the sample story.")

with tab_search:
    st.subheader("Semantic search")
    st.caption("Raw retrieval: the chunks the LLM would see for this query.")
    query = st.text_input("Query", placeholder="e.g. Who is Alan?")
    if query:
        ok, body = api("POST", f"/api/v1/nlp/index/search/{project_id}", json={"text": query, "limit": top_k})
        if ok:
            render_sources(body["results"])
        else:
            st.warning(f"{body} — have you indexed documents in this project?")

with tab_chat:
    if not chat_history and not question:
        st.info("Ask anything about the documents in this project. "
                "No documents yet? Open the **Documents** tab and load the sample story.")

    for message in chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("documents"):
                render_sources(message["documents"])

if question:
    chat_history.append({"role": "user", "content": question})
    with tab_chat:
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("Retrieving and thinking…"):
                ok, body = api("POST", f"/api/v1/nlp/index/answer/{project_id}",
                               json={"text": question, "limit": top_k})
            if ok:
                st.markdown(body["answer"])
                render_sources(body["documents"])
                if show_prompt and body.get("full_prompt"):
                    with st.expander("Full prompt sent to the LLM"):
                        st.code(body["full_prompt"], language="markdown")
                chat_history.append({"role": "assistant", "content": body["answer"], "documents": body["documents"]})
            else:
                message = f"⚠️ {body}. Make sure this project has indexed documents."
                st.markdown(message)
                chat_history.append({"role": "assistant", "content": message})
