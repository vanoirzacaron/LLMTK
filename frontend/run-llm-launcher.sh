#!/bin/bash

# Launch your Tkinter app
python3 /home/zacaron/LLMTK/frontend/llm-launcher.py &

APP_PID=$!

# Wait for the window to appear
sleep 1

# Find window by title and make it sticky (visible on all workspaces)
wmctrl -r "LLM Services Launcher" -b add,sticky

wait $APP_PID

