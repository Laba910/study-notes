from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import subprocess
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"],
    allow_headers=["*"],
)

REPO_DIR = os.path.expanduser("~/study-notes")

class Conversation(BaseModel):
    source: str  # "chatgpt" or "gemini"
    title: str
    content: str

@app.post("/save")
def save(conv: Conversation):
    date = datetime.now().strftime("%Y-%m-%d")
    time = datetime.now().strftime("%H%M%S")
    source = conv.source.lower()

    log_dir = os.path.join(REPO_DIR, "logs", source)
    os.makedirs(log_dir, exist_ok=True)

    safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in conv.title)[:50].strip()
    filename = f"{date}_{time}_{safe_title}.md"
    filepath = os.path.join(log_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# {conv.title}\n\n")
        f.write(f"**Source:** {conv.source}  \n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n\n")
        f.write("---\n\n")
        f.write(conv.content)

    subprocess.run(["git", "add", filename], cwd=log_dir)
    subprocess.run(["git", "commit", "-m", f"[{source}] {date} - {conv.title[:40]}"], cwd=REPO_DIR)
    subprocess.run(["git", "push"], cwd=REPO_DIR)

    return {"status": "ok", "file": filename}
