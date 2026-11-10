#!/usr/bin/env sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
pid_file="$root/.video-cutter.pid"

if [ ! -f "$pid_file" ]; then
    echo 'No service PID file found.'
    exit 0
fi

pid=$(cat "$pid_file")
case "$pid" in
    ''|*[!0-9]*) echo 'Invalid service PID file.' >&2; exit 1 ;;
esac

if kill -0 "$pid" 2>/dev/null; then
    command_line=$(ps -p "$pid" -f 2>/dev/null || true)
    case "$command_line" in
        *video_cutter.py*) ;;
        *) printf 'PID %s belongs to another process. Remove the stale PID file manually.\n' "$pid" >&2; exit 1 ;;
    esac
    kill "$pid"
    printf 'Service stopped (PID %s).\n' "$pid"
else
    echo 'Service was already stopped.'
fi
rm "$pid_file"
