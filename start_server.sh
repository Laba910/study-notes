#!/bin/bash
cd ~/study-notes/server
pip install -q -r requirements.txt
uvicorn server:app --host 127.0.0.1 --port 8765
