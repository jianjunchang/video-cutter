#!/usr/bin/env sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
pid_file="$root/.video-cutter.pid"

if [ -f "$pid_file" ]; then
    pid=$(cat "$pid_file")
    if kill -0 "$pid" 2>/dev/null; then
        printf 'Service may already be running (PID %s).\n' "$pid" >&2
        exit 1
    fi
    rm "$pid_file"
fi

if [ -x "$root/.venv/bin/python" ]; then
    python="$root/.venv/bin/python"
elif [ -x "$root/.venv/Scripts/python.exe" ]; then
    python="$root/.venv/Scripts/python.exe"
elif command -v python3 >/dev/null 2>&1; then
    python=python3
else
    python=python
fi

command -v "$python" >/dev/null 2>&1 || { echo 'Python was not found.' >&2; exit 1; }
command -v ffmpeg >/dev/null 2>&1 || { echo 'ffmpeg was not found on PATH.' >&2; exit 1; }

"$python" -u "$root/video_cutter.py" --no-browser >"$root/.video-cutter.log" 2>&1 &
pid=$!
sleep 1
if ! kill -0 "$pid" 2>/dev/null; then
    echo 'Service failed to start. See .video-cutter.log.' >&2
    exit 1
fi

printf '%s\n' "$pid" > "$pid_file"
printf 'Service started (PID %s): http://127.0.0.1:8765/\n' "$pid"
