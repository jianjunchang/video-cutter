# 本地视频剪辑工具

这是一个本地 HTML5 操作页面 + Python 后端 + ffmpeg 的视频剪辑脚本。

## 启动

后台启动和停止服务：

```powershell
.\scripts\start.ps1
.\scripts\stop.ps1
```

在 Linux/macOS 或其他支持 POSIX shell 的环境：

```sh
sh scripts/start.sh
sh scripts/stop.sh
```

脚本需要 Python 和 ffmpeg；优先使用项目 `.venv` 中的 Python。启动后访问 `http://127.0.0.1:8765/`，日志保存在项目目录中。

也可以在前台运行：

在 `C:\Users\hp\Videos\src` 目录运行：

```powershell
uv run python video_cutter.py
```

启动后浏览器会自动打开：

```text
http://127.0.0.1:8765/
```

如果浏览器没有自动打开，手动访问上面的地址即可。

也可以用已有 conda 环境启动：

```powershell
conda activate py311
cd C:\Users\hp\Videos\src
python video_cutter.py
```

## 使用

1. 顶部选择当前目录或子目录里的 `mp4/mov/m4v` 视频。
2. 在播放器下方控制播放、暂停、前进或后退；也可输入秒数或 `时:分:秒`（例如 `01:02:03.500`）直接跳转。
3. 在片段列表里输入起始秒数和终止秒数，或点击“取当前”把当前播放位置写入输入框。
4. 点击“导出完整剪辑视频”，脚本会把所有片段按列表顺序合成为一个新视频。

## 输出

导出文件会保存到 `C:\Users\hp\Videos\edited_output` 子目录中。

原视频只会被读取，不会被修改或覆盖。
