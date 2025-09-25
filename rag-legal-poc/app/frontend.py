import streamlit as st
import requests
import os

API_BASE = "http://127.0.0.1:8000"

st.set_page_config(page_title="RAG Legal Assistant", page_icon="⚖️", layout="wide")

st.title("⚖️ دستیار حقوقی بانکی (RAG PoC)")
st.markdown("این یک **Proof-of-Concept** است. پاسخ‌ها جنبه‌ی مشاوره رسمی ندارند.")

# ---------- Sidebar ----------
st.sidebar.header("مدیریت اسناد")

uploaded_files = st.sidebar.file_uploader(
    "📂 آپلود فایل آیین‌نامه (PDF یا TXT)",
    type=["pdf", "txt"],
    accept_multiple_files=True
)

if st.sidebar.button("ارسال و ایندکس"):
    if uploaded_files:
        files = [("files", (f.name, f.read(), f"type")) for f in uploaded_files]
        resp = requests.post(f"{API_BASE}/upload", files=files)
        if resp.ok:
            st.sidebar.success(f"✅ {len(uploaded_files)} فایل آپلود شد")
        else:
            st.sidebar.error(f"❌ خطا: {resp.text}")
    else:
        st.sidebar.warning("هیچ فایلی انتخاب نشده.")

st.sidebar.markdown("---")
query = st.sidebar.text_input("🔎 پرسش شما")
if st.sidebar.button("بپرس"):
    if query.strip():
        data = {"query": query}
        resp = requests.post(f"{API_BASE}/ask", data=data)
        if resp.ok:
            ans = resp.json()
            st.subheader("📝 پاسخ سیستم")
            st.write(ans["answer"])
            with st.expander("منابع"):
                st.json(ans["citations"])
        else:
            st.error(f"❌ خطا: {resp.text}")
    else:
        st.sidebar.warning("سوالی وارد کنید.")

st.sidebar.markdown("---")
doc_id = st.sidebar.number_input("📄 Doc ID برای خلاصه یا تعارض", min_value=1, step=1)
col1, col2 = st.sidebar.columns(2)
if col1.button("📑 خلاصه‌سازی"):
    resp = requests.post(f"{API_BASE}/summarize", data={"doc_id": doc_id})
    if resp.ok:
        st.subheader(f"📑 خلاصه سند {doc_id}")
        st.write(resp.json()["summary"])
    else:
        st.error(f"❌ خطا: {resp.text}")

if col2.button("⚔️ بررسی تعارض"):
    resp = requests.post(f"{API_BASE}/conflict-check", data={"doc_id": doc_id})
    if resp.ok:
        st.subheader(f"⚔️ تعارضات سند {doc_id}")
        st.json(resp.json())
    else:
        st.error(f"❌ خطا: {resp.text}")
