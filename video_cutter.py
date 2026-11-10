from __future__ import annotations

import argparse
import json
import mimetypes
import os
import shutil
import subprocess
import tempfile
import time
import urllib.parse
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = APP_DIR.parent
OUTPUT_DIR = WORKSPACE_DIR / "edited_output"
VIDEO_EXTENSIONS = {".mp4", ".m4v", ".mov"}


INDEX_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>本地视频剪辑</title>
  <style>
    :root {
      color-scheme: light;
      font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
      background: #f4f6f8;
      color: #17202a;
    }
    * { box-sizing: border-box; }
    body { margin: 0; min-height: 100vh; }
    main { max-width: 1160px; margin: 0 auto; padding: 18px; }
    .topbar {
      display: flex;
      gap: 10px;
      align-items: center;
      margin-bottom: 12px;
    }
    select, input, button {
      font: inherit;
      border: 1px solid #c9d2dc;
      border-radius: 6px;
      min-height: 36px;
      background: #fff;
      color: #17202a;
    }
    select { flex: 1; min-width: 240px; padding: 0 10px; }
    input { width: 116px; padding: 0 9px; }
    button {
      padding: 0 12px;
      cursor: pointer;
      background: #ffffff;
      transition: background 120ms ease, border-color 120ms ease;
    }
    button:hover { background: #eef3f7; border-color: #9fb0bf; }
    button.primary {
      background: #156f7d;
      border-color: #156f7d;
      color: #fff;
      font-weight: 600;
    }
    button.primary:hover { background: #105d69; border-color: #105d69; }
    button.danger { color: #9d2635; }
    video {
      display: block;
      width: 100%;
      max-height: 62vh;
      background: #10161d;
      border-radius: 8px;
      outline: 1px solid #d5dde5;
    }
    .toolbar {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      padding: 10px 0 12px;
    }
    .timebox {
      min-width: 92px;
      padding: 7px 10px;
      border: 1px solid #d5dde5;
      border-radius: 6px;
      background: #fff;
      text-align: center;
      font-variant-numeric: tabular-nums;
    }
    .jumpbar, .jump-form {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }
    .jumpbar { padding: 0 0 14px; }
    .jump-form label { white-space: nowrap; }
    .jump-form input { width: 136px; font-variant-numeric: tabular-nums; }
    .jump-form input[type="text"] { width: 156px; }
    .jump-status { color: #9d2635; }
    input[type="range"] { flex: 1; min-width: 220px; padding: 0; }
    .segments {
      width: 100%;
      border-collapse: collapse;
      background: #fff;
      border: 1px solid #d5dde5;
      border-radius: 8px;
      overflow: hidden;
    }
    .segments th, .segments td {
      padding: 9px;
      border-bottom: 1px solid #edf1f4;
      text-align: left;
      vertical-align: middle;
    }
    .segments th {
      background: #e9eef3;
      font-weight: 600;
      white-space: nowrap;
    }
    .segments tr:last-child td { border-bottom: 0; }
    .row-actions, .time-actions { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
    .footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-top: 14px;
      flex-wrap: wrap;
    }
    .status {
      min-height: 22px;
      color: #50606f;
      overflow-wrap: anywhere;
    }
    .output a { color: #0f6370; font-weight: 600; }
    @media (max-width: 760px) {
      main { padding: 12px; }
      .topbar { flex-direction: column; align-items: stretch; }
      .segments, .segments thead, .segments tbody, .segments th, .segments td, .segments tr {
        display: block;
      }
      .segments thead { display: none; }
      .segments tr { border-bottom: 1px solid #edf1f4; padding: 8px; }
      .segments td { border: 0; padding: 6px 0; }
      .segments td::before {
        display: block;
        margin-bottom: 4px;
        color: #657482;
        font-size: 13px;
      }
      .segments td:nth-child(1)::before { content: "序号"; }
      .segments td:nth-child(2)::before { content: "起始秒数"; }
      .segments td:nth-child(3)::before { content: "终止秒数"; }
      .segments td:nth-child(4)::before { content: "操作"; }
      input { width: 100%; }
      .jump-form input, .jump-form input[type="text"] { width: 136px; max-width: 45vw; }
    }
  </style>
</head>
<body>
<main>
  <div class="topbar">
    <select id="videoSelect" aria-label="选择视频"></select>
    <button id="reloadBtn" type="button">刷新列表</button>
  </div>

  <video id="video" preload="metadata"></video>

  <div class="toolbar">
    <button id="playBtn" type="button">播放</button>
    <button id="pauseBtn" type="button">暂停</button>
    <button id="backBtn" type="button">-1 秒</button>
    <button id="forwardBtn" type="button">+1 秒</button>
    <span id="currentTime" class="timebox">0.000</span>
    <input id="seekBar" type="range" min="0" max="0" value="0" step="0.001" aria-label="播放进度">
    <span id="duration" class="timebox">0.000</span>
  </div>

  <div class="jumpbar">
    <form id="secondsJumpForm" class="jump-form">
      <label for="secondsJumpInput">秒数</label>
      <input id="secondsJumpInput" type="number" min="0" step="any" placeholder="例如 90.5" required>
      <button type="submit">跳转</button>
    </form>
    <form id="clockJumpForm" class="jump-form">
      <label for="clockJumpInput">时:分:秒</label>
      <input id="clockJumpInput" type="text" inputmode="decimal" placeholder="00:01:30.500" required>
      <button type="submit">跳转</button>
    </form>
    <span id="jumpStatus" class="jump-status" role="status" aria-live="polite"></span>
  </div>

  <table class="segments">
    <thead>
      <tr>
        <th style="width:70px">序号</th>
        <th>起始秒数位置</th>
        <th>终止秒数位置</th>
        <th style="width:210px">操作</th>
      </tr>
    </thead>
    <tbody id="segmentBody"></tbody>
  </table>

  <div class="footer">
    <div>
      <button id="addSegmentBtn" type="button">添加片段</button>
      <button id="exportBtn" class="primary" type="button">导出完整剪辑视频</button>
    </div>
    <div id="status" class="status"></div>
  </div>
  <div id="output" class="status output"></div>
</main>

<script>
const videoSelect = document.getElementById("videoSelect");
const reloadBtn = document.getElementById("reloadBtn");
const video = document.getElementById("video");
const playBtn = document.getElementById("playBtn");
const pauseBtn = document.getElementById("pauseBtn");
const backBtn = document.getElementById("backBtn");
const forwardBtn = document.getElementById("forwardBtn");
const currentTimeEl = document.getElementById("currentTime");
const durationEl = document.getElementById("duration");
const seekBar = document.getElementById("seekBar");
const secondsJumpForm = document.getElementById("secondsJumpForm");
const secondsJumpInput = document.getElementById("secondsJumpInput");
const clockJumpForm = document.getElementById("clockJumpForm");
const clockJumpInput = document.getElementById("clockJumpInput");
const jumpStatus = document.getElementById("jumpStatus");
const segmentBody = document.getElementById("segmentBody");
const addSegmentBtn = document.getElementById("addSegmentBtn");
const exportBtn = document.getElementById("exportBtn");
const statusEl = document.getElementById("status");
const outputEl = document.getElementById("output");

let videos = [];
let segments = [];

function fmtSeconds(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n.toFixed(3) : "0.000";
}

function setStatus(text) {
  statusEl.textContent = text || "";
}

async function loadVideos() {
  setStatus("正在读取本地视频列表...");
  outputEl.textContent = "";
  const res = await fetch("/api/videos");
  if (!res.ok) throw new Error(await res.text());
  videos = await res.json();
  videoSelect.innerHTML = "";
  if (!videos.length) {
    const opt = document.createElement("option");
    opt.textContent = "当前目录未找到 mp4/mov/m4v 视频";
    videoSelect.appendChild(opt);
    video.removeAttribute("src");
    setStatus("未找到可播放视频。");
    return;
  }
  for (const item of videos) {
    const opt = document.createElement("option");
    opt.value = item.id;
    opt.textContent = item.name;
    videoSelect.appendChild(opt);
  }
  selectVideo(videos[0].id);
  setStatus(`找到 ${videos.length} 个视频。`);
}

function selectVideo(id) {
  if (!id) return;
  video.src = `/media/${encodeURIComponent(id)}`;
  video.load();
  jumpStatus.textContent = "";
  segments = [{ start: "0.000", end: "" }];
  renderSegments();
  outputEl.textContent = "";
}

function renderSegments() {
  segmentBody.innerHTML = "";
  segments.forEach((seg, index) => {
    const tr = document.createElement("tr");

    const num = document.createElement("td");
    num.textContent = String(index + 1);
    tr.appendChild(num);

    const startTd = document.createElement("td");
    const startWrap = document.createElement("div");
    startWrap.className = "time-actions";
    const startInput = document.createElement("input");
    startInput.type = "number";
    startInput.step = "0.001";
    startInput.min = "0";
    startInput.value = seg.start;
    startInput.addEventListener("input", () => segments[index].start = startInput.value);
    const setStart = document.createElement("button");
    setStart.type = "button";
    setStart.textContent = "取当前";
    setStart.addEventListener("click", () => {
      segments[index].start = fmtSeconds(video.currentTime);
      renderSegments();
    });
    startWrap.append(startInput, setStart);
    startTd.appendChild(startWrap);
    tr.appendChild(startTd);

    const endTd = document.createElement("td");
    const endWrap = document.createElement("div");
    endWrap.className = "time-actions";
    const endInput = document.createElement("input");
    endInput.type = "number";
    endInput.step = "0.001";
    endInput.min = "0";
    endInput.value = seg.end;
    endInput.addEventListener("input", () => segments[index].end = endInput.value);
    const setEnd = document.createElement("button");
    setEnd.type = "button";
    setEnd.textContent = "取当前";
    setEnd.addEventListener("click", () => {
      segments[index].end = fmtSeconds(video.currentTime);
      renderSegments();
    });
    endWrap.append(endInput, setEnd);
    endTd.appendChild(endWrap);
    tr.appendChild(endTd);

    const actions = document.createElement("td");
    const actionWrap = document.createElement("div");
    actionWrap.className = "row-actions";
    const preview = document.createElement("button");
    preview.type = "button";
    preview.textContent = "跳到起点";
    preview.addEventListener("click", () => {
      const start = Number(segments[index].start);
      if (Number.isFinite(start)) video.currentTime = Math.max(0, start);
    });
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "danger";
    remove.textContent = "删除";
    remove.addEventListener("click", () => {
      segments.splice(index, 1);
      if (!segments.length) segments.push({ start: "0.000", end: "" });
      renderSegments();
    });
    actionWrap.append(preview, remove);
    actions.appendChild(actionWrap);
    tr.appendChild(actions);

    segmentBody.appendChild(tr);
  });
}

function readSegments() {
  return segments.map((seg, idx) => {
    const start = Number(seg.start);
    const end = Number(seg.end);
    if (!Number.isFinite(start) || !Number.isFinite(end)) {
      throw new Error(`第 ${idx + 1} 行时间不是有效数字。`);
    }
    if (start < 0 || end <= start) {
      throw new Error(`第 ${idx + 1} 行要求终止秒数大于起始秒数。`);
    }
    if (Number.isFinite(video.duration) && end > video.duration + 0.01) {
      throw new Error(`第 ${idx + 1} 行终止秒数超过视频时长。`);
    }
    return { start, end };
  });
}

function jumpTo(seconds) {
  if (video.readyState < HTMLMediaElement.HAVE_METADATA || !Number.isFinite(video.duration)) {
    throw new Error("请等待视频加载完成。");
  }
  if (!Number.isFinite(seconds) || seconds < 0 || seconds > video.duration) {
    throw new Error(`跳转时间须在 0 到 ${fmtSeconds(video.duration)} 秒之间。`);
  }
  video.currentTime = seconds;
  jumpStatus.textContent = "";
}

secondsJumpForm.addEventListener("submit", event => {
  event.preventDefault();
  try {
    const value = secondsJumpInput.value.trim();
    if (!value) throw new Error("请输入秒数。");
    jumpTo(Number(value));
  } catch (err) {
    jumpStatus.textContent = err.message;
  }
});

clockJumpForm.addEventListener("submit", event => {
  event.preventDefault();
  try {
    const match = /^(\d+):([0-5]?\d):([0-5]?\d(?:\.\d{1,3})?)$/.exec(clockJumpInput.value.trim());
    if (!match) throw new Error("请输入时:分:秒，例如 01:02:03.500。");
    jumpTo(Number(match[1]) * 3600 + Number(match[2]) * 60 + Number(match[3]));
  } catch (err) {
    jumpStatus.textContent = err.message;
  }
});

videoSelect.addEventListener("change", () => selectVideo(videoSelect.value));
reloadBtn.addEventListener("click", () => loadVideos().catch(err => setStatus(err.message)));
playBtn.addEventListener("click", () => video.play());
pauseBtn.addEventListener("click", () => video.pause());
backBtn.addEventListener("click", () => video.currentTime = Math.max(0, video.currentTime - 1));
forwardBtn.addEventListener("click", () => video.currentTime = Math.min(video.duration || Infinity, video.currentTime + 1));
addSegmentBtn.addEventListener("click", () => {
  segments.push({ start: fmtSeconds(video.currentTime), end: "" });
  renderSegments();
});

video.addEventListener("loadedmetadata", () => {
  seekBar.max = Number.isFinite(video.duration) ? String(video.duration) : "0";
  durationEl.textContent = fmtSeconds(video.duration);
});
video.addEventListener("timeupdate", () => {
  currentTimeEl.textContent = fmtSeconds(video.currentTime);
  seekBar.value = String(video.currentTime);
});
seekBar.addEventListener("input", () => video.currentTime = Number(seekBar.value));

exportBtn.addEventListener("click", async () => {
  try {
    const videoId = videoSelect.value;
    if (!videoId) throw new Error("请先选择视频。");
    const payload = { video_id: videoId, segments: readSegments() };
    setStatus("正在导出，请等待 ffmpeg 完成...");
    outputEl.textContent = "";
    exportBtn.disabled = true;
    const res = await fetch("/api/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || "导出失败。");
    setStatus("导出完成。");
    outputEl.innerHTML = `输出文件：<a href="/download/${encodeURIComponent(data.id)}" target="_blank">${data.path}</a>`;
  } catch (err) {
    setStatus(err.message);
  } finally {
    exportBtn.disabled = false;
  }
});

loadVideos().catch(err => setStatus(err.message));
</script>
</body>
</html>
"""


def json_bytes(data: object) -> bytes:
    return json.dumps(data, ensure_ascii=False).encode("utf-8")


def safe_relative(path: Path) -> str:
    return path.resolve().relative_to(WORKSPACE_DIR.resolve()).as_posix()


def discover_videos() -> list[dict[str, str]]:
    videos: list[dict[str, str]] = []
    for path in sorted(WORKSPACE_DIR.rglob("*"), key=lambda p: safe_relative(p) if p.is_file() else ""):
        if not path.is_file() or path.suffix.lower() not in VIDEO_EXTENSIONS:
            continue
        try:
            rel = safe_relative(path)
        except ValueError:
            continue
        if rel.startswith("edited_output/") or rel.startswith("src/"):
            continue
        videos.append({"id": rel, "name": rel})
    return videos


def resolve_workspace_file(file_id: str, *, must_be_video: bool = False) -> Path:
    decoded = urllib.parse.unquote(file_id)
    candidate = (WORKSPACE_DIR / decoded).resolve()
    root = WORKSPACE_DIR.resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError("路径超出当前工作目录。")
    if not candidate.is_file():
        raise FileNotFoundError("文件不存在。")
    if must_be_video and candidate.suffix.lower() not in VIDEO_EXTENSIONS:
        raise ValueError("只支持 mp4/mov/m4v 视频。")
    return candidate


def run_ffmpeg(args: list[str]) -> None:
    completed = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "ffmpeg 执行失败。"
        raise RuntimeError(message[-3000:])


def normalize_segments(raw_segments: object) -> list[tuple[float, float]]:
    if not isinstance(raw_segments, list) or not raw_segments:
        raise ValueError("片段列表不能为空。")
    segments: list[tuple[float, float]] = []
    for index, item in enumerate(raw_segments, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"第 {index} 行片段格式错误。")
        try:
            start = float(item["start"])
            end = float(item["end"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"第 {index} 行时间不是有效数字。") from exc
        if start < 0 or end <= start:
            raise ValueError(f"第 {index} 行要求终止秒数大于起始秒数。")
        segments.append((start, end))
    return segments


def export_video(video_path: Path, segments: list[tuple[float, float]]) -> Path:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("找不到 ffmpeg，请先安装并加入 PATH。")

    OUTPUT_DIR.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUT_DIR / f"{video_path.stem}_cut_{stamp}.mp4"

    with tempfile.TemporaryDirectory(prefix="video_cutter_") as tmp_dir_name:
        tmp_dir = Path(tmp_dir_name)
        segment_paths: list[Path] = []
        for index, (start, end) in enumerate(segments, start=1):
            part_path = tmp_dir / f"part_{index:03d}.mp4"
            duration = end - start
            run_ffmpeg([
                "ffmpeg",
                "-hide_banner",
                "-y",
                "-ss",
                f"{start:.3f}",
                "-i",
                str(video_path),
                "-t",
                f"{duration:.3f}",
                "-map",
                "0:v:0",
                "-map",
                "0:a?",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "18",
                "-c:a",
                "aac",
                "-b:a",
                "160k",
                "-movflags",
                "+faststart",
                "-avoid_negative_ts",
                "make_zero",
                str(part_path),
            ])
            segment_paths.append(part_path)

        concat_file = tmp_dir / "concat.txt"
        concat_file.write_text(
            "".join(f"file '{path.as_posix()}'\n" for path in segment_paths),
            encoding="utf-8",
        )
        run_ffmpeg([
            "ffmpeg",
            "-hide_banner",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(output_path),
        ])

    return output_path


class VideoCutterHandler(BaseHTTPRequestHandler):
    server_version = "VideoCutter/1.0"

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.address_string()} - {fmt % args}")

    def send_bytes(self, body: bytes, content_type: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, data: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        self.send_bytes(json_bytes(data), "application/json; charset=utf-8", status)

    def send_error_json(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        self.send_json({"error": message}, status)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        try:
            if path == "/":
                self.send_bytes(INDEX_HTML.encode("utf-8"), "text/html; charset=utf-8")
            elif path == "/api/videos":
                self.send_json(discover_videos())
            elif path.startswith("/media/"):
                self.serve_file(resolve_workspace_file(path.removeprefix("/media/"), must_be_video=True), inline=True)
            elif path.startswith("/download/"):
                self.serve_file(resolve_workspace_file(path.removeprefix("/download/")), inline=False)
            else:
                self.send_error(HTTPStatus.NOT_FOUND)
        except FileNotFoundError as exc:
            self.send_error_json(str(exc), HTTPStatus.NOT_FOUND)
        except ValueError as exc:
            self.send_error_json(str(exc), HTTPStatus.BAD_REQUEST)
        except Exception as exc:
            self.send_error_json(str(exc), HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/api/export":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            video_path = resolve_workspace_file(str(payload.get("video_id", "")), must_be_video=True)
            segments = normalize_segments(payload.get("segments"))
            output_path = export_video(video_path, segments)
            rel = safe_relative(output_path)
            self.send_json({"id": rel, "path": rel})
        except json.JSONDecodeError:
            self.send_error_json("请求 JSON 格式错误。", HTTPStatus.BAD_REQUEST)
        except (ValueError, FileNotFoundError) as exc:
            self.send_error_json(str(exc), HTTPStatus.BAD_REQUEST)
        except Exception as exc:
            self.send_error_json(str(exc), HTTPStatus.INTERNAL_SERVER_ERROR)

    def serve_file(self, file_path: Path, *, inline: bool) -> None:
        file_size = file_path.stat().st_size
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        range_header = self.headers.get("Range")
        start = 0
        end = file_size - 1
        status = HTTPStatus.OK

        if range_header:
            units, _, range_spec = range_header.partition("=")
            if units.strip().lower() == "bytes":
                start_text, _, end_text = range_spec.partition("-")
                start = int(start_text) if start_text else 0
                end = int(end_text) if end_text else file_size - 1
                start = max(0, start)
                end = min(file_size - 1, end)
                status = HTTPStatus.PARTIAL_CONTENT

        if start > end:
            self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
            self.send_header("Content-Range", f"bytes */{file_size}")
            self.end_headers()
            return

        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        if status == HTTPStatus.PARTIAL_CONTENT:
            self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
        disposition = "inline" if inline else "attachment"
        quoted_name = urllib.parse.quote(file_path.name)
        self.send_header("Content-Disposition", f"{disposition}; filename*=UTF-8''{quoted_name}")
        self.end_headers()

        with file_path.open("rb") as file_obj:
            file_obj.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                chunk = file_obj.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)


def main() -> None:
    parser = argparse.ArgumentParser(description="本地 HTML5 + ffmpeg 视频剪辑工具")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true", help="启动后不自动打开浏览器")
    args = parser.parse_args()

    if shutil.which("ffmpeg") is None:
        raise SystemExit("找不到 ffmpeg，请先安装并加入 PATH。")

    server = ThreadingHTTPServer((args.host, args.port), VideoCutterHandler)
    url = f"http://{args.host}:{args.port}/"
    print(f"工作目录: {WORKSPACE_DIR}")
    print(f"输出目录: {OUTPUT_DIR}")
    print(f"访问地址: {url}")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
