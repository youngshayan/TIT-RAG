# ingest_folder.py
from pathlib import Path
from app.store import Store
from app.ingest import ingest_file
from app import config

ALLOWED_EXT = {".pdf", ".txt", ".text", ".md"}

def iter_files(root: Path):
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in ALLOWED_EXT:
            yield p

def main():
    store = Store()
    base = config.FILES_DIR
    if not base.exists():
        print(f"Folder not found: {base}")
        return
    count = 0
    for fp in iter_files(base):
        try:
            print(f"📄 Ingest: {fp}")
            doc_id = ingest_file(store, fp, title=fp.stem)
            print(f"✅ Done: doc_id={doc_id}")
            count += 1
        except Exception as e:
            print(f"❌ Failed on {fp}: {e}")
    print(f"\n🎉 Ingestion complete. Files processed: {count}")

if __name__ == "__main__":
    main()
