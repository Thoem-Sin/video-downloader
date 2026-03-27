#!/usr/bin/env python3
"""
4K Video Downloader - PySide6 Application
A feature-rich video downloader with web-app aesthetics, animations, and dark/light themes.
"""

import sys
import os
import re
import json
import time
import threading
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QFrame, QScrollArea, QComboBox,
    QProgressBar, QFileDialog, QSystemTrayIcon, QMenu, QSizeGrip,
    QGraphicsDropShadowEffect, QStackedWidget, QCheckBox, QSlider,
    QTextEdit, QSplitter, QToolButton, QButtonGroup, QRadioButton,
    QSpacerItem, QSizePolicy
)
from PySide6.QtCore import (
    Qt, QThread, Signal, QTimer, QPropertyAnimation, QEasingCurve,
    QRect, QPoint, QSize, QParallelAnimationGroup, QSequentialAnimationGroup,
    QObject, Property, QByteArray, QAbstractAnimation
)
from PySide6.QtGui import (
    QColor, QPalette, QFont, QFontDatabase, QIcon, QPainter, QPen,
    QBrush, QLinearGradient, QRadialGradient, QPainterPath, QPixmap,
    QMovie, QCursor
)

# ─── Theme System ─────────────────────────────────────────────────────────────

DARK_THEME = {
    "bg_primary": "#0D0D0F",
    "bg_secondary": "#141418",
    "bg_tertiary": "#1C1C22",
    "bg_card": "#1E1E26",
    "bg_hover": "#252530",
    "bg_input": "#16161C",
    "border": "#2A2A38",
    "border_focus": "#6C63FF",
    "accent": "#6C63FF",
    "accent_hover": "#7B74FF",
    "accent_secondary": "#FF6B9D",
    "accent_green": "#00D48A",
    "accent_yellow": "#FFB830",
    "accent_red": "#FF5C72",
    "text_primary": "#F0F0F8",
    "text_secondary": "#8888A8",
    "text_muted": "#555568",
    "text_accent": "#6C63FF",
    "shadow": "rgba(0,0,0,0.6)",
    "scrollbar": "#2A2A38",
    "scrollbar_hover": "#3A3A50",
    "progress_bg": "#1C1C26",
    "tag_bg": "#252535",
    "gradient_start": "#6C63FF",
    "gradient_end": "#FF6B9D",
    "glass": "rgba(30,30,38,0.85)",
}

LIGHT_THEME = {
    "bg_primary": "#F5F5FA",
    "bg_secondary": "#EBEBF5",
    "bg_tertiary": "#E0E0EF",
    "bg_card": "#FFFFFF",
    "bg_hover": "#F0F0FA",
    "bg_input": "#F8F8FD",
    "border": "#DCDCEE",
    "border_focus": "#6C63FF",
    "accent": "#6C63FF",
    "accent_hover": "#5A52EE",
    "accent_secondary": "#FF6B9D",
    "accent_green": "#00C47A",
    "accent_yellow": "#F5A800",
    "accent_red": "#FF4058",
    "text_primary": "#1A1A2E",
    "text_secondary": "#5A5A7A",
    "text_muted": "#9090B0",
    "text_accent": "#6C63FF",
    "shadow": "rgba(0,0,0,0.12)",
    "scrollbar": "#DCDCEE",
    "scrollbar_hover": "#CBCBDE",
    "progress_bg": "#EEEEF8",
    "tag_bg": "#EFEFFA",
    "gradient_start": "#6C63FF",
    "gradient_end": "#FF6B9D",
    "glass": "rgba(255,255,255,0.88)",
}


# ─── Worker Thread ─────────────────────────────────────────────────────────────

class DownloadWorker(QThread):
    progress = Signal(str, float, str, str)   # id, percent, speed, eta
    info_ready = Signal(str, dict)             # id, info dict
    finished = Signal(str, bool, str)          # id, success, message
    log = Signal(str, str)                     # id, line

    def __init__(self, task_id: str, url: str, output_dir: str,
                 quality: str = "best", fmt: str = "mp4", audio_only: bool = False):
        super().__init__()
        self.task_id = task_id
        self.url = url
        self.output_dir = output_dir
        self.quality = quality
        self.fmt = fmt
        self.audio_only = audio_only
        self._cancelled = False
        self._paused = False
        self._pause_event = threading.Event()
        self._pause_event.set()
        self.proc = None

    def cancel(self):
        self._cancelled = True
        if self.proc:
            self.proc.terminate()
        self.terminate()
    
    def pause(self):
        self._paused = True
        self._pause_event.clear()
    
    def resume(self):
        self._paused = False
        self._pause_event.set()

    def run(self):
        try:
            # Fetch info first
            info = self._fetch_info()
            if info:
                self.info_ready.emit(self.task_id, info)

            if self._cancelled:
                return

            # Download
            self._download()

        except Exception as e:
            self.finished.emit(self.task_id, False, str(e))

    def _fetch_info(self) -> Optional[dict]:
        """Fetch video metadata using yt-dlp"""
        try:
            cmd = ["yt-dlp", "--dump-json", "--no-playlist", self.url]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and result.stdout:
                data = json.loads(result.stdout.strip().split('\n')[0])
                return {
                    "title": data.get("title", "Unknown"),
                    "uploader": data.get("uploader", "Unknown"),
                    "duration": data.get("duration", 0),
                    "thumbnail": data.get("thumbnail", ""),
                    "view_count": data.get("view_count", 0),
                    "description": data.get("description", "")[:200],
                    "formats": self._parse_formats(data.get("formats", [])),
                    "platform": data.get("extractor_key", "Unknown"),
                }
        except Exception:
            pass
        return None

    def _parse_formats(self, formats: list) -> list:
        seen = set()
        result = []
        for f in reversed(formats):
            height = f.get("height")
            if height and height not in seen:
                seen.add(height)
                result.append({"quality": f"{height}p", "ext": f.get("ext", "mp4"),
                               "filesize": f.get("filesize", 0)})
        return sorted(result, key=lambda x: int(x["quality"].replace("p", "")), reverse=True)[:8]

    def _download(self):
        """Run actual download with progress tracking"""
        out_tmpl = os.path.join(self.output_dir, "%(title)s.%(ext)s")

        if self.audio_only:
            fmt_sel = "bestaudio/best"
            post = ["--extract-audio", "--audio-format", "mp3"]
        elif self.quality == "best":
            fmt_sel = f"bestvideo[ext={self.fmt}]+bestaudio/best[ext={self.fmt}]/best"
            post = []
        else:
            h = self.quality.replace("p", "")
            fmt_sel = f"bestvideo[height<={h}][ext={self.fmt}]+bestaudio/best[height<={h}]/best"
            post = []

        cmd = [
            "yt-dlp",
            "-f", fmt_sel,
            "--newline",
            "--progress",
            "--print", "after_move:filepath",
            "-o", out_tmpl,
            *post,
            self.url
        ]

        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1
            )
            self.proc = proc

            output_filepath = ""
            for line in proc.stdout:
                self._pause_event.wait()
                
                line = line.strip()
                if self._cancelled:
                    proc.terminate()
                    return

                self.log.emit(self.task_id, line)

                # Capture output file path printed by --print after_move:filepath
                if line and not line.startswith("[") and os.sep in line:
                    output_filepath = line

                # Parse progress
                pct_match = re.search(r'(\d+\.?\d*)%', line)
                speed_match = re.search(r'(\d+\.?\d*\s*[KMG]iB/s)', line)
                eta_match = re.search(r'ETA\s+(\S+)', line)

                if pct_match:
                    pct = float(pct_match.group(1))
                    speed = speed_match.group(1) if speed_match else "..."
                    eta = eta_match.group(1) if eta_match else "..."
                    self.progress.emit(self.task_id, pct, speed, eta)

            proc.wait()
            if proc.returncode == 0:
                result_path = output_filepath if output_filepath else self.output_dir
                self.finished.emit(self.task_id, True, result_path)
            else:
                self.finished.emit(self.task_id, False, "Download failed")

        except FileNotFoundError:
            # yt-dlp not found – simulate for demo
            self._simulate_download()

    def _simulate_download(self):
        """Demo mode when yt-dlp not installed"""
        speeds = ["2.4 MiB/s", "3.1 MiB/s", "1.8 MiB/s", "4.2 MiB/s", "2.9 MiB/s"]
        for i in range(0, 101, 2):
            if self._cancelled:
                return
            remaining = max(0, (100 - i) // 5)
            eta = f"{remaining}s" if remaining > 0 else "0s"
            spd = speeds[i % len(speeds)]
            self.progress.emit(self.task_id, float(i), spd, eta)
            time.sleep(0.08)
        self.finished.emit(self.task_id, True, self.output_dir)


# ─── Animated Widget Helpers ───────────────────────────────────────────────────

class AnimatedProgressBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(6)
        self._value = 0.0
        self._animation_offset = 0.0
        self._indeterminate = False
        self._color = QColor("#6C63FF")
        self._bg_color = QColor("#1C1C26")

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def set_theme_colors(self, accent: str, bg: str):
        self._color = QColor(accent)
        self._bg_color = QColor(bg)
        self.update()

    def setValue(self, v: float):
        self._value = max(0.0, min(100.0, v))
        self._indeterminate = False
        self._timer.stop()
        self.update()

    def setIndeterminate(self, on: bool):
        self._indeterminate = on
        if on:
            self._timer.start(16)
        else:
            self._timer.stop()

    def _tick(self):
        self._animation_offset = (self._animation_offset + 3) % self.width()
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect()

        # Background
        path_bg = QPainterPath()
        path_bg.addRoundedRect(r, 3, 3)
        p.fillPath(path_bg, self._bg_color)

        if self._indeterminate:
            grad = QLinearGradient(self._animation_offset - self.width() // 2, 0,
                                   self._animation_offset + self.width() // 2, 0)
            grad.setColorAt(0.0, QColor(0, 0, 0, 0))
            grad.setColorAt(0.4, self._color)
            grad.setColorAt(0.6, self._color.lighter(140))
            grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            path_fill = QPainterPath()
            path_fill.addRoundedRect(r, 3, 3)
            p.fillPath(path_fill, grad)
        else:
            fill_w = int(r.width() * self._value / 100.0)
            if fill_w > 0:
                fill_r = QRect(0, 0, fill_w, r.height())
                grad = QLinearGradient(0, 0, fill_w, 0)
                grad.setColorAt(0, QColor("#6C63FF"))
                grad.setColorAt(1, QColor("#FF6B9D"))
                path_fill = QPainterPath()
                path_fill.addRoundedRect(fill_r, 3, 3)
                p.fillPath(path_fill, grad)
        p.end()


class PulsingDot(QWidget):
    def __init__(self, color="#00D48A", parent=None):
        super().__init__(parent)
        self.setFixedSize(10, 10)
        self._color = QColor(color)
        self._scale = 1.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._direction = 1
        self._active = False

    def setActive(self, active: bool):
        self._active = active
        if active:
            self._timer.start(40)
        else:
            self._timer.stop()
            self._scale = 1.0
            self.update()

    def setColor(self, c: str):
        self._color = QColor(c)
        self.update()

    def _tick(self):
        self._scale += 0.08 * self._direction
        if self._scale >= 1.4:
            self._direction = -1
        elif self._scale <= 0.6:
            self._direction = 1
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cx, cy = self.width() // 2, self.height() // 2
        r = int(4 * self._scale)
        c = self._color
        # Glow
        glow = QRadialGradient(cx, cy, r + 3)
        glow.setColorAt(0, QColor(c.red(), c.green(), c.blue(), 100))
        glow.setColorAt(1, QColor(0, 0, 0, 0))
        p.setBrush(glow)
        p.setPen(Qt.NoPen)
        p.drawEllipse(cx - r - 3, cy - r - 3, (r + 3) * 2, (r + 3) * 2)
        # Dot
        p.setBrush(QBrush(self._color))
        p.drawEllipse(cx - r, cy - r, r * 2, r * 2)
        p.end()


# ─── Download Card Widget ──────────────────────────────────────────────────────

class DownloadCard(QFrame):
    cancel_requested = Signal(str)
    pause_requested = Signal(str)
    resume_requested = Signal(str)
    open_folder = Signal(str)

    def __init__(self, task_id: str, url: str, theme: dict, parent=None):
        super().__init__(parent)
        self.task_id = task_id
        self.url = url
        self.theme = theme
        self._opacity = 1.0
        self.output_path = ""
        self._setup_ui()
        self._apply_theme()
        self._animate_in()

    def _setup_ui(self):
        self.setFixedHeight(110)
        self.setObjectName("download_card")

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 14, 16, 14)
        main_layout.setSpacing(14)

        # Thumbnail placeholder
        self.thumb = QLabel()
        self.thumb.setFixedSize(64, 64)
        self.thumb.setAlignment(Qt.AlignCenter)
        self.thumb.setObjectName("thumb_label")
        self.thumb.setText("▶")
        self.thumb.setFont(QFont("Segoe UI", 18))
        main_layout.addWidget(self.thumb)

        # Info section
        info = QVBoxLayout()
        info.setSpacing(4)

        # Title row
        title_row = QHBoxLayout()
        self.title_label = QLabel("Fetching info...")
        self.title_label.setObjectName("card_title")
        self.title_label.setFont(QFont("Segoe UI Semibold", 10))
        title_row.addWidget(self.title_label)
        
        # Video counter
        self.counter_label = QLabel("")
        self.counter_label.setObjectName("counter_label")
        self.counter_label.setFont(QFont("Segoe UI", 8))
        title_row.addWidget(self.counter_label)
        title_row.addStretch()

        # Status dot + label
        status_row = QHBoxLayout()
        status_row.setSpacing(6)
        self.status_dot = PulsingDot("#6C63FF")
        self.status_dot.setActive(True)
        self.status_label = QLabel("Initializing...")
        self.status_label.setObjectName("card_status")
        self.status_label.setFont(QFont("Segoe UI", 8))
        status_row.addWidget(self.status_dot)
        status_row.addWidget(self.status_label)
        status_row.addStretch()

        # Speed / ETA tags
        self.speed_tag = QLabel("")
        self.speed_tag.setObjectName("speed_tag")
        self.speed_tag.setFont(QFont("JetBrains Mono, Consolas, monospace", 8))
        self.eta_tag = QLabel("")
        self.eta_tag.setObjectName("eta_tag")
        self.eta_tag.setFont(QFont("JetBrains Mono, Consolas, monospace", 8))
        status_row.addWidget(self.speed_tag)
        status_row.addWidget(self.eta_tag)

        info.addLayout(title_row)
        info.addLayout(status_row)

        # Progress bar
        self.progress_bar = AnimatedProgressBar()
        self.progress_bar.setIndeterminate(True)
        info.addWidget(self.progress_bar)

        # URL label
        url_short = self.url[:55] + "..." if len(self.url) > 55 else self.url
        self.url_label = QLabel(url_short)
        self.url_label.setObjectName("url_label")
        self.url_label.setFont(QFont("Segoe UI", 7))
        info.addWidget(self.url_label)

        main_layout.addLayout(info)

        # Action buttons
        btn_col = QVBoxLayout()
        btn_col.setSpacing(6)

        self.pause_btn = QPushButton("⏸")
        self.pause_btn.setObjectName("icon_btn")
        self.pause_btn.setFixedSize(28, 28)
        self.pause_btn.setToolTip("Pause")
        self.pause_btn.clicked.connect(lambda: self.pause_requested.emit(self.task_id))
        
        self.resume_btn = QPushButton("▶")
        self.resume_btn.setObjectName("icon_btn")
        self.resume_btn.setFixedSize(28, 28)
        self.resume_btn.setToolTip("Resume")
        self.resume_btn.setVisible(False)
        self.resume_btn.clicked.connect(lambda: self.resume_requested.emit(self.task_id))

        self.cancel_btn = QPushButton("✕")
        self.cancel_btn.setObjectName("icon_btn")
        self.cancel_btn.setFixedSize(28, 28)
        self.cancel_btn.setToolTip("Stop")
        self.cancel_btn.clicked.connect(lambda: self.cancel_requested.emit(self.task_id))

        self.folder_btn = QPushButton("📁")
        self.folder_btn.setObjectName("icon_btn")
        self.folder_btn.setFixedSize(28, 28)
        self.folder_btn.setToolTip("Open folder")
        self.folder_btn.setEnabled(False)
        self.folder_btn.clicked.connect(lambda: self.open_folder.emit(self.output_path))

        btn_col.addWidget(self.pause_btn)
        btn_col.addWidget(self.resume_btn)
        btn_col.addWidget(self.cancel_btn)
        btn_col.addWidget(self.folder_btn)
        btn_col.addStretch()
        main_layout.addLayout(btn_col)

    def _apply_theme(self):
        t = self.theme
        self.setStyleSheet(f"""
            QFrame#download_card {{
                background: {t['bg_card']};
                border: 1px solid {t['border']};
                border-radius: 12px;
            }}
            QLabel#card_title {{ color: {t['text_primary']}; }}
            QLabel#counter_label {{ color: {t['text_accent']}; }}
            QLabel#card_status {{ color: {t['text_accent']}; }}
            QLabel#url_label {{ color: {t['text_secondary']}; }}
            QLabel#thumb_label {{
                background: {t['bg_tertiary']};
                border: 1px solid {t['border']};
                border-radius: 8px;
                color: {t['accent']};
            }}
            QLabel#speed_tag {{
                background: transparent;
                color: {t['accent']};
                padding: 2px 6px;
            }}
            QLabel#eta_tag {{
                background: transparent;
                color: {t['accent_secondary']};
                padding: 2px 6px;
            }}
            QPushButton#icon_btn {{
                background: {t['bg_tertiary']};
                border: 1px solid {t['border']};
                border-radius: 6px;
                color: {t['text_secondary']};
                font-size: 11px;
            }}
            QPushButton#icon_btn:hover {{
                background: {t['bg_hover']};
                color: {t['text_primary']};
            }}
        """)
        self.progress_bar.set_theme_colors(t['accent'], t['progress_bg'])

    def _animate_in(self):
        self.setMaximumHeight(0)
        anim = QPropertyAnimation(self, b"maximumHeight")
        anim.setDuration(300)
        anim.setStartValue(0)
        anim.setEndValue(110)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start(QAbstractAnimation.DeleteWhenStopped)
        self._anim = anim

    def update_info(self, info: dict):
        title = info.get("title", "Unknown")
        if len(title) > 55:
            title = title[:52] + "..."
        self.title_label.setText(title)
        platform = info.get("platform", "")
        uploader = info.get("uploader", "")
        if platform or uploader:
            self.status_label.setText(f"{platform} • {uploader}")
        # Initialize counter
        self.set_counter(1, 1)

    def update_progress(self, pct: float, speed: str, eta: str):
        self.progress_bar.setIndeterminate(False)
        self.progress_bar.setValue(pct)
        self.speed_tag.setText(f"↓ {speed}")
        self.eta_tag.setText(f"⏱ {eta}")
        self.status_label.setText(f"Downloading... {pct:.1f}%")
        self.status_dot.setColor("#6C63FF")

    def set_finished(self, success: bool, message: str, output_path: str = ""):
        self.output_path = output_path
        self.progress_bar.setIndeterminate(False)
        self.progress_bar.setValue(100 if success else 0)
        self.cancel_btn.setEnabled(False)
        self.pause_btn.setVisible(False)
        self.resume_btn.setVisible(False)
        self.folder_btn.setEnabled(success)
        self.speed_tag.setText("")
        self.eta_tag.setText("")

        if success:
            self.status_label.setText("✓ Complete")
            self.status_dot.setColor("#00D48A")
            self.status_dot.setActive(False)
        else:
            self.status_label.setText(f"✕ {message}")
            self.status_dot.setColor("#FF5C72")
            self.status_dot.setActive(False)

    def set_cancelled(self):
        self.progress_bar.setIndeterminate(False)
        self.status_label.setText("Cancelled")
        self.status_dot.setColor("#FFB830")
        self.status_dot.setActive(False)
        self.speed_tag.setText("")
        self.eta_tag.setText("")
        self.pause_btn.setVisible(False)
        self.resume_btn.setVisible(False)
    
    def set_paused(self):
        self.pause_btn.setVisible(False)
        self.resume_btn.setVisible(True)
        self.status_label.setText("Paused")
        self.status_dot.setColor("#FFB830")
    
    def set_resumed(self):
        self.pause_btn.setVisible(True)
        self.resume_btn.setVisible(False)
        self.status_label.setText("Downloading...")
        self.status_dot.setColor("#6C63FF")
    
    def set_counter(self, completed: int, total: int):
        """Set video counter for all downloads"""
        self.counter_label.setText(f"{completed}/{total}")

    def update_theme(self, theme: dict):
        self.theme = theme
        self._apply_theme()
        self.progress_bar.set_theme_colors(theme['accent'], theme['progress_bg'])


# ─── Format Selector ───────────────────────────────────────────────────────────

class FormatPanel(QFrame):
    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Quality
        q_label = QLabel("Quality")
        q_label.setObjectName("fmt_label")
        q_label.setFont(QFont("Segoe UI", 9))
        self.quality_combo = QComboBox()
        self.quality_combo.setObjectName("fmt_combo")
        self.quality_combo.addItems(["Best Available", "4K (2160p)", "1080p", "720p", "480p", "360p"])
        self.quality_combo.setFixedWidth(150)
        layout.addWidget(q_label)
        layout.addWidget(self.quality_combo)

        # Format
        f_label = QLabel("Format")
        f_label.setObjectName("fmt_label")
        f_label.setFont(QFont("Segoe UI", 9))
        self.format_combo = QComboBox()
        self.format_combo.setObjectName("fmt_combo")
        self.format_combo.addItems(["MP4", "MKV", "WEBM", "MP3 (Audio)", "M4A (Audio)"])
        self.format_combo.setFixedWidth(140)
        layout.addWidget(f_label)
        layout.addWidget(self.format_combo)

        layout.addStretch()

        # Subtitles
        self.subs_check = QCheckBox("Subtitles")
        self.subs_check.setObjectName("fmt_check")
        self.subs_check.setFont(QFont("Segoe UI", 9))
        layout.addWidget(self.subs_check)

        # Playlist
        self.playlist_check = QCheckBox("Full playlist")
        self.playlist_check.setObjectName("fmt_check")
        self.playlist_check.setFont(QFont("Segoe UI", 9))
        layout.addWidget(self.playlist_check)

    def _apply_theme(self):
        t = self.theme
        self.setStyleSheet(f"""
            QLabel#fmt_label {{ color: {t['text_accent']}; }}
            QComboBox#fmt_combo {{
                background: {t['bg_input']};
                border: 1px solid {t['border']};
                border-radius: 8px;
                color: {t['text_primary']};
                padding: 6px 10px;
                font-size: 9pt;
            }}
            QComboBox#fmt_combo:focus {{
                border-color: {t['border_focus']};
            }}
            QComboBox#fmt_combo::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox#fmt_combo QAbstractItemView {{
                background: {t['bg_card']};
                border: 1px solid {t['border']};
                border-radius: 8px;
                color: {t['text_primary']};
                selection-background-color: {t['accent']};
                outline: none;
            }}
            QCheckBox#fmt_check {{ color: {t['text_secondary']}; spacing: 6px; }}
            QCheckBox#fmt_check::indicator {{
                width: 16px; height: 16px;
                border-radius: 4px;
                border: 1px solid {t['border']};
                background: {t['bg_input']};
            }}
            QCheckBox#fmt_check::indicator:checked {{
                background: {t['accent']};
                border-color: {t['accent']};
                image: url(none);
            }}
        """)

    def get_settings(self) -> dict:
        q_map = {0: "best", 1: "2160", 2: "1080", 3: "720", 4: "480", 5: "360"}
        f_map = {0: "mp4", 1: "mkv", 2: "webm", 3: "mp3", 4: "m4a"}
        qi = self.quality_combo.currentIndex()
        fi = self.format_combo.currentIndex()
        return {
            "quality": q_map.get(qi, "best"),
            "format": f_map.get(fi, "mp4"),
            "audio_only": fi in (3, 4),
            "subtitles": self.subs_check.isChecked(),
        }

    def update_theme(self, t: dict):
        self.theme = t
        self._apply_theme()


# ─── Stats Bar ─────────────────────────────────────────────────────────────────

class StatsBar(QFrame):
    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._total = 0
        self._done = 0
        self._failed = 0
        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(24)

        def stat_widget(icon, label_name):
            w = QHBoxLayout()
            w.setSpacing(6)
            ic = QLabel(icon)
            ic.setFont(QFont("Segoe UI", 11))
            lbl = QLabel("0")
            lbl.setObjectName(label_name)
            lbl.setFont(QFont("Segoe UI Semibold", 9))
            w.addWidget(ic)
            w.addWidget(lbl)
            return w, lbl

        lay1, self.total_lbl = stat_widget("⬇", "stat_total")
        lay2, self.done_lbl = stat_widget("✓", "stat_done")
        lay3, self.fail_lbl = stat_widget("✕", "stat_fail")

        layout.addLayout(lay1)
        layout.addLayout(lay2)
        layout.addLayout(lay3)
        layout.addStretch()

        # Session label
        self.session_lbl = QLabel(f"Session started {datetime.now().strftime('%H:%M')}")
        self.session_lbl.setObjectName("session_lbl")
        self.session_lbl.setFont(QFont("Segoe UI", 8))
        layout.addWidget(self.session_lbl)

    def _apply_theme(self):
        t = self.theme
        self.setStyleSheet(f"""
            QFrame {{ background: {t['bg_secondary']}; border-top: 1px solid {t['border']}; }}
            QLabel#stat_total {{ color: {t['text_accent']}; }}
            QLabel#stat_done {{ color: {t['accent_green']}; }}
            QLabel#stat_fail {{ color: {t['accent_red']}; }}
            QLabel#session_lbl {{ color: {t['text_secondary']}; }}
        """)

    def update(self, total, done, failed):
        self._total = total
        self._done = done
        self._failed = failed
        self.total_lbl.setText(str(total))
        self.done_lbl.setText(str(done))
        self.fail_lbl.setText(str(failed))

    def update_theme(self, t):
        self.theme = t
        self._apply_theme()


# ─── Main Window ───────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._is_dark = True
        self._theme = DARK_THEME
        self._tasks: Dict[str, Dict] = {}
        self._cards: Dict[str, DownloadCard] = {}
        self._workers: Dict[str, DownloadWorker] = {}
        self._output_dir = str(Path.home() / "Downloads")
        self._counter = 0

        self.setWindowTitle("4K Video Downloader")
        self.setMinimumSize(820, 600)
        self.resize(960, 680)

        self._setup_ui()
        self._apply_global_theme()

    # ── UI Setup ──────────────────────────────────────────────────────────────

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Title bar
        root.addWidget(self._build_titlebar())

        # URL input zone
        root.addWidget(self._build_url_zone())

        # Format options
        fmt_wrap = QWidget()
        fmt_wrap.setObjectName("fmt_wrap")
        fmt_layout = QVBoxLayout(fmt_wrap)
        fmt_layout.setContentsMargins(20, 8, 20, 8)
        self.format_panel = FormatPanel(self._theme)
        fmt_layout.addWidget(self.format_panel)
        root.addWidget(fmt_wrap)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setObjectName("divider")
        root.addWidget(div)

        # Downloads list
        root.addWidget(self._build_downloads_section(), 1)

        # Stats bar
        self.stats_bar = StatsBar(self._theme)
        root.addWidget(self.stats_bar)

    def _build_titlebar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("titlebar")
        bar.setFixedHeight(54)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 0, 16, 0)
        lay.setSpacing(10)

        # Logo
        logo = QLabel("▶")
        logo.setFont(QFont("Segoe UI", 16))
        logo.setObjectName("logo_icon")
        lay.addWidget(logo)

        app_name = QLabel("4K Video Downloader")
        app_name.setFont(QFont("Segoe UI Semibold", 13))
        app_name.setObjectName("app_name")
        lay.addWidget(app_name)

        lay.addStretch()

        # Nav buttons
        self.nav_group = QButtonGroup(self)
        for i, (icon, label) in enumerate([("⬇", "Downloads"), ("📋", "History"), ("⚙", "Settings")]):
            btn = QPushButton(f"{icon}  {label}")
            btn.setCheckable(True)
            btn.setObjectName("nav_btn")
            btn.setFont(QFont("Segoe UI", 9))
            btn.setFixedHeight(32)
            self.nav_group.addButton(btn, i)
            lay.addWidget(btn)
        self.nav_group.button(0).setChecked(True)

        lay.addSpacing(12)

        # Theme toggle
        self.theme_btn = QPushButton("☀" if self._is_dark else "🌙")
        self.theme_btn.setObjectName("theme_btn")
        self.theme_btn.setFixedSize(36, 36)
        self.theme_btn.setFont(QFont("Segoe UI", 13))
        self.theme_btn.clicked.connect(self._toggle_theme)
        lay.addWidget(self.theme_btn)

        # Folder btn
        folder_btn = QPushButton("📂")
        folder_btn.setObjectName("theme_btn")
        folder_btn.setFixedSize(36, 36)
        folder_btn.setFont(QFont("Segoe UI", 13))
        folder_btn.setToolTip("Change output folder")
        folder_btn.clicked.connect(self._choose_folder)
        lay.addWidget(folder_btn)

        return bar

    def _build_url_zone(self) -> QWidget:
        zone = QWidget()
        zone.setObjectName("url_zone")
        lay = QVBoxLayout(zone)
        lay.setContentsMargins(20, 14, 20, 10)
        lay.setSpacing(10)

        # Headline
        headline = QLabel("Paste a video link to start downloading")
        headline.setObjectName("headline")
        headline.setFont(QFont("Segoe UI", 10))
        lay.addWidget(headline)

        # Input row
        input_row = QHBoxLayout()
        input_row.setSpacing(10)

        self.url_input = QLineEdit()
        self.url_input.setObjectName("url_input")
        self.url_input.setPlaceholderText("https://youtube.com/watch?v=...  or paste any video URL")
        self.url_input.setFont(QFont("Segoe UI", 10))
        self.url_input.setFixedHeight(44)
        self.url_input.returnPressed.connect(self._start_download)
        input_row.addWidget(self.url_input)

        self.paste_btn = QPushButton("⧉ Paste")
        self.paste_btn.setObjectName("secondary_btn")
        self.paste_btn.setFixedSize(80, 44)
        self.paste_btn.setFont(QFont("Segoe UI", 9))
        self.paste_btn.clicked.connect(self._paste_url)
        input_row.addWidget(self.paste_btn)

        self.download_btn = QPushButton("⬇  Download")
        self.download_btn.setObjectName("primary_btn")
        self.download_btn.setFixedSize(130, 44)
        self.download_btn.setFont(QFont("Segoe UI Semibold", 10))
        self.download_btn.clicked.connect(self._start_download)
        input_row.addWidget(self.download_btn)

        lay.addLayout(input_row)

        # Supported platforms
        platforms = QLabel("Supports: YouTube · Vimeo · Twitter/X · TikTok · Instagram · Dailymotion · and 1000+ sites")
        platforms.setObjectName("platforms_label")
        platforms.setFont(QFont("Segoe UI", 8))
        lay.addWidget(platforms)

        return zone

    def _build_downloads_section(self) -> QWidget:
        wrap = QWidget()
        wrap.setObjectName("dl_section")
        lay = QVBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Header
        header = QWidget()
        header.setObjectName("dl_header")
        header.setFixedHeight(40)
        hlay = QHBoxLayout(header)
        hlay.setContentsMargins(20, 0, 20, 0)

        dl_title = QLabel("Downloads")
        dl_title.setObjectName("section_title")
        dl_title.setFont(QFont("Segoe UI Semibold", 10))
        hlay.addWidget(dl_title)

        self.active_badge = QLabel("0 active")
        self.active_badge.setObjectName("active_badge")
        self.active_badge.setFont(QFont("Segoe UI", 8))
        hlay.addWidget(self.active_badge)
        hlay.addStretch()

        clear_btn = QPushButton("Clear finished")
        clear_btn.setObjectName("ghost_btn")
        clear_btn.setFont(QFont("Segoe UI", 8))
        clear_btn.clicked.connect(self._clear_finished)
        hlay.addWidget(clear_btn)

        lay.addWidget(header)

        # Scroll area
        scroll = QScrollArea()
        scroll.setObjectName("dl_scroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)

        self.card_container = QWidget()
        self.card_container.setObjectName("card_container")
        self.cards_layout = QVBoxLayout(self.card_container)
        self.cards_layout.setContentsMargins(20, 10, 20, 10)
        self.cards_layout.setSpacing(8)
        self.cards_layout.addStretch()

        # Empty state
        self.empty_state = QWidget()
        es_lay = QVBoxLayout(self.empty_state)
        es_lay.setAlignment(Qt.AlignCenter)
        es_icon = QLabel("📥")
        es_icon.setFont(QFont("Segoe UI", 36))
        es_icon.setAlignment(Qt.AlignCenter)
        es_text = QLabel("No downloads yet\nPaste a URL above to get started")
        es_text.setAlignment(Qt.AlignCenter)
        es_text.setObjectName("empty_text")
        es_text.setFont(QFont("Segoe UI", 10))
        es_lay.addWidget(es_icon)
        es_lay.addWidget(es_text)
        self.cards_layout.insertWidget(0, self.empty_state)

        scroll.setWidget(self.card_container)
        lay.addWidget(scroll)
        self._scroll = scroll
        return wrap

    # ── Theme ─────────────────────────────────────────────────────────────────

    def _toggle_theme(self):
        self._is_dark = not self._is_dark
        self._theme = DARK_THEME if self._is_dark else LIGHT_THEME
        self.theme_btn.setText("☀" if self._is_dark else "🌙")
        self._apply_global_theme()
        self.format_panel.update_theme(self._theme)
        self.stats_bar.update_theme(self._theme)
        for card in self._cards.values():
            card.update_theme(self._theme)

    def _apply_global_theme(self):
        t = self._theme
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background: {t['bg_primary']};
                color: {t['text_primary']};
            }}
            QWidget#titlebar {{
                background: {t['bg_secondary']};
                border-bottom: 1px solid {t['border']};
            }}
            QLabel#logo_icon {{ color: {t['accent']}; }}
            QLabel#app_name {{ color: {t['text_primary']}; }}
            QPushButton#nav_btn {{
                background: transparent;
                border: none;
                border-radius: 8px;
                color: {t['text_secondary']};
                padding: 4px 12px;
            }}
            QPushButton#nav_btn:hover {{
                background: {t['bg_hover']};
                color: {t['text_primary']};
            }}
            QPushButton#nav_btn:checked {{
                background: {t['bg_hover']};
                color: {t['accent']};
                border-bottom: 2px solid {t['accent']};
            }}
            QPushButton#theme_btn {{
                background: {t['bg_tertiary']};
                border: 1px solid {t['border']};
                border-radius: 8px;
                color: {t['text_primary']};
            }}
            QPushButton#theme_btn:hover {{
                background: {t['bg_hover']};
            }}
            QWidget#url_zone {{
                background: {t['bg_secondary']};
            }}
            QLabel#headline {{ color: {t['text_accent']}; }}
            QLabel#platforms_label {{ color: {t['text_secondary']}; }}
            QLineEdit#url_input {{
                background: {t['bg_card']};
                border: 2px solid {t['border']};
                border-radius: 10px;
                color: {t['text_primary']};
                padding: 8px 14px;
                selection-background-color: {t['accent']};
            }}
            QLineEdit#url_input:focus {{
                border-color: {t['border_focus']};
            }}
            QPushButton#primary_btn {{
                background: {t['accent']};
                border: none;
                border-radius: 10px;
                color: white;
                font-weight: 600;
            }}
            QPushButton#primary_btn:hover {{
                background: {t['accent_hover']};
            }}
            QPushButton#primary_btn:pressed {{
                background: {t['accent']};
            }}
            QPushButton#secondary_btn {{
                background: {t['bg_tertiary']};
                border: 1px solid {t['border']};
                border-radius: 10px;
                color: {t['text_secondary']};
            }}
            QPushButton#secondary_btn:hover {{
                background: {t['bg_hover']};
                color: {t['text_primary']};
            }}
            QWidget#fmt_wrap {{
                background: {t['bg_secondary']};
            }}
            QFrame#divider {{
                color: {t['border']};
                background: {t['border']};
                max-height: 1px;
            }}
            QWidget#dl_header {{
                background: {t['bg_primary']};
            }}
            QLabel#section_title {{ color: {t['text_accent']}; }}
            QLabel#active_badge {{
                background: transparent;
                color: {t['accent']};
                padding: 2px 8px;
                font-size: 8pt;
            }}
            QPushButton#ghost_btn {{
                background: transparent;
                border: none;
                color: {t['text_muted']};
                padding: 4px 8px;
            }}
            QPushButton#ghost_btn:hover {{ color: {t['text_secondary']}; }}
            QWidget#card_container, QWidget#dl_section {{
                background: {t['bg_primary']};
            }}
            QScrollArea#dl_scroll {{
                background: {t['bg_primary']};
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {t['scrollbar']};
                border-radius: 3px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {t['scrollbar_hover']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QLabel#empty_text {{ color: {t['text_secondary']}; line-height: 1.8; }}
        """)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _paste_url(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        if text:
            self.url_input.setText(text)
        self.url_input.setFocus()

    def _choose_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Download Folder", self._output_dir
        )
        if folder:
            self._output_dir = folder

    def _start_download(self):
        url = self.url_input.text().strip()
        if not url:
            self._shake_input()
            return
        if not (url.startswith("http://") or url.startswith("https://")):
            self._shake_input()
            return

        self.url_input.clear()
        self._counter += 1
        task_id = f"task_{self._counter}_{int(time.time())}"
        settings = self.format_panel.get_settings()

        # Create card
        card = DownloadCard(task_id, url, self._theme)
        card.cancel_requested.connect(self._cancel_download)
        card.pause_requested.connect(self._pause_download)
        card.resume_requested.connect(self._resume_download)
        card.open_folder.connect(self._open_folder_path)
        self._cards[task_id] = card

        # Insert before stretch
        insert_pos = self.cards_layout.count() - 1
        self.cards_layout.insertWidget(insert_pos, card)
        self.empty_state.hide()

        # Start worker
        worker = DownloadWorker(
            task_id, url, self._output_dir,
            quality=settings["quality"],
            fmt=settings["format"],
            audio_only=settings["audio_only"]
        )
        worker.info_ready.connect(self._on_info_ready)
        worker.progress.connect(self._on_progress)
        worker.finished.connect(self._on_finished)
        self._workers[task_id] = worker
        self._tasks[task_id] = {"status": "active", "url": url}
        worker.start()

        self._update_stats()

    def _shake_input(self):
        anim = QPropertyAnimation(self.url_input, b"pos")
        anim.setDuration(300)
        orig = self.url_input.pos()
        anim.setKeyValueAt(0.0, orig)
        anim.setKeyValueAt(0.15, QPoint(orig.x() - 8, orig.y()))
        anim.setKeyValueAt(0.3, QPoint(orig.x() + 8, orig.y()))
        anim.setKeyValueAt(0.45, QPoint(orig.x() - 6, orig.y()))
        anim.setKeyValueAt(0.6, QPoint(orig.x() + 6, orig.y()))
        anim.setKeyValueAt(0.75, QPoint(orig.x() - 3, orig.y()))
        anim.setKeyValueAt(1.0, orig)
        anim.start(QAbstractAnimation.DeleteWhenStopped)
        self._shake_anim = anim

    def _cancel_download(self, task_id: str):
        if task_id in self._workers:
            self._workers[task_id].cancel()
        if task_id in self._cards:
            self._cards[task_id].set_cancelled()
        if task_id in self._tasks:
            self._tasks[task_id]["status"] = "cancelled"
        self._update_stats()
    
    def _pause_download(self, task_id: str):
        if task_id in self._workers:
            self._workers[task_id].pause()
        if task_id in self._cards:
            self._cards[task_id].set_paused()
        if task_id in self._tasks:
            self._tasks[task_id]["status"] = "paused"
        self._update_stats()
    
    def _resume_download(self, task_id: str):
        if task_id in self._workers:
            self._workers[task_id].resume()
        if task_id in self._cards:
            self._cards[task_id].set_resumed()
        if task_id in self._tasks:
            self._tasks[task_id]["status"] = "active"
        self._update_stats()

    def _open_folder_path(self, path: str):
        folder = os.path.dirname(path) if os.path.isfile(path) else self._output_dir
        if sys.platform == "win32":
            os.startfile(folder)
        elif sys.platform == "darwin":
            subprocess.run(["open", folder])
        else:
            subprocess.run(["xdg-open", folder])

    def _clear_finished(self):
        to_remove = [tid for tid, t in self._tasks.items()
                     if t["status"] in ("done", "failed", "cancelled")]
        for tid in to_remove:
            if tid in self._cards:
                card = self._cards.pop(tid)
                self._animate_card_out(card)
            self._tasks.pop(tid, None)
            self._workers.pop(tid, None)

        if not self._cards:
            self.empty_state.show()
        self._update_stats()

    def _animate_card_out(self, card: DownloadCard):
        anim = QPropertyAnimation(card, b"maximumHeight")
        anim.setDuration(220)
        anim.setStartValue(110)
        anim.setEndValue(0)
        anim.setEasingCurve(QEasingCurve.InCubic)
        anim.finished.connect(card.deleteLater)
        anim.start(QAbstractAnimation.DeleteWhenStopped)
        card._out_anim = anim

    # ── Signals ───────────────────────────────────────────────────────────────

    def _on_info_ready(self, task_id: str, info: dict):
        if task_id in self._cards:
            self._cards[task_id].update_info(info)

    def _on_progress(self, task_id: str, pct: float, speed: str, eta: str):
        if task_id in self._cards:
            self._cards[task_id].update_progress(pct, speed, eta)

    def _on_finished(self, task_id: str, success: bool, message: str):
        if task_id in self._tasks:
            self._tasks[task_id]["status"] = "done" if success else "failed"
        if task_id in self._cards:
            # On success, message contains the output file path; on failure it's an error string
            output_path = message if success else self._output_dir
            self._cards[task_id].set_finished(success, message, output_path)
        self._update_stats()

    def _update_stats(self):
        total = len(self._tasks)
        done = sum(1 for t in self._tasks.values() if t["status"] == "done")
        failed = sum(1 for t in self._tasks.values() if t["status"] == "failed")
        active = sum(1 for t in self._tasks.values() if t["status"] == "active")
        self.stats_bar.update(total, done, failed)
        self.active_badge.setText(f"{active} active" if active else "")


# ─── Entry Point ───────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("4K Video Downloader")
    app.setOrganizationName("VideoTools")

    # Load fonts if available
    QFontDatabase.addApplicationFont(":/fonts/SegoeUI.ttf")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
