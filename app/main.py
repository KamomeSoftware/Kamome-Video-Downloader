import os
import sys
import subprocess
import threading
import queue
import json
import tempfile
import shutil
import re
import time
import urllib.request
import webbrowser
import locale
from pathlib import Path
from urllib.error import URLError, HTTPError
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP_NAME = "Kamome Video Downloader"
APP_VERSION = "0.6.5"
APP_USER_MODEL_ID = "KamomeSoftware.KamomeVideoDownloader"


def set_windows_app_id():
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
        except Exception:
            pass


def icon_path() -> Path:
    return app_dir() / "assets" / "kamome.ico"


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def config_dir() -> Path:
    # Portable mode: keep all application state beside the executable.
    # Kamome itself does not write settings to AppData or the registry.
    return app_dir()


def config_path() -> Path:
    return app_dir() / "settings.json"


def app_config_path() -> Path:
    return app_dir() / "app_config.json"


TOOLS_DIR = app_dir() / "tools"
YT_DLP = TOOLS_DIR / "yt-dlp.exe"
FFMPEG = TOOLS_DIR / "ffmpeg.exe"
FFPROBE = TOOLS_DIR / "ffprobe.exe"
EXTERNAL_PLUGINS = app_dir() / "plugins"
LICENSES_DIR = app_dir() / "licenses"

COOKIE_OPTIONS = ["Firefox", "Chrome", "Edge", "None"]
COOKIE_BROWSER = {"Firefox": "firefox", "Chrome": "chrome", "Edge": "edge", "None": None}

I18N = {
"ja": {
"support":"開発を支援", "licenses":"利用上の注意・ライセンス", "updates":"更新を確認",
"video_url":"動画URL", "paste":"貼り付け", "reanalyze":"再解析", "cookie":"YouTube認証Cookie",
"cookie_note":"※ bot確認が出る動画では、ログイン済みブラウザを選択", "none":"使用しない",
"preview":"動画情報 / プレビュー", "preview_wait":"URLを貼り付けると自動解析します。",
"title":"タイトル: ", "uploader":"投稿者: ", "duration":"長さ: ",
"formats":"利用可能な映像形式（選択してダウンロード）", "resolution":"解像度", "codec":"映像形式",
"container":"形式", "size":"推定容量", "destination":"保存先", "choose":"選択…", "open":"開く",
"embed_thumb":"動画にサムネイルを埋め込む", "download":"ダウンロード", "cancel":"キャンセル", "log":"ログ",
"language":"言語", "lang_name":"日本語", "analyzing":"動画情報を解析中…", "thumb_wait":"サムネイル取得待ち…",
"starting":"開始しています…", "done":"完了", "failed":"失敗しました", "downloading":"ダウンロード中…",
"merging":"映像と音声を結合中…", "embedding":"サムネイルを埋め込み中…", "remux":"MP4に整えています…",
"ready":"待機中", "analysis_done":"解析完了：{count}種類の映像形式", "analysis_failed":"解析に失敗しました",
"preview_failed":"プレビューを取得できませんでした。", "no_thumbnail":"サムネイルなし",
"unknown":"不明", "cancelled":"キャンセルしました", "cut":"切り取り", "copy":"コピー", "select_all":"すべて選択"
},
"en": {
"support":"Support Development", "licenses":"Terms & Licenses", "updates":"Check for Updates",
"video_url":"Video URL", "paste":"Paste", "reanalyze":"Analyze Again", "cookie":"YouTube Cookies",
"cookie_note":"Use a signed-in browser if YouTube requests verification", "none":"None",
"preview":"Video Information / Preview", "preview_wait":"Paste a URL to analyze automatically.",
"title":"Title: ", "uploader":"Uploader: ", "duration":"Duration: ",
"formats":"Available Video Formats (select one to download)", "resolution":"Resolution", "codec":"Codec",
"container":"Container", "size":"Est. Size", "destination":"Save to", "choose":"Browse…", "open":"Open",
"embed_thumb":"Embed thumbnail in video", "download":"Download", "cancel":"Cancel", "log":"Log",
"language":"Language", "lang_name":"English", "analyzing":"Analyzing video…", "thumb_wait":"Waiting for thumbnail…",
"starting":"Starting…", "done":"Complete", "failed":"Failed", "downloading":"Downloading…",
"merging":"Merging video and audio…", "embedding":"Embedding thumbnail…", "remux":"Preparing MP4…",
"ready":"Ready", "analysis_done":"Analysis complete: {count} video formats", "analysis_failed":"Analysis failed",
"preview_failed":"Preview could not be loaded.", "no_thumbnail":"No thumbnail",
"unknown":"Unknown", "cancelled":"Cancelled", "cut":"Cut", "copy":"Copy", "select_all":"Select All"
}
}

TERMS_TEXT_JA = """Kamome Video Downloader 利用上の注意

・本ソフトは Google LLC / YouTube と提携・承認関係のない非公式ツールです。
・ダウンロードが許可されているコンテンツ、または利用者自身が権利を有するコンテンツに使用してください。
・各サービスの利用規約、著作権その他の法令を守って使用してください。
・本ソフトは yt-dlp および FFmpeg を利用します。各ソフトウェアにはそれぞれのライセンス条件が適用されます。
・ブラウザCookieを使用する設定では、yt-dlpが指定ブラウザのCookieを直接読み取ります。本アプリ自身はCookieを保存しません。
・本ソフトの利用により発生した損害について、開発者は法令上許される範囲で責任を負いません。
"""

TERMS_TEXT_EN = """Kamome Video Downloader - Terms of Use

- This software is an unofficial tool and is not affiliated with or endorsed by Google LLC or YouTube.
- Use it only for content that you are authorized to download or content for which you hold the necessary rights.
- Follow the terms of service of each website, copyright law, and all applicable laws and regulations.
- This software uses yt-dlp and FFmpeg. Their respective license terms apply.
- When browser cookies are enabled, yt-dlp reads cookies directly from the selected browser. Kamome Video Downloader itself does not store those cookies.
- To the extent permitted by law, the developer is not liable for damages arising from use of this software.
"""


def human_size(n, unknown="Unknown"):
    if not n:
        return unknown
    try:
        n = float(n)
    except Exception:
        return unknown
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while n >= 1024 and i < len(units) - 1:
        n /= 1024.0
        i += 1
    return f"{n:.1f} {units[i]}"


def codec_name(vcodec, unknown="Unknown"):
    v = (vcodec or "").lower()
    if v.startswith("vp09") or v.startswith("vp9"):
        return "VP9"
    if v.startswith("av01") or v.startswith("av1"):
        return "AV1"
    if v.startswith("avc1") or "h264" in v:
        return "H.264"
    if v.startswith("hev1") or v.startswith("hvc1") or "hevc" in v:
        return "HEVC"
    return vcodec or unknown


def sanitize_windows_filename(name):
    # Close to yt-dlp --windows-filenames for the common title-only case.
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name or "video")
    name = name.rstrip(" .")
    if not name:
        name = "video"
    reserved = {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {f"LPT{i}" for i in range(1, 10)}
    stem = name.split(".", 1)[0].upper()
    if stem in reserved:
        name = "_" + name
    return name


def version_tuple(s):
    nums = re.findall(r"\d+", s or "")
    return tuple(int(x) for x in nums[:4]) if nums else (0,)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("980x860")
        self.minsize(860, 720)
        self.proc = None
        self.q = queue.Queue()
        self.url_var = tk.StringVar()
        self.dest_var = tk.StringVar(value=str(Path.home() / "Downloads"))
        self.thumb_var = tk.BooleanVar(value=True)
        self.cookie_var = tk.StringVar(value="Firefox")
        try:
            sysloc = (locale.getlocale()[0] or locale.getdefaultlocale()[0] or "").lower()
        except Exception:
            sysloc = ""
        self.lang = "ja" if sysloc.startswith("ja") else "en"
        self.status_var = tk.StringVar(value=self._tr("ready"))
        self.progress_var = tk.DoubleVar(value=0)
        self.preview_photo = None
        self.preview_tmp = None
        self.video_info = None
        self.format_map = {}
        self.url_after_id = None
        self.analysis_serial = 0
        self.saved_window_state = "normal"
        self.saved_window_geometry = "980x860"
        self.last_normal_geometry = "980x860"
        self.skipped_update_version = ""
        self.update_later_version = ""
        self.update_later_date = ""
        self.app_cfg = self._load_app_config()
        self._load_settings()
        # The saved language can differ from the Windows locale used above.
        # Refresh language-dependent state after settings are loaded.
        self.status_var.set(self._tr("ready"))
        self._apply_window_icon()
        self._build_ui()
        self._restore_window_state()
        self.bind("<Configure>", self._remember_window_geometry, add="+")
        self.url_var.trace_add("write", self._on_url_changed)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._poll_queue)
        self.after(800, self._background_startup_tasks)

    def _load_app_config(self):
        defaults = {"support_url": "", "github_repo": "", "auto_check_updates": True}
        try:
            if app_config_path().exists():
                data = json.loads(app_config_path().read_text(encoding="utf-8"))
                defaults.update(data if isinstance(data, dict) else {})
        except Exception:
            pass
        return defaults

    def _load_settings(self):
        p = config_path()
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            d = data.get("destination")
            if d:
                self.dest_var.set(d)
            if "embed_thumbnail" in data:
                self.thumb_var.set(bool(data["embed_thumbnail"]))
            c = data.get("cookie_browser")
            if c in COOKIE_OPTIONS:
                self.cookie_var.set(c)
            elif c == "使用しない":
                self.cookie_var.set("None")
            lang = data.get("language")
            if lang in ("ja", "en"):
                self.lang = lang
            state = data.get("window_state")
            if state in ("normal", "zoomed"):
                self.saved_window_state = state
            geometry = data.get("window_geometry")
            if isinstance(geometry, str) and re.fullmatch(r"\d+x\d+[+-]\d+[+-]\d+", geometry):
                self.saved_window_geometry = geometry
                self.last_normal_geometry = geometry
            self.skipped_update_version = str(data.get("skipped_update_version") or "")
            self.update_later_version = str(data.get("update_later_version") or "")
            self.update_later_date = str(data.get("update_later_date") or "")
        except Exception:
            pass

    def _apply_window_icon(self):
        try:
            p = icon_path()
            if p.exists():
                self.iconbitmap(default=str(p))
        except Exception:
            pass

    def _virtual_screen_rect(self):
        # Use the Windows virtual desktop so saved positions also work with
        # multi-monitor layouts, including monitors placed left/above primary.
        if sys.platform.startswith("win"):
            try:
                import ctypes
                user32 = ctypes.windll.user32
                return (
                    user32.GetSystemMetrics(76),  # SM_XVIRTUALSCREEN
                    user32.GetSystemMetrics(77),  # SM_YVIRTUALSCREEN
                    user32.GetSystemMetrics(78),  # SM_CXVIRTUALSCREEN
                    user32.GetSystemMetrics(79),  # SM_CYVIRTUALSCREEN
                )
            except Exception:
                pass
        return (0, 0, self.winfo_screenwidth(), self.winfo_screenheight())

    def _safe_geometry(self, geometry):
        m = re.fullmatch(r"(\d+)x(\d+)([+-]\d+)([+-]\d+)", geometry or "")
        if not m:
            return "980x860"
        w, h, x, y = map(int, m.groups())
        vx, vy, vw, vh = self._virtual_screen_rect()
        # Keep a usable part of the title bar on-screen if a monitor vanished.
        w = max(860, min(w, max(860, vw)))
        h = max(720, min(h, max(720, vh)))
        min_visible_x = 120
        min_visible_y = 60
        x = min(max(x, vx - w + min_visible_x), vx + vw - min_visible_x)
        y = min(max(y, vy), vy + vh - min_visible_y)
        return f"{w}x{h}{x:+d}{y:+d}"

    def _restore_window_state(self):
        try:
            geometry = self._safe_geometry(self.saved_window_geometry)
            self.geometry(geometry)
            self.last_normal_geometry = geometry
            if self.saved_window_state == "zoomed":
                self.after_idle(lambda: self.state("zoomed"))
        except Exception:
            pass

    def _remember_window_geometry(self, event=None):
        try:
            if self.state() == "normal":
                geometry = self.geometry()
                if re.fullmatch(r"\d+x\d+[+-]\d+[+-]\d+", geometry):
                    self.last_normal_geometry = geometry
        except Exception:
            pass

    def _save_settings(self):
        try:
            state = self.state()
            if state not in ("normal", "zoomed"):
                state = self.saved_window_state if self.saved_window_state in ("normal", "zoomed") else "normal"
            geometry = self.last_normal_geometry
            if state == "normal":
                current = self.geometry()
                if re.fullmatch(r"\d+x\d+[+-]\d+[+-]\d+", current):
                    geometry = current
            config_path().write_text(json.dumps({
                "destination": self.dest_var.get().strip(),
                "embed_thumbnail": self.thumb_var.get(),
                "cookie_browser": self.cookie_var.get(),
                "language": self.lang,
                "window_state": state,
                "window_geometry": geometry,
                "skipped_update_version": self.skipped_update_version,
                "update_later_version": self.update_later_version,
                "update_later_date": self.update_later_date,
            }, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _on_close(self):
        self._save_settings()
        if self.preview_tmp:
            shutil.rmtree(self.preview_tmp, ignore_errors=True)
        self.destroy()

    def _tr(self, key):
        return I18N.get(self.lang, I18N["en"]).get(key, key)

    def _change_language(self, event=None):
        selected = self.lang_var.get()
        new_lang = "ja" if selected == "jp" else selected
        if new_lang not in ("ja", "en") or new_lang == self.lang:
            return
        self.lang = new_lang
        self._save_settings()
        messagebox.showinfo(APP_NAME, "言語設定を保存しました。再起動すると反映されます。" if self.lang == "ja" else "Language saved. Restart the application to apply it.")

    def _build_ui(self):
        main = ttk.Frame(self)
        main.pack(fill="both", expand=True)

        topbar = ttk.Frame(main)
        topbar.pack(fill="x", padx=14, pady=(12, 4))
        ttk.Label(topbar, text=f"{APP_NAME}  v{APP_VERSION}", font=("Segoe UI", 12, "bold")).pack(side="left")
        ttk.Button(topbar, text=self._tr("support"), command=self._support).pack(side="right")
        ttk.Button(topbar, text=self._tr("licenses"), command=self._show_licenses).pack(side="right", padx=(0, 8))
        ttk.Button(topbar, text=self._tr("updates"), command=lambda: self._check_updates(manual=True)).pack(side="right", padx=(0, 8))

        ttk.Label(main, text=self._tr("video_url")).pack(anchor="w", padx=14, pady=(8, 5))
        urlrow = ttk.Frame(main)
        urlrow.pack(fill="x", padx=14)
        self.url_entry = ttk.Entry(urlrow, textvariable=self.url_var)
        self.url_entry.pack(side="left", fill="x", expand=True)
        self._install_entry_context_menu(self.url_entry)
        ttk.Button(urlrow, text=self._tr("paste"), command=self._paste).pack(side="left", padx=(8, 0))
        self.analyze_btn = ttk.Button(urlrow, text=self._tr("reanalyze"), command=self._analyze_now)
        self.analyze_btn.pack(side="left", padx=(8, 0))

        authrow = ttk.Frame(main)
        authrow.pack(fill="x", padx=14, pady=(8, 4))
        ttk.Label(authrow, text=self._tr("cookie")).pack(side="left")
        cookie_combo = ttk.Combobox(authrow, textvariable=self.cookie_var, values=["Firefox", "Chrome", "Edge", self._tr("none")], state="readonly", width=14)
        cookie_combo.pack(side="left", padx=(8, 10))
        cookie_combo.bind("<<ComboboxSelected>>", lambda e: self._on_cookie_change())
        ttk.Label(authrow, text=self._tr("cookie_note")).pack(side="left")

        infoframe = ttk.LabelFrame(main, text=self._tr("preview"))
        infoframe.pack(fill="x", padx=14, pady=8)
        body = ttk.Frame(infoframe)
        body.pack(fill="x", padx=8, pady=8)
        self.preview_label = ttk.Label(body, text=self._tr("preview_wait"), anchor="center", width=45)
        self.preview_label.pack(side="left", fill="both", expand=False, padx=(0, 12))
        infocol = ttk.Frame(body)
        infocol.pack(side="left", fill="both", expand=True)
        self.title_var = tk.StringVar(value=self._tr("title") + "-")
        self.duration_var = tk.StringVar(value=self._tr("duration") + "-")
        self.channel_var = tk.StringVar(value=self._tr("uploader") + "-")
        ttk.Label(infocol, textvariable=self.title_var, wraplength=520).pack(anchor="w", pady=(4, 4))
        ttk.Label(infocol, textvariable=self.channel_var, wraplength=520).pack(anchor="w", pady=4)
        ttk.Label(infocol, textvariable=self.duration_var).pack(anchor="w", pady=4)

        fmtframe = ttk.LabelFrame(main, text=self._tr("formats"))
        fmtframe.pack(fill="both", expand=True, padx=14, pady=8)
        cols = ("resolution", "fps", "codec", "container", "size", "format_id")
        self.format_tree = ttk.Treeview(fmtframe, columns=cols, show="headings", height=10, selectmode="browse")
        headings = {
            "resolution": self._tr("resolution"),
            "fps": "FPS",
            "codec": self._tr("codec"),
            "container": self._tr("container"),
            "size": self._tr("size"),
            "format_id": "ID",
        }
        widths = {"resolution": 110, "fps": 70, "codec": 110, "container": 80, "size": 120, "format_id": 90}
        for c in cols:
            self.format_tree.heading(c, text=headings[c])
            self.format_tree.column(c, width=widths[c], anchor="center")
        sb = ttk.Scrollbar(fmtframe, orient="vertical", command=self.format_tree.yview)
        self.format_tree.configure(yscrollcommand=sb.set)
        self.format_tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        sb.pack(side="right", fill="y", padx=(0, 8), pady=8)

        ttk.Label(main, text=self._tr("destination")).pack(anchor="w", padx=14, pady=(3, 5))
        destrow = ttk.Frame(main)
        destrow.pack(fill="x", padx=14)
        dest_entry = ttk.Entry(destrow, textvariable=self.dest_var)
        dest_entry.pack(side="left", fill="x", expand=True)
        self._install_entry_context_menu(dest_entry)
        ttk.Button(destrow, text=self._tr("choose"), command=self._choose_dest).pack(side="left", padx=(8, 0))
        ttk.Button(destrow, text=self._tr("open"), command=self._open_dest).pack(side="left", padx=(8, 0))

        opts = ttk.Frame(main)
        opts.pack(fill="x", padx=14, pady=(10, 4))
        ttk.Checkbutton(opts, text=self._tr("embed_thumb"), variable=self.thumb_var).pack(side="left")
        langbox = ttk.Frame(opts)
        langbox.pack(side="right")
        ttk.Label(langbox, text=self._tr("language")).pack(side="left", padx=(0, 6))
        self.lang_var = tk.StringVar(value="jp" if self.lang == "ja" else "en")
        lang_combo = ttk.Combobox(langbox, textvariable=self.lang_var, values=["en", "jp"], state="readonly", width=7)
        lang_combo.pack(side="left")
        lang_combo.bind("<<ComboboxSelected>>", self._change_language)

        btnrow = ttk.Frame(main)
        btnrow.pack(fill="x", padx=14, pady=10)
        style = ttk.Style(self)
        style.configure("Download.TButton", font=("Yu Gothic UI", 10, "bold"), padding=(16, 7))
        self.download_btn = ttk.Button(btnrow, text=self._tr("download"), command=self._start, state="disabled", style="Download.TButton")
        self.download_btn.pack(side="left")
        self.cancel_btn = ttk.Button(btnrow, text=self._tr("cancel"), command=self._cancel, state="disabled")
        self.cancel_btn.pack(side="left", padx=(8, 0))

        ttk.Progressbar(main, variable=self.progress_var, maximum=100).pack(fill="x", padx=14, pady=(0, 5))
        ttk.Label(main, textvariable=self.status_var).pack(anchor="w", padx=14, pady=(0, 6))

        logframe = ttk.LabelFrame(main, text=self._tr("log"))
        logframe.pack(fill="both", expand=False, padx=14, pady=(0, 14))
        self.log = tk.Text(logframe, height=8, wrap="word")
        self.log.pack(fill="both", expand=True, padx=8, pady=8)
        self.log.configure(state="disabled")

    def _install_entry_context_menu(self, entry):
        menu = tk.Menu(self, tearoff=False)
        menu.add_command(label=self._tr("cut"), command=lambda: entry.event_generate("<<Cut>>"))
        menu.add_command(label=self._tr("copy"), command=lambda: entry.event_generate("<<Copy>>"))
        menu.add_command(label=self._tr("paste"), command=lambda: entry.event_generate("<<Paste>>"))
        menu.add_separator()
        menu.add_command(label=self._tr("select_all"), command=lambda: (entry.select_range(0, "end"), entry.icursor("end")))

        def popup(event):
            try:
                entry.focus_set()
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()
        entry.bind("<Button-3>", popup)

    def _paste(self):
        try:
            self.url_var.set(self.clipboard_get().strip())
        except tk.TclError:
            pass

    def _on_cookie_change(self):
        self._save_settings()
        if self.url_var.get().strip().startswith(("http://", "https://")):
            self._schedule_analysis(100)

    def _on_url_changed(self, *_):
        self._schedule_analysis(700)

    def _schedule_analysis(self, delay):
        if self.url_after_id:
            try:
                self.after_cancel(self.url_after_id)
            except Exception:
                pass
        self.url_after_id = self.after(delay, self._analyze_now)

    def _analyze_now(self):
        self.url_after_id = None
        url = self.url_var.get().strip()
        if not url.startswith(("http://", "https://")):
            return
        if not self._validate_tools():
            return
        self.analysis_serial += 1
        serial = self.analysis_serial
        self.analyze_btn.configure(state="disabled")
        self.download_btn.configure(state="disabled")
        self.status_var.set(self._tr("analyzing"))
        self.preview_label.configure(image="", text=self._tr("thumb_wait"))
        self.preview_photo = None
        self._clear_formats()
        threading.Thread(target=self._analyze_worker, args=(url, serial), daemon=True).start()

    def _cookie_args(self):
        selected = self.cookie_var.get()
        if selected in ("使用しない", "None", self._tr("none")):
            selected = "None"
        browser = COOKIE_BROWSER.get(selected)
        return ["--cookies-from-browser", browser] if browser else []

    def _common_ytdlp_args(self):
        args = [str(YT_DLP), "--no-playlist", "--ffmpeg-location", str(FFMPEG.parent), "--encoding", "utf-8"]
        if EXTERNAL_PLUGINS.exists():
            args += ["--plugin-dirs", str(EXTERNAL_PLUGINS)]
        args += self._cookie_args()
        return args

    def _analyze_worker(self, url, serial):
        cmd = self._common_ytdlp_args() + ["--dump-single-json", "--skip-download", url]
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        try:
            r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                               encoding="utf-8", errors="replace", creationflags=creationflags)
            if r.returncode != 0:
                err = (r.stderr or r.stdout or self._tr("analysis_failed")).strip()
                self.q.put(("analysis_error", (serial, err)))
                return
            data = json.loads(r.stdout)
            formats = self._prepare_formats(data)
            self.q.put(("analysis", (serial, data, formats)))
        except Exception as e:
            self.q.put(("analysis_error", (serial, str(e))))

    def _prepare_formats(self, data):
        duration = data.get("duration") or 0
        formats = data.get("formats") or []
        audio_sizes = []
        for a in formats:
            if a.get("vcodec") == "none" and a.get("acodec") not in (None, "none"):
                s = self._format_size(a, duration)
                if s:
                    audio_sizes.append(s)
        # Approximation only: add a likely best audio size to video-only streams.
        audio_est = max(audio_sizes) if audio_sizes else 0

        grouped = {}
        for f in formats:
            vcodec = f.get("vcodec")
            height = f.get("height")
            if not vcodec or vcodec == "none" or not height:
                continue
            fps = int(round(f.get("fps") or 0))
            codec = codec_name(vcodec, self._tr("unknown"))
            dynamic = f.get("dynamic_range") or "SDR"
            key = (int(height), fps, codec, dynamic, f.get("ext") or "")
            size = self._format_size(f, duration)
            if f.get("acodec") in (None, "none") and size:
                size += audio_est
            item = {
                "format_id": str(f.get("format_id")),
                "height": int(height),
                "width": f.get("width"),
                "fps": fps,
                "codec": codec,
                "vcodec": vcodec,
                "acodec": f.get("acodec"),
                "ext": f.get("ext") or "",
                "dynamic_range": dynamic,
                "size": size,
                "tbr": f.get("tbr") or 0,
            }
            old = grouped.get(key)
            if old is None or (item["tbr"], item["size"] or 0) > (old["tbr"], old["size"] or 0):
                grouped[key] = item
        result = list(grouped.values())
        result.sort(key=lambda x: (x["height"], x["fps"], x["codec"] == "VP9", x["tbr"]), reverse=True)
        return result

    def _format_size(self, f, duration):
        s = f.get("filesize") or f.get("filesize_approx")
        if s:
            return int(s)
        tbr = f.get("tbr")
        if tbr and duration:
            try:
                return int(float(tbr) * 1000 / 8 * float(duration))
            except Exception:
                return 0
        return 0

    def _clear_formats(self):
        for iid in self.format_tree.get_children():
            self.format_tree.delete(iid)
        self.format_map = {}

    def _fill_formats(self, formats):
        self._clear_formats()
        preferred_iid = None
        fallback_iid = None
        for i, f in enumerate(formats):
            iid = f"fmt{i}"
            res = f"{f['height']}p"
            if f.get("width"):
                res = f"{f['width']}×{f['height']}"
            codec = f["codec"]
            if f.get("dynamic_range") and f["dynamic_range"] not in ("SDR", ""): 
                codec += f" / {f['dynamic_range']}"
            self.format_tree.insert("", "end", iid=iid, values=(res, f["fps"] or "-", codec, f["ext"], human_size(f["size"], self._tr("unknown")), f["format_id"]))
            self.format_map[iid] = f
            if fallback_iid is None:
                fallback_iid = iid
            if preferred_iid is None and f["codec"] == "VP9" and f["height"] <= 1080:
                preferred_iid = iid
        pick = preferred_iid or fallback_iid
        if pick:
            self.format_tree.selection_set(pick)
            self.format_tree.focus(pick)
            self.format_tree.see(pick)
            self.download_btn.configure(state="normal")

    def _duration_text(self, seconds):
        try:
            seconds = int(seconds or 0)
            h, rem = divmod(seconds, 3600)
            m, s = divmod(rem, 60)
            return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
        except Exception:
            return "-"

    def _start_thumbnail(self, data, serial):
        url = data.get("thumbnail")
        if not url:
            thumbs = data.get("thumbnails") or []
            if thumbs:
                url = thumbs[-1].get("url")
        if not url:
            self.preview_label.configure(text=self._tr("no_thumbnail"))
            return
        threading.Thread(target=self._thumbnail_worker, args=(url, serial), daemon=True).start()

    def _thumbnail_worker(self, url, serial):
        tmp = tempfile.mkdtemp(prefix="kamome_preview_")
        src = Path(tmp) / "thumb.img"
        png = Path(tmp) / "thumb.png"
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as resp, open(src, "wb") as f:
                shutil.copyfileobj(resp, f)
            r = subprocess.run([str(FFMPEG), "-y", "-hide_banner", "-loglevel", "error", "-i", str(src), str(png)],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=creationflags)
            if r.returncode == 0 and png.exists():
                self.q.put(("thumbnail", (serial, str(png), tmp)))
            else:
                self.q.put(("thumbnail_error", (serial, tmp)))
        except Exception:
            self.q.put(("thumbnail_error", (serial, tmp)))

    def _choose_dest(self):
        p = filedialog.askdirectory(initialdir=self.dest_var.get() or str(Path.home()))
        if p:
            self.dest_var.set(p)
            self._save_settings()

    def _open_dest(self):
        p = Path(self.dest_var.get())
        p.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(p)

    def _log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _validate_tools(self):
        missing = [str(p) for p in (YT_DLP, FFMPEG, FFPROBE) if not p.exists()]
        if missing:
            messagebox.showerror(
                "Required files are missing" if self.lang == "en" else "必要ファイルがありません",
                ("Required files were not found in the tools folder.\n\n" + "\n".join(missing) + "\n\nPlease run build_portable.bat again.")
                if self.lang == "en" else
                ("toolsフォルダ内の必要ファイルが見つかりません。\n\n" + "\n".join(missing) + "\n\nbuild_portable.batをもう一度実行してください。")
            )
            return False
        return True

    def _selected_format(self):
        sel = self.format_tree.selection()
        if not sel:
            return None
        return self.format_map.get(sel[0])

    def _start(self):
        url = self.url_var.get().strip()
        dest = self.dest_var.get().strip()
        fmt = self._selected_format()
        if not url:
            messagebox.showwarning("URL", "Please paste a video URL." if self.lang == "en" else "動画URLを貼り付けてください。")
            return
        if not fmt:
            messagebox.showwarning("Video format" if self.lang == "en" else "映像形式", "Please select a video format from the list." if self.lang == "en" else "一覧からダウンロードする映像形式を選択してください。")
            return
        if not dest:
            messagebox.showwarning("Destination" if self.lang == "en" else "保存先", "Please select a destination folder." if self.lang == "en" else "保存先を選んでください。")
            return
        if not self._validate_tools():
            return
        if not self.video_info:
            messagebox.showwarning("Analysis" if self.lang == "en" else "解析", "Please analyze the video before downloading." if self.lang == "en" else "動画情報を解析してからダウンロードしてください。")
            return
        Path(dest).mkdir(parents=True, exist_ok=True)
        self._save_settings()

        title = sanitize_windows_filename(self.video_info.get("title") or "video")
        final_path = Path(dest) / f"{title}.mp4"
        overwrite = False
        if final_path.exists():
            ans = messagebox.askyesno("File already exists" if self.lang == "en" else "同名ファイルがあります", (f"A file with the same name already exists.\n\n{final_path.name}\n\nOverwrite it?" if self.lang == "en" else f"同名のファイルがすでに存在します。\n\n{final_path.name}\n\n上書きしますか？"))
            if not ans:
                return
            overwrite = True

        self.progress_var.set(0)
        self.download_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.status_var.set(self._tr("starting"))
        self._log(f"--- Download started: {fmt['height']}p / {fmt['codec']} / format {fmt['format_id']} ---")
        threading.Thread(target=self._worker, args=(url, dest, fmt, overwrite), daemon=True).start()

    def _worker(self, url, dest, fmt, overwrite):
        # Exact selected video format. If it is video-only, pair it with best audio.
        if fmt.get("acodec") not in (None, "none"):
            selector = fmt["format_id"]
        else:
            selector = f"{fmt['format_id']}+bestaudio/best"
        cmd = self._common_ytdlp_args() + [
            "--newline", "--paths", dest,
            "-o", "%(title)s.%(ext)s",
            "-f", selector,
            "--merge-output-format", "mp4",
            "--remux-video", "mp4",
            "--windows-filenames",
        ]
        if overwrite:
            cmd += ["--force-overwrites"]
        else:
            cmd += ["--no-overwrites"]
        # Preserve source information inside the MP4. yt-dlp/FFmpeg write standard metadata
        # including title/date; the explicit mappings keep uploader and source URL accessible.
        cmd += [
            "--embed-metadata",
            "--parse-metadata", "%(uploader)s:%(meta_artist)s",
            "--parse-metadata", "%(webpage_url)s:%(meta_comment)s",
        ]
        if self.thumb_var.get():
            # Keep a standalone thumbnail image as well as embedding it into the MP4.
            # Kamome does not delete or suppress the thumbnail file.
            # JPEG conversion improves MP4 cover-art compatibility.
            cmd += ["--write-thumbnail", "--convert-thumbnails", "jpg", "--embed-thumbnail"]
        cmd.append(url)
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        try:
            self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                         encoding="utf-8", errors="replace", creationflags=creationflags)
            last_lines = []
            for line in self.proc.stdout:
                line = line.rstrip()
                last_lines.append(line)
                last_lines = last_lines[-30:]
                self.q.put(("log", line))
                if "[download]" in line and "%" in line:
                    m = re.search(r"([0-9]+(?:\.[0-9]+)?)%", line)
                    if m:
                        self.q.put(("progress", float(m.group(1))))
                low = line.lower()
                if "merging formats" in low or "merger" in low:
                    self.q.put(("status", self._tr("merging")))
                elif "embedding thumbnail" in low:
                    self.q.put(("status", self._tr("embedding")))
                elif "remuxing video" in low:
                    self.q.put(("status", self._tr("remux")))
            ok = self.proc.wait() == 0
            self.q.put(("done", (ok, "\n".join(last_lines))))
        except Exception as e:
            self.q.put(("done", (False, str(e))))
        finally:
            self.proc = None

    def _cancel(self):
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
                self.status_var.set(self._tr("cancelled"))
            except Exception:
                pass

    def _friendly_error(self, text):
        t = text or ""
        low = t.lower()
        en = self.lang == "en"
        if "sign in to confirm" in low and "not a bot" in low:
            return (
                "YouTube requested bot verification.\n\nSelect Firefox / Chrome / Edge signed in to YouTube under 'YouTube Cookies', then analyze the URL again."
                if en else
                "YouTubeからbot確認を求められました。\n\n上部の『YouTube認証Cookie』で、YouTubeにログイン済みのFirefox / Chrome / Edgeを選び、再解析してください。"
            )
        if "requested format is not available" in low:
            return (
                "The selected video format is currently unavailable. Analyze the video again and select another format from the list."
                if en else
                "選択した映像形式が現在取得できません。動画を再解析して、一覧から別の形式を選んでください。"
            )
        if "private video" in low:
            return (
                "This is a private video. Select browser cookies from an account that has access."
                if en else
                "非公開動画のため取得できません。アクセス権のあるブラウザCookieを選択してください。"
            )
        if "video unavailable" in low:
            return (
                "The video could not be accessed. Check for regional restrictions, deletion, or sign-in requirements."
                if en else
                "動画を取得できませんでした。地域制限、削除、ログイン条件などを確認してください。"
            )
        if "cookies" in low and "browser" in low:
            return (
                "Browser cookies could not be read. Close the selected browser and try again, or select a different browser."
                if en else
                "ブラウザCookieの読み取りに失敗しました。対象ブラウザを一度終了して再試行するか、別のブラウザを選んでください。"
            )
        return (
            "The operation failed. Details are shown in the log below."
            if en else
            "処理に失敗しました。下部のログに詳細を表示しました。"
        )

    def _support(self):
        url = (self.app_cfg.get("support_url") or "").strip()
        if not url:
            messagebox.showinfo("Support Development" if self.lang == "en" else "開発を支援", ("The support page URL has not been configured yet.\n\nSet support_url in app_config.json before publishing." if self.lang == "en" else "支援ページURLはまだ設定されていません。\n\n公開前に app_config.json の support_url に OFUSE / Ko-fi などのURLを設定してください。"))
            return
        webbrowser.open(url)

    def _show_licenses(self):
        win = tk.Toplevel(self)
        en = self.lang == "en"
        win.title("Terms & Licenses" if en else "利用上の注意・ライセンス")
        win.geometry("760x620")
        try:
            p = icon_path()
            if p.exists():
                win.iconbitmap(default=str(p))
        except Exception:
            pass
        notebook = ttk.Notebook(win)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        terms = tk.Text(notebook, wrap="word")
        terms.insert("1.0", TERMS_TEXT_EN if en else TERMS_TEXT_JA)
        terms.configure(state="disabled")
        notebook.add(terms, text="Terms of Use" if en else "利用上の注意")

        licenses = tk.Text(notebook, wrap="word")
        blocks = []
        if LICENSES_DIR.exists():
            for p in sorted(LICENSES_DIR.glob("*.txt")):
                try:
                    blocks.append(f"===== {p.name} =====\n" + p.read_text(encoding="utf-8", errors="replace"))
                except Exception:
                    pass
        if not blocks:
            blocks.append("License documents were not found. Please run build_portable.bat again." if en else "ライセンス文書が見つかりません。build_portable.batを再実行してください。")
        licenses.insert("1.0", "\n\n".join(blocks))
        licenses.configure(state="disabled")
        notebook.add(licenses, text="Third-party Licenses" if en else "第三者ライセンス")

    def _background_startup_tasks(self):
        if not self._validate_tools():
            return
        threading.Thread(target=self._update_ytdlp_worker, daemon=True).start()
        if self.app_cfg.get("auto_check_updates", True):
            threading.Thread(target=self._check_updates_worker, args=(False,), daemon=True).start()

    def _update_ytdlp_worker(self):
        stamp = config_dir() / "engine_update_check.txt"
        try:
            if stamp.exists() and time.time() - stamp.stat().st_mtime < 24 * 3600:
                return
            stamp.write_text(str(time.time()), encoding="ascii")
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            r = subprocess.run([str(YT_DLP), "-U"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8", errors="replace", creationflags=creationflags, timeout=120)
            msg = (r.stdout or "").strip()
            if msg:
                self.q.put(("log", "[yt-dlp auto-update] " + msg.replace("\n", " | ")))
        except Exception as e:
            self.q.put(("log", f"[yt-dlp auto-update] Update check failed: {e}"))

    def _check_updates(self, manual=False):
        threading.Thread(target=self._check_updates_worker, args=(manual,), daemon=True).start()

    def _check_updates_worker(self, manual):
        repo = (self.app_cfg.get("github_repo") or "").strip().strip("/")
        if not repo:
            if manual:
                self.q.put(("update_info", ("The application update source has not been configured yet.\n\nSet github_repo in app_config.json to owner/repository after publishing on GitHub." if self.lang == "en" else "アプリ本体の更新先はまだ未設定です。\n\nGitHub公開後、app_config.json の github_repo に『owner/repository』を設定すると、起動時に最新版を自動確認できます。")))
            return
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": f"{APP_NAME}/{APP_VERSION}", "Accept": "application/vnd.github+json"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            tag = data.get("tag_name") or ""
            page = data.get("html_url") or f"https://github.com/{repo}/releases"
            if version_tuple(tag) > version_tuple(APP_VERSION):
                if not manual:
                    today = time.strftime("%Y-%m-%d")
                    if tag == self.skipped_update_version:
                        return
                    if tag == self.update_later_version and today == self.update_later_date:
                        return
                self.q.put(("update_available", (tag, page, manual)))
            elif manual:
                self.q.put(("update_info", f"現在の v{APP_VERSION} が最新版です。" if self.lang == "ja" else f"v{APP_VERSION} is the latest version."))
        except Exception as e:
            if manual:
                self.q.put(("update_info", (f"Could not check for updates.\n\n{e}" if self.lang == "en" else f"更新情報を確認できませんでした。\n\n{e}")))

    def _show_update_dialog(self, tag, page, manual=False):
        dlg = tk.Toplevel(self)
        dlg.title("新しいバージョンがあります" if self.lang == "ja" else "Update Available")
        dlg.resizable(False, False)
        dlg.transient(self)
        try:
            p = icon_path()
            if p.exists():
                dlg.iconbitmap(default=str(p))
        except Exception:
            pass

        frame = ttk.Frame(dlg, padding=18)
        frame.pack(fill="both", expand=True)
        if self.lang == "ja":
            msg = f"新しいバージョン {tag} が公開されています。\n\nどうしますか？"
            open_text, later_text, skip_text = "更新ページを開く", "あとで", "このバージョンをスキップ"
        else:
            msg = f"A new version {tag} is available.\n\nWhat would you like to do?"
            open_text, later_text, skip_text = "Open update page", "Later", "Skip this version"
        ttk.Label(frame, text=msg, justify="left").pack(anchor="w", pady=(0, 16))
        buttons = ttk.Frame(frame)
        buttons.pack(fill="x")

        def finish(choice):
            if choice == "open":
                webbrowser.open(page)
            elif choice == "later":
                self.update_later_version = tag
                self.update_later_date = time.strftime("%Y-%m-%d")
                self._save_settings()
            elif choice == "skip":
                self.skipped_update_version = tag
                if self.update_later_version == tag:
                    self.update_later_version = ""
                    self.update_later_date = ""
                self._save_settings()
            try:
                dlg.grab_release()
            except Exception:
                pass
            dlg.destroy()

        ttk.Button(buttons, text=open_text, command=lambda: finish("open")).pack(side="left")
        ttk.Button(buttons, text=later_text, command=lambda: finish("later")).pack(side="left", padx=8)
        ttk.Button(buttons, text=skip_text, command=lambda: finish("skip")).pack(side="left")
        dlg.protocol("WM_DELETE_WINDOW", lambda: finish("later"))
        dlg.update_idletasks()
        try:
            x = self.winfo_rootx() + max(0, (self.winfo_width() - dlg.winfo_width()) // 2)
            y = self.winfo_rooty() + max(0, (self.winfo_height() - dlg.winfo_height()) // 2)
            dlg.geometry(f"+{x}+{y}")
        except Exception:
            pass
        dlg.grab_set()
        dlg.focus_set()

    def _poll_queue(self):
        try:
            while True:
                kind, value = self.q.get_nowait()
                if kind == "log":
                    self._log(value)
                elif kind == "progress":
                    self.progress_var.set(value)
                    self.status_var.set(f"{self._tr('downloading')} {value:.1f}%")
                elif kind == "status":
                    self.status_var.set(value)
                elif kind == "analysis":
                    serial, data, formats = value
                    if serial != self.analysis_serial:
                        continue
                    self.video_info = data
                    self.title_var.set(self._tr("title") + (data.get("title") or "-"))
                    self.channel_var.set(self._tr("uploader") + (data.get("uploader") or data.get("channel") or "-"))
                    self.duration_var.set(self._tr("duration") + self._duration_text(data.get("duration")))
                    self._fill_formats(formats)
                    self.status_var.set(self._tr("analysis_done").format(count=len(formats)))
                    self.analyze_btn.configure(state="normal")
                    self._start_thumbnail(data, serial)
                elif kind == "analysis_error":
                    serial, err = value
                    if serial != self.analysis_serial:
                        continue
                    self.video_info = None
                    self.analyze_btn.configure(state="normal")
                    self.download_btn.configure(state="disabled")
                    self.status_var.set(self._tr("analysis_failed"))
                    self.preview_label.configure(image="", text=self._tr("preview_failed"))
                    self._log("[Analysis error] " + err)
                    messagebox.showerror("Could not retrieve video information" if self.lang == "en" else "動画情報を取得できません", self._friendly_error(err))
                elif kind == "thumbnail":
                    serial, path, tmp = value
                    if serial != self.analysis_serial:
                        shutil.rmtree(tmp, ignore_errors=True)
                        continue
                    if self.preview_tmp:
                        shutil.rmtree(self.preview_tmp, ignore_errors=True)
                    self.preview_tmp = tmp
                    try:
                        img = tk.PhotoImage(file=path)
                        scale = max(1, (img.width() + 379) // 380, (img.height() + 219) // 220)
                        if scale > 1:
                            img = img.subsample(scale, scale)
                        self.preview_photo = img
                        self.preview_label.configure(image=img, text="")
                    except Exception as e:
                        self.preview_label.configure(image="", text=(f"Preview error: {e}" if self.lang == "en" else f"プレビュー表示エラー: {e}"))
                elif kind == "thumbnail_error":
                    serial, tmp = value
                    shutil.rmtree(tmp, ignore_errors=True)
                    if serial == self.analysis_serial:
                        self.preview_label.configure(image="", text=("Could not display thumbnail." if self.lang == "en" else "サムネイルを表示できませんでした。"))
                elif kind == "done":
                    ok, details = value
                    self.download_btn.configure(state="normal" if self.video_info else "disabled")
                    self.cancel_btn.configure(state="disabled")
                    if ok:
                        self.progress_var.set(100)
                        self.status_var.set(self._tr("done"))
                        self._log("--- Download complete ---")
                    else:
                        self.status_var.set(self._tr("failed"))
                        self._log("--- Download failed ---")
                        messagebox.showerror("Download failed" if self.lang == "en" else "ダウンロード失敗", self._friendly_error(details))
                elif kind == "update_info":
                    messagebox.showinfo("Update Check" if self.lang == "en" else "更新確認", value)
                elif kind == "update_available":
                    tag, page, manual = value
                    self._show_update_dialog(tag, page, manual)
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)


if __name__ == "__main__":
    set_windows_app_id()
    App().mainloop()
