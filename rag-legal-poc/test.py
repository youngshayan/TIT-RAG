# مثال: اسکریپت کوچک یا حتی از یک endpoint ادمین
from app.store import Store
st = Store()
st.reset_all()  # sqlite + faiss + bm25 پاک و خالی می‌شود
