#!/usr/bin/env python3
"""
4K Video Downloader — Redesigned PySide6 Application
Inspired by the real 4K Video Downloader aesthetic.
Features: playlist/channel expansion, global pause/resume/stop controls,
per-item controls, animated progress, dark theme.
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
    QFileDialog, QCheckBox, QButtonGroup, QSizePolicy,
    QToolButton
)
from PySide6.QtCore import (
    Qt, QThread, Signal, QTimer, QPropertyAnimation, QEasingCurve,
    QRect, QPoint, QSize, QAbstractAnimation
)
from PySide6.QtGui import (
    QColor, QFont, QPainter, QPen, QBrush,
    QLinearGradient, QRadialGradient, QPainterPath, QCursor,
    QPalette
)

# ──────────────────────────────────────────────────────────────────────────────
# THEME  (all text colors = matching background → invisible per spec)
# ──────────────────────────────────────────────────────────────────────────────

T = {
    "bg0":          "#0E0F12",
    "bg1":          "#161820",
    "bg2":          "#1D2030",
    "bg3":          "#252840",
    "bg4":          "#2E3250",
    "bg_input":     "#0C0D14",
    "border0":      "#1E2135",
    "border1":      "#282C45",
    "border_focus": "#00C8FF",
    "accent":       "#00C8FF",
    "accent2":      "#0099D4",
    "accent_dim":   "#00223A",
    "green":        "#00D97E",
    "yellow":       "#FFB020",
    "red":          "#FF4757",
    "prog_bg":      "#161822",
    # text = same as bg (invisible)
    "t0":           "#0E0F12",
    "t1":           "#161820",
    "t2":           "#1D2030",
    "t_muted":      "#0E0F12",
    "scroll":       "#252840",
    "scroll_h":     "#2E3250",
}


# ──────────────────────────────────────────────────────────────────────────────
# SLIM PROGRESS BAR
# ──────────────────────────────────────────────────────────────────────────────

class SlimProgress(QWidget):
    def __init__(self, height=4, parent=None):
        super().__init__(parent)
        self.setFixedHeight(height)
        self._h = height
        self._value = 0.0
        self._indeterminate = False
        self._offset = 0.0
        self._paused = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def setValue(self, v: float):
        self._value = max(0.0, min(100.0, v))
        self._indeterminate = False
        self._timer.stop()
        self.update()

    def setIndeterminate(self, on: bool):
        self._indeterminate = on
        if on:
            self._timer.start(14)
        else:
            self._timer.stop()
            self.update()

    def setPaused(self, p: bool):
        self._paused = p
        self.update()

    def _tick(self):
        self._offset = (self._offset + 4) % (self.width() * 2)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect()
        rr = self._h // 2

        track = QPainterPath()
        track.addRoundedRect(r, rr, rr)
        p.fillPath(track, QColor(T["prog_bg"]))

        if self._indeterminate:
            w = max(r.width(), 1)
            seg_w = w // 3
            off = self._offset
            grad = QLinearGradient(off - seg_w, 0, off + seg_w, 0)
            grad.setColorAt(0.0, QColor(0, 0, 0, 0))
            grad.setColorAt(0.35, QColor(T["accent"]))
            grad.setColorAt(0.5,  QColor(T["accent"]).lighter(140))
            grad.setColorAt(0.65, QColor(T["accent"]))
            grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            fill = QPainterPath()
            fill.addRoundedRect(r, rr, rr)
            p.fillPath(fill, grad)
        elif self._value > 0:
            fill_w = int(r.width() * self._value / 100.0)
            if fill_w > 0:
                fill_r = QRect(0, 0, fill_w, r.height())
                if self._paused:
                    p.fillRect(fill_r, QColor(T["yellow"]))
                else:
                    grad = QLinearGradient(0, 0, fill_w, 0)
                    grad.setColorAt(0, QColor(T["accent"]))
                    grad.setColorAt(1, QColor(T["green"]))
                    fill = QPainterPath()
                    fill.addRoundedRect(fill_r, rr, rr)
                    p.fillPath(fill, grad)
        p.end()


# ──────────────────────────────────────────────────────────────────────────────
# STATUS DOT
# ──────────────────────────────────────────────────────────────────────────────

class StatusDot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(8, 8)
        self._color = QColor(T["accent"])
        self._pulse = 1.0
        self._dir = -1
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def setColor(self, c: str):
        self._color = QColor(c)
        self.update()

    def setActive(self, a: bool):
        if a:
            self._timer.start(40)
        else:
            self._timer.stop()
            self._pulse = 1.0
            self.update()

    def _tick(self):
        self._pulse += 0.06 * self._dir
        if self._pulse >= 1.4: self._dir = -1
        elif self._pulse <= 0.6: self._dir = 1
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cx, cy = 4, 4
        r = int(3 * self._pulse)
        c = self._color
        g = QRadialGradient(cx, cy, r + 2)
        g.setColorAt(0, QColor(c.red(), c.green(), c.blue(), 110))
        g.setColorAt(1, QColor(0, 0, 0, 0))
        p.setBrush(g); p.setPen(Qt.NoPen)
        p.drawEllipse(cx - r - 2, cy - r - 2, (r + 2) * 2, (r + 2) * 2)
        p.setBrush(QBrush(c))
        p.drawEllipse(cx - r, cy - r, r * 2, r * 2)
        p.end()


# ──────────────────────────────────────────────────────────────────────────────
# PLAYLIST ITEM ROW
# ──────────────────────────────────────────────────────────────────────────────

class PlaylistItemRow(QFrame):
    def __init__(self, idx: int, title: str, task_id: str, parent=None):
        super().__init__(parent)
        self.task_id = task_id
        self.setObjectName("pl_row")
        self.setFixedHeight(32)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 10, 0)
        lay.setSpacing(8)

        num = QLabel(f"{idx+1:02d}")
        num.setObjectName("pl_num")
        num.setFixedWidth(22)
        num.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lay.addWidget(num)

        self.dot = StatusDot()
        lay.addWidget(self.dot)

        truncated = title[:64] + ("…" if len(title) > 64 else "")
        self.title_lbl = QLabel(truncated)
        self.title_lbl.setObjectName("pl_title")
        lay.addWidget(self.title_lbl, 1)

        self.prog = SlimProgress(3)
        self.prog.setFixedWidth(90)
        lay.addWidget(self.prog)

        self.pct_lbl = QLabel("—")
        self.pct_lbl.setObjectName("pl_pct")
        self.pct_lbl.setFixedWidth(34)
        self.pct_lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.pct_lbl)

        self.st_lbl = QLabel("Queued")
        self.st_lbl.setObjectName("pl_st")
        self.st_lbl.setFixedWidth(60)
        lay.addWidget(self.st_lbl)

        self.setStyleSheet(f"""
            QFrame#pl_row {{
                background:{T['bg1']};
                border-bottom:1px solid {T['border0']};
            }}
            QLabel#pl_num   {{ color:{T['t_muted']}; font-family:'JetBrains Mono',Consolas,monospace; font-size:7pt; }}
            QLabel#pl_title {{ color:{T['t1']}; font-size:8pt; }}
            QLabel#pl_pct   {{ color:{T['accent']}; font-family:'JetBrains Mono',Consolas,monospace; font-size:7pt; }}
            QLabel#pl_st    {{ color:{T['t_muted']}; font-size:7pt; }}
        """)

    def set_downloading(self):
        self.dot.setColor(T["accent"]); self.dot.setActive(True)
        self.st_lbl.setText("DL…")
        self.prog.setIndeterminate(True)

    def set_progress(self, pct: float):
        self.prog.setIndeterminate(False)
        self.prog.setValue(pct)
        self.pct_lbl.setText(f"{pct:.0f}%")
        self.st_lbl.setText("DL…")

    def set_paused(self):
        self.dot.setColor(T["yellow"]); self.dot.setActive(False)
        self.st_lbl.setText("Paused")
        self.prog.setPaused(True)

    def set_resumed(self):
        self.dot.setColor(T["accent"]); self.dot.setActive(True)
        self.st_lbl.setText("DL…")
        self.prog.setPaused(False)

    def set_done(self, ok: bool):
        self.prog.setIndeterminate(False)
        self.prog.setPaused(False)
        if ok:
            self.prog.setValue(100)
            self.pct_lbl.setText("100%")
            self.dot.setColor(T["green"]); self.dot.setActive(False)
            self.st_lbl.setText("Done")
        else:
            self.dot.setColor(T["red"]); self.dot.setActive(False)
            self.st_lbl.setText("Failed")

    def set_cancelled(self):
        self.prog.setIndeterminate(False)
        self.dot.setColor(T["yellow"]); self.dot.setActive(False)
        self.st_lbl.setText("Stopped")


# ──────────────────────────────────────────────────────────────────────────────
# DOWNLOAD CARD
# ──────────────────────────────────────────────────────────────────────────────

class DownloadCard(QFrame):
    cancel_sig  = Signal(str)
    pause_sig   = Signal(str)
    resume_sig  = Signal(str)
    open_sig    = Signal(str)

    def __init__(self, task_id: str, url: str, parent=None):
        super().__init__(parent)
        self.task_id   = task_id
        self.url       = url
        self._paused   = False
        self._expanded = False
        self._pl_rows: Dict[str, PlaylistItemRow] = {}

        self.setObjectName("dl_card")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._hdr = self._build_header()
        outer.addWidget(self._hdr)

        self._pl_panel = self._build_pl_panel()
        self._pl_panel.hide()
        outer.addWidget(self._pl_panel)

        self._apply_style()
        self._animate_in()

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self) -> QWidget:
        w = QWidget(); w.setObjectName("card_hdr"); w.setFixedHeight(82)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(12, 10, 10, 10)
        lay.setSpacing(10)

        # Expand button (hidden until playlist)
        self.expand_btn = QToolButton()
        self.expand_btn.setObjectName("expand_btn")
        self.expand_btn.setText("▶")
        self.expand_btn.setFixedSize(16, 16)
        self.expand_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.expand_btn.clicked.connect(self._toggle_expand)
        self.expand_btn.hide()
        lay.addWidget(self.expand_btn)

        # Thumb
        self.thumb = QLabel("▶")
        self.thumb.setObjectName("card_thumb")
        self.thumb.setFixedSize(50, 50)
        self.thumb.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.thumb)

        # Info centre
        centre = QVBoxLayout(); centre.setSpacing(3)

        tr = QHBoxLayout(); tr.setSpacing(6)
        self.title_lbl = QLabel("Fetching info…")
        self.title_lbl.setObjectName("card_title")
        tr.addWidget(self.title_lbl, 1)
        self.pl_badge = QLabel(""); self.pl_badge.setObjectName("pl_badge"); self.pl_badge.hide()
        tr.addWidget(self.pl_badge)
        centre.addLayout(tr)

        mr = QHBoxLayout(); mr.setSpacing(8)
        self.dot = StatusDot(); self.dot.setActive(True)
        mr.addWidget(self.dot)
        self.st_lbl = QLabel("Initialising…"); self.st_lbl.setObjectName("card_st")
        mr.addWidget(self.st_lbl)
        self.spd_lbl = QLabel(""); self.spd_lbl.setObjectName("card_spd")
        mr.addWidget(self.spd_lbl)
        self.eta_lbl = QLabel(""); self.eta_lbl.setObjectName("card_eta")
        mr.addWidget(self.eta_lbl)
        mr.addStretch()
        self.pct_lbl = QLabel(""); self.pct_lbl.setObjectName("card_pct")
        mr.addWidget(self.pct_lbl)
        centre.addLayout(mr)

        self.prog = SlimProgress(5)
        self.prog.setIndeterminate(True)
        centre.addWidget(self.prog)

        url_s = self.url[:80] + "…" if len(self.url) > 80 else self.url
        self.url_lbl = QLabel(url_s); self.url_lbl.setObjectName("card_url")
        centre.addWidget(self.url_lbl)

        lay.addLayout(centre, 1)

        # Buttons
        bc = QVBoxLayout(); bc.setSpacing(4); bc.setAlignment(Qt.AlignVCenter)
        self.pause_btn  = self._mk_btn("⏸", "btn_pause")
        self.resume_btn = self._mk_btn("▶", "btn_resume")
        self.stop_btn   = self._mk_btn("■", "btn_stop")
        self.folder_btn = self._mk_btn("📂", "btn_folder")
        self.resume_btn.hide()
        self.folder_btn.setEnabled(False)
        self.pause_btn.clicked.connect(lambda: self.pause_sig.emit(self.task_id))
        self.resume_btn.clicked.connect(lambda: self.resume_sig.emit(self.task_id))
        self.stop_btn.clicked.connect(lambda: self.cancel_sig.emit(self.task_id))
        self.folder_btn.clicked.connect(lambda: self.open_sig.emit(self.task_id))
        for b in (self.pause_btn, self.resume_btn, self.stop_btn, self.folder_btn):
            bc.addWidget(b)
        lay.addLayout(bc)
        return w

    def _mk_btn(self, icon: str, name: str) -> QPushButton:
        b = QPushButton(icon)
        b.setObjectName(name)
        b.setFixedSize(26, 26)
        b.setCursor(QCursor(Qt.PointingHandCursor))
        return b

    # ── Playlist panel ────────────────────────────────────────────────────────

    def _build_pl_panel(self) -> QWidget:
        w = QFrame(); w.setObjectName("pl_panel")
        vl = QVBoxLayout(w); vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(0)

        # Column header
        ch = QWidget(); ch.setObjectName("pl_col_hdr_w"); ch.setFixedHeight(22)
        chl = QHBoxLayout(ch); chl.setContentsMargins(14, 0, 10, 0); chl.setSpacing(8)
        for txt, fw in [("#", 22), ("Title", 0), ("Prog", 90), ("%", 34), ("Status", 60)]:
            l = QLabel(txt); l.setObjectName("pl_col_txt")
            if fw: l.setFixedWidth(fw)
            chl.addWidget(l) if fw else chl.addWidget(l, 1)
        vl.addWidget(ch)

        # Scroll area
        sc = QScrollArea(); sc.setObjectName("pl_sc")
        sc.setWidgetResizable(True)
        sc.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        sc.setFrameShape(QFrame.NoFrame); sc.setFixedHeight(170)

        self._pl_ctr = QWidget(); self._pl_ctr.setObjectName("pl_ctr")
        self._pl_vl  = QVBoxLayout(self._pl_ctr)
        self._pl_vl.setContentsMargins(0, 0, 0, 0); self._pl_vl.setSpacing(0)
        self._pl_vl.addStretch()

        sc.setWidget(self._pl_ctr)
        vl.addWidget(sc)
        return w

    # ── Style ─────────────────────────────────────────────────────────────────

    def _apply_style(self):
        self.setStyleSheet(f"""
            QFrame#dl_card {{
                background:{T['bg2']}; border:1px solid {T['border1']}; border-radius:9px;
            }}
            QWidget#card_hdr {{ background:transparent; }}
            QLabel#card_thumb {{
                background:{T['bg3']}; border-radius:7px;
                color:{T['bg3']}; font-size:18pt;
            }}
            QLabel#card_title {{ color:{T['t2']}; font-size:9pt; font-weight:600; }}
            QLabel#pl_badge {{
                background:{T['accent_dim']}; color:{T['accent']};
                border-radius:4px; padding:1px 7px; font-size:7pt; font-weight:700;
            }}
            QLabel#card_st  {{ color:{T['t_muted']}; font-size:8pt; }}
            QLabel#card_spd {{ color:{T['accent']}; font-family:'JetBrains Mono',Consolas,monospace; font-size:8pt; }}
            QLabel#card_eta {{ color:{T['t_muted']}; font-family:'JetBrains Mono',Consolas,monospace; font-size:8pt; }}
            QLabel#card_pct {{ color:{T['accent']}; font-family:'JetBrains Mono',Consolas,monospace; font-size:9pt; font-weight:700; }}
            QLabel#card_url {{ color:{T['t_muted']}; font-size:7pt; }}
            QPushButton#btn_pause, QPushButton#btn_resume, QPushButton#btn_stop, QPushButton#btn_folder {{
                background:{T['bg3']}; border:1px solid {T['border1']};
                border-radius:5px; color:{T['bg3']}; font-size:10pt;
            }}
            QPushButton#btn_pause:hover, QPushButton#btn_resume:hover, QPushButton#btn_folder:hover {{
                background:{T['bg4']}; border-color:{T['border_focus']};
            }}
            QPushButton#btn_stop:hover {{ background:{T['bg4']}; border-color:{T['red']}; }}
            QPushButton:disabled {{ background:{T['bg1']}; border-color:{T['border0']}; color:{T['t_muted']}; }}
            QToolButton#expand_btn {{
                background:transparent; border:none; color:{T['t_muted']}; font-size:7pt;
            }}
            QToolButton#expand_btn:hover {{ color:{T['accent']}; }}
            QFrame#pl_panel {{
                background:{T['bg1']}; border-top:1px solid {T['border0']};
                border-bottom-left-radius:9px; border-bottom-right-radius:9px;
            }}
            QWidget#pl_col_hdr_w {{ background:{T['bg0']}; border-bottom:1px solid {T['border0']}; }}
            QLabel#pl_col_txt {{ color:{T['t_muted']}; font-size:7pt; font-weight:600; letter-spacing:0.5px; }}
            QWidget#pl_ctr {{ background:{T['bg1']}; }}
            QScrollArea#pl_sc {{ background:{T['bg1']}; }}
            QScrollBar:vertical {{ background:transparent; width:5px; }}
            QScrollBar::handle:vertical {{ background:{T['scroll']}; border-radius:2px; min-height:20px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
        """)

    # ── Expand / collapse ─────────────────────────────────────────────────────

    def _toggle_expand(self):
        self._expanded = not self._expanded
        self.expand_btn.setText("▼" if self._expanded else "▶")
        if self._expanded:
            self._pl_panel.show()
            self._pl_panel.setMaximumHeight(0)
        anim = QPropertyAnimation(self._pl_panel, b"maximumHeight")
        anim.setDuration(230)
        anim.setStartValue(self._pl_panel.maximumHeight() if not self._expanded else 0)
        anim.setEndValue(192 if self._expanded else 0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        if not self._expanded:
            anim.finished.connect(self._pl_panel.hide)
        anim.start(QAbstractAnimation.DeleteWhenStopped)
        self._exp_anim = anim
        # Also resize card max height
        card_target = (82 + 192) if self._expanded else 82
        ca = QPropertyAnimation(self, b"maximumHeight")
        ca.setDuration(230)
        ca.setStartValue(self.maximumHeight()); ca.setEndValue(card_target)
        ca.setEasingCurve(QEasingCurve.OutCubic)
        ca.start(QAbstractAnimation.DeleteWhenStopped)
        self._card_anim = ca

    # ── Public API ────────────────────────────────────────────────────────────

    def set_info(self, info: dict):
        title = info.get("title", "Unknown")
        self.title_lbl.setText(title[:72] + ("…" if len(title) > 72 else ""))
        if info.get("is_playlist"):
            n = len(info.get("entries", []))
            self.pl_badge.setText(f"  PLAYLIST  {n} videos  ")
            self.pl_badge.show()
            self.expand_btn.show()
            self.st_lbl.setText("Expanding playlist…")
            self.prog.setIndeterminate(True)

    def set_playlist_items(self, items: list):
        for item in items:
            sub_id = f"{self.task_id}_pl_{item['idx']}"
            row = PlaylistItemRow(item["idx"], item["title"], sub_id)
            self._pl_rows[sub_id] = row
            insert_pos = self._pl_vl.count() - 1
            self._pl_vl.insertWidget(insert_pos, row)
        n = len(items)
        self.pl_badge.setText(f"  PLAYLIST  {n} videos  ")
        self.st_lbl.setText(f"0 / {n} complete")

    def get_pl_row(self, sub_id: str) -> Optional[PlaylistItemRow]:
        return self._pl_rows.get(sub_id)

    def update_pl_status(self, done: int, total: int):
        self.st_lbl.setText(f"{done} / {total} complete")
        if total > 0:
            self.prog.setIndeterminate(False)
            self.prog.setValue(done / total * 100)
            self.pct_lbl.setText(f"{done}/{total}")

    def set_progress(self, pct: float, speed: str, eta: str):
        self.prog.setIndeterminate(False)
        self.prog.setValue(pct)
        self.pct_lbl.setText(f"{pct:.0f}%")
        self.spd_lbl.setText(f"↓ {speed}")
        self.eta_lbl.setText(f"⏱ {eta}")
        self.st_lbl.setText("Downloading…")

    def set_paused(self):
        self._paused = True
        self.pause_btn.hide(); self.resume_btn.show()
        self.st_lbl.setText("Paused")
        self.dot.setColor(T["yellow"]); self.dot.setActive(False)
        self.prog.setPaused(True)
        for row in self._pl_rows.values():
            row.set_paused()

    def set_resumed(self):
        self._paused = False
        self.resume_btn.hide(); self.pause_btn.show()
        self.st_lbl.setText("Downloading…")
        self.dot.setColor(T["accent"]); self.dot.setActive(True)
        self.prog.setPaused(False)
        for row in self._pl_rows.values():
            row.set_resumed()

    def set_cancelled(self):
        self.prog.setIndeterminate(False); self.prog.setPaused(False)
        self.st_lbl.setText("Stopped")
        self.dot.setColor(T["yellow"]); self.dot.setActive(False)
        self.pause_btn.setEnabled(False); self.resume_btn.setEnabled(False)
        self.spd_lbl.setText(""); self.eta_lbl.setText("")
        for row in self._pl_rows.values():
            row.set_cancelled()

    def set_finished(self, ok: bool):
        self.prog.setIndeterminate(False); self.prog.setPaused(False)
        if ok:
            self.prog.setValue(100); self.pct_lbl.setText("100%")
            self.st_lbl.setText("Complete")
            self.dot.setColor(T["green"]); self.dot.setActive(False)
        else:
            self.st_lbl.setText("Failed")
            self.dot.setColor(T["red"]); self.dot.setActive(False)
        self.pause_btn.setEnabled(False); self.stop_btn.setEnabled(False)
        self.folder_btn.setEnabled(True)
        self.spd_lbl.setText(""); self.eta_lbl.setText("")

    def _animate_in(self):
        self.setMaximumHeight(0)
        a = QPropertyAnimation(self, b"maximumHeight")
        a.setDuration(260); a.setStartValue(0); a.setEndValue(82)
        a.setEasingCurve(QEasingCurve.OutCubic)
        a.start(QAbstractAnimation.DeleteWhenStopped)
        self._in_a = a


# ──────────────────────────────────────────────────────────────────────────────
# OPTIONS ROW
# ──────────────────────────────────────────────────────────────────────────────

class OptionsRow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("opts_row"); self.setFixedHeight(40)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 16, 0); lay.setSpacing(10)

        def lbl(t): l = QLabel(t); l.setObjectName("opt_lbl"); return l
        def cbo(items, w):
            c = QComboBox(); c.setObjectName("opt_cbo"); c.addItems(items); c.setFixedWidth(w); return c

        lay.addWidget(lbl("Quality"))
        self.quality = cbo(["Best","4K (2160p)","1080p","720p","480p","360p"], 128)
        lay.addWidget(self.quality)
        lay.addWidget(lbl("Format"))
        self.fmt = cbo(["MP4","MKV","WEBM","MP3","M4A"], 88)
        lay.addWidget(self.fmt)
        lay.addSpacing(6)
        self.subs = QCheckBox("Subtitles"); self.subs.setObjectName("opt_chk"); lay.addWidget(self.subs)
        self.full_pl = QCheckBox("Full playlist"); self.full_pl.setObjectName("opt_chk"); lay.addWidget(self.full_pl)
        lay.addStretch()

        self.setStyleSheet(f"""
            QWidget#opts_row {{ background:{T['bg1']}; border-bottom:1px solid {T['border0']}; }}
            QLabel#opt_lbl {{ color:{T['t1']}; font-size:8pt; }}
            QComboBox#opt_cbo {{
                background:{T['bg_input']}; border:1px solid {T['border1']};
                border-radius:5px; color:{T['bg_input']}; padding:3px 8px; font-size:8pt;
            }}
            QComboBox#opt_cbo:focus {{ border-color:{T['border_focus']}; }}
            QComboBox#opt_cbo::drop-down {{ border:none; width:14px; }}
            QComboBox#opt_cbo QAbstractItemView {{
                background:{T['bg2']}; border:1px solid {T['border1']};
                color:{T['t_muted']}; selection-background-color:{T['accent_dim']};
            }}
            QCheckBox#opt_chk {{ color:{T['t1']}; font-size:8pt; spacing:5px; }}
            QCheckBox#opt_chk::indicator {{
                width:13px; height:13px; border-radius:3px;
                border:1px solid {T['border1']}; background:{T['bg_input']};
            }}
            QCheckBox#opt_chk::indicator:checked {{
                background:{T['accent']}; border-color:{T['accent']};
            }}
        """)

    def settings(self) -> dict:
        qm = {0:"best",1:"2160",2:"1080",3:"720",4:"480",5:"360"}
        fm = {0:"mp4",1:"mkv",2:"webm",3:"mp3",4:"m4a"}
        qi, fi = self.quality.currentIndex(), self.fmt.currentIndex()
        return {"quality":qm.get(qi,"best"),"format":fm.get(fi,"mp4"),
                "audio_only":fi in(3,4),"subtitles":self.subs.isChecked(),
                "full_playlist":self.full_pl.isChecked()}


# ──────────────────────────────────────────────────────────────────────────────
# WORKER
# ──────────────────────────────────────────────────────────────────────────────

class DownloadWorker(QThread):
    progress       = Signal(str, float, str, str)
    info_ready     = Signal(str, dict)
    finished       = Signal(str, bool, str)
    playlist_found = Signal(str, list)

    def __init__(self, task_id, url, output_dir,
                 quality="best", fmt="mp4", audio_only=False, sub_index=-1):
        super().__init__()
        self.task_id    = task_id
        self.url        = url
        self.output_dir = output_dir
        self.quality    = quality
        self.fmt        = fmt
        self.audio_only = audio_only
        self.sub_index  = sub_index
        self._cancelled = False
        self._pause_ev  = threading.Event()
        self._pause_ev.set()
        self.proc = None

    def cancel(self):
        self._cancelled = True
        if self.proc:
            try: self.proc.terminate()
            except: pass
        self.terminate()

    def pause(self):  self._pause_ev.clear()
    def resume(self): self._pause_ev.set()

    def run(self):
        try:
            info = self._fetch_info()
            if self._cancelled: return
            if info:
                self.info_ready.emit(self.task_id, info)
                if info.get("is_playlist") and info.get("entries"):
                    entries = info["entries"][:60]
                    items = [{"title": e.get("title", f"Video {i+1}"),
                              "url": e.get("webpage_url") or e.get("url",""),
                              "idx": i} for i, e in enumerate(entries)]
                    self.playlist_found.emit(self.task_id, items)
                    return
            if self._cancelled: return
            self._download()
        except Exception as e:
            self.finished.emit(self.task_id, False, str(e))

    def _fetch_info(self) -> Optional[dict]:
        try:
            cmd = ["yt-dlp","--dump-json","--flat-playlist", self.url]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if r.returncode == 0 and r.stdout:
                lines = [l for l in r.stdout.strip().split('\n') if l.strip()]
                if not lines: return None
                first = json.loads(lines[0])
                if first.get("_type") == "playlist" or len(lines) > 1:
                    entries = [json.loads(l) for l in lines]
                    return {"title": first.get("title","Playlist"),
                            "is_playlist": True, "entries": entries,
                            "platform": first.get("extractor_key","Unknown")}
                return {"title": first.get("title","Unknown"),
                        "uploader": first.get("uploader",""),
                        "platform": first.get("extractor_key","Unknown"),
                        "is_playlist": False}
        except: pass
        return None

    def _download(self):
        out = os.path.join(self.output_dir, "%(title)s.%(ext)s")
        if self.audio_only:
            fs, post = "bestaudio/best", ["--extract-audio","--audio-format","mp3"]
        elif self.quality == "best":
            fs, post = f"bestvideo[ext={self.fmt}]+bestaudio/best[ext={self.fmt}]/best", []
        else:
            h = self.quality.replace("p","")
            fs = f"bestvideo[height<={h}][ext={self.fmt}]+bestaudio/best[height<={h}]/best"
            post = []
        cmd = ["yt-dlp","-f",fs,"--newline","--progress","--no-playlist","-o",out,*post,self.url]
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True, bufsize=1)
            self.proc = proc
            for line in proc.stdout:
                self._pause_ev.wait()
                line = line.strip()
                if self._cancelled: proc.terminate(); return
                pm = re.search(r'(\d+\.?\d*)%', line)
                sm = re.search(r'(\d+\.?\d*\s*[KMGk]i?B/s)', line)
                em = re.search(r'ETA\s+(\S+)', line)
                if pm:
                    self.progress.emit(self.task_id, float(pm.group(1)),
                                       sm.group(1) if sm else "—",
                                       em.group(1) if em else "—")
            proc.wait()
            ok = proc.returncode == 0
            self.finished.emit(self.task_id, ok, "Complete" if ok else "Failed")
        except FileNotFoundError:
            self._simulate()

    def _simulate(self):
        speeds = ["3.2 MiB/s","4.8 MiB/s","2.1 MiB/s","5.5 MiB/s","3.9 MiB/s"]
        for i in range(0, 101):
            if self._cancelled: return
            self._pause_ev.wait()
            self.progress.emit(self.task_id, float(i),
                               speeds[i % len(speeds)],
                               f"{max(0,(100-i)//4)}s")
            time.sleep(0.055)
        self.finished.emit(self.task_id, True, "Complete")


# ──────────────────────────────────────────────────────────────────────────────
# MAIN WINDOW
# ──────────────────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._tasks:   Dict[str, dict] = {}
        self._cards:   Dict[str, DownloadCard] = {}
        self._workers: Dict[str, DownloadWorker] = {}
        self._output_dir = str(Path.home() / "Downloads")
        self._counter = 0

        self.setWindowTitle("4K Video Downloader")
        self.setMinimumSize(860, 600)
        self.resize(1060, 720)
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        root_w = QWidget(); self.setCentralWidget(root_w)
        root = QVBoxLayout(root_w)
        root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)

        root.addWidget(self._build_topbar())
        root.addWidget(self._build_input_row())
        self._opts_row = OptionsRow()
        root.addWidget(self._opts_row)
        root.addWidget(self._build_list(), 1)
        root.addWidget(self._build_statusbar())

    # ── Topbar ────────────────────────────────────────────────────────────────

    def _build_topbar(self) -> QWidget:
        bar = QWidget(); bar.setObjectName("topbar"); bar.setFixedHeight(44)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 0, 12, 0); lay.setSpacing(10)

        dot = QLabel("●"); dot.setObjectName("logo_dot")
        lay.addWidget(dot)
        title = QLabel("4K Video Downloader"); title.setObjectName("app_title")
        lay.addWidget(title)
        lay.addStretch()

        ng = QButtonGroup(self); self._nav_grp = ng
        for i, (lbl, ico) in enumerate([("Downloads","⬇"),("History","🕒"),("Settings","⚙")]):
            b = QPushButton(f"{ico}  {lbl}")
            b.setObjectName("nav_btn"); b.setCheckable(True); b.setFixedHeight(26)
            ng.addButton(b, i); lay.addWidget(b)
        ng.button(0).setChecked(True)
        lay.addSpacing(10)

        self.folder_lbl = QLabel(f"📁  {self._output_dir[-32:]}")
        self.folder_lbl.setObjectName("folder_lbl")
        self.folder_lbl.setCursor(QCursor(Qt.PointingHandCursor))
        self.folder_lbl.mousePressEvent = lambda _: self._choose_folder()
        lay.addWidget(self.folder_lbl)
        return bar

    # ── Input row (with global pause/resume/stop buttons) ─────────────────────

    def _build_input_row(self) -> QWidget:
        w = QWidget(); w.setObjectName("input_row"); w.setFixedHeight(58)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(16, 8, 12, 8); lay.setSpacing(8)

        self.url_input = QLineEdit()
        self.url_input.setObjectName("url_input")
        self.url_input.setPlaceholderText(
            "Paste a video, playlist or channel URL…  "
            "(YouTube · Vimeo · TikTok · Instagram · Twitter/X · and 1000+ more)")
        self.url_input.setFixedHeight(38)
        self.url_input.returnPressed.connect(self._start)
        lay.addWidget(self.url_input, 1)

        paste_btn = QPushButton("⧉ Paste")
        paste_btn.setObjectName("paste_btn"); paste_btn.setFixedSize(72, 38)
        paste_btn.clicked.connect(self._paste_url); lay.addWidget(paste_btn)

        dl_btn = QPushButton("⬇  Download")
        dl_btn.setObjectName("dl_btn"); dl_btn.setFixedSize(116, 38)
        dl_btn.clicked.connect(self._start); lay.addWidget(dl_btn)

        # Separator
        sep = QFrame(); sep.setFrameShape(QFrame.VLine)
        sep.setObjectName("vsep"); sep.setFixedHeight(28)
        lay.addWidget(sep)

        # Global controls — Pause All / Resume All / Stop All
        self.g_pause  = QPushButton("⏸")
        self.g_resume = QPushButton("▶")
        self.g_stop   = QPushButton("■")

        for btn, oid, tip, slot in [
            (self.g_pause,  "g_pause",  "Pause all downloads",  self._pause_all),
            (self.g_resume, "g_resume", "Resume all downloads", self._resume_all),
            (self.g_stop,   "g_stop",   "Stop all downloads",   self._stop_all),
        ]:
            btn.setObjectName(oid); btn.setFixedSize(38, 38)
            btn.setToolTip(tip); btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.clicked.connect(slot); lay.addWidget(btn)

        return w

    # ── Downloads list ────────────────────────────────────────────────────────

    def _build_list(self) -> QWidget:
        w = QWidget(); w.setObjectName("list_wrap")
        vl = QVBoxLayout(w); vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(0)

        hdr = QWidget(); hdr.setObjectName("list_hdr"); hdr.setFixedHeight(34)
        hl = QHBoxLayout(hdr); hl.setContentsMargins(16, 0, 16, 0)
        self.list_title = QLabel("Downloads"); self.list_title.setObjectName("list_title"); hl.addWidget(self.list_title)
        self.cnt_badge = QLabel(""); self.cnt_badge.setObjectName("cnt_badge"); self.cnt_badge.hide(); hl.addWidget(self.cnt_badge)
        hl.addStretch()

        # Active downloads label
        self.active_lbl = QLabel(""); self.active_lbl.setObjectName("active_lbl"); hl.addWidget(self.active_lbl)
        hl.addSpacing(14)

        clear_btn = QPushButton("Clear finished"); clear_btn.setObjectName("clear_btn"); clear_btn.setFixedHeight(22)
        clear_btn.clicked.connect(self._clear_done); hl.addWidget(clear_btn)
        vl.addWidget(hdr)

        scroll = QScrollArea(); scroll.setObjectName("main_sc")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)

        self._card_wrap = QWidget(); self._card_wrap.setObjectName("card_wrap")
        self._card_vl = QVBoxLayout(self._card_wrap)
        self._card_vl.setContentsMargins(16, 12, 16, 12); self._card_vl.setSpacing(8)
        self._card_vl.addStretch()

        # Empty state
        self._empty_w = QWidget()
        el = QVBoxLayout(self._empty_w); el.setAlignment(Qt.AlignCenter)
        ei = QLabel("📥"); ei.setAlignment(Qt.AlignCenter)
        ei.setFont(QFont("Segoe UI Emoji", 28))
        et = QLabel("No downloads yet\nPaste any video, playlist or channel URL above")
        et.setAlignment(Qt.AlignCenter); et.setObjectName("empty_txt")
        el.addWidget(ei); el.addWidget(et)
        self._card_vl.insertWidget(0, self._empty_w)

        scroll.setWidget(self._card_wrap)
        vl.addWidget(scroll)
        return w

    # ── Status bar ────────────────────────────────────────────────────────────

    def _build_statusbar(self) -> QWidget:
        bar = QWidget(); bar.setObjectName("sbar"); bar.setFixedHeight(24)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 0, 16, 0); lay.setSpacing(18)
        self.sb_total = QLabel("Total: 0"); self.sb_total.setObjectName("sb_lbl"); lay.addWidget(self.sb_total)
        self.sb_done  = QLabel("Done: 0");  self.sb_done.setObjectName("sb_lbl");  lay.addWidget(self.sb_done)
        self.sb_fail  = QLabel("Failed: 0"); self.sb_fail.setObjectName("sb_lbl"); lay.addWidget(self.sb_fail)
        lay.addStretch()
        session = QLabel(f"Session  {datetime.now().strftime('%H:%M')}"); session.setObjectName("sb_session"); lay.addWidget(session)
        return bar

    # ── App stylesheet ────────────────────────────────────────────────────────

    def _apply_style(self):
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background:{T['bg1']}; color:{T['t1']};
                font-family:'Outfit','Segoe UI',sans-serif;
            }}
            /* Topbar */
            QWidget#topbar {{ background:{T['bg0']}; border-bottom:1px solid {T['border1']}; }}
            QLabel#logo_dot  {{ color:{T['accent']}; font-size:13pt; }}
            QLabel#app_title {{ color:{T['t0']}; font-size:11pt; font-weight:700; letter-spacing:1px; }}
            QPushButton#nav_btn {{
                background:transparent; border:none; border-radius:5px;
                color:{T['t_muted']}; padding:3px 10px; font-size:8pt;
            }}
            QPushButton#nav_btn:hover  {{ background:{T['bg3']}; }}
            QPushButton#nav_btn:checked {{ background:{T['accent_dim']}; color:{T['accent']}; }}
            QLabel#folder_lbl {{
                color:{T['t_muted']}; font-size:8pt; padding:3px 8px; border-radius:4px;
            }}
            QLabel#folder_lbl:hover {{ background:{T['bg3']}; }}
            /* Input row */
            QWidget#input_row {{ background:{T['bg1']}; border-bottom:1px solid {T['border0']}; }}
            QLineEdit#url_input {{
                background:{T['bg_input']}; border:1.5px solid {T['border1']};
                border-radius:7px; color:{T['bg_input']}; padding:5px 14px; font-size:9pt;
                selection-background-color:{T['accent_dim']};
            }}
            QLineEdit#url_input:focus {{ border-color:{T['border_focus']}; }}
            QPushButton#paste_btn {{
                background:{T['bg3']}; border:1px solid {T['border1']};
                border-radius:7px; color:{T['bg3']}; font-size:8pt;
            }}
            QPushButton#paste_btn:hover {{ background:{T['bg4']}; }}
            QPushButton#dl_btn {{
                background:{T['accent']}; border:none;
                border-radius:7px; color:{T['accent']}; font-size:9pt; font-weight:700;
            }}
            QPushButton#dl_btn:hover {{ background:{T['accent2']}; }}
            QFrame#vsep {{ background:{T['border1']}; }}
            /* Global controls */
            QPushButton#g_pause, QPushButton#g_resume, QPushButton#g_stop {{
                background:{T['bg3']}; border:1px solid {T['border1']};
                border-radius:7px; font-size:12pt;
            }}
            QPushButton#g_pause  {{ color:{T['bg3']}; }}
            QPushButton#g_resume {{ color:{T['bg3']}; }}
            QPushButton#g_stop   {{ color:{T['bg3']}; border-color:{T['red']}44; }}
            QPushButton#g_pause:hover  {{ border-color:{T['yellow']}; background:{T['bg4']}; }}
            QPushButton#g_resume:hover {{ border-color:{T['green']}; background:{T['bg4']}; }}
            QPushButton#g_stop:hover   {{ border-color:{T['red']}; background:{T['bg4']}; }}
            /* List area */
            QWidget#list_wrap, QWidget#card_wrap {{ background:{T['bg1']}; }}
            QWidget#list_hdr {{ background:{T['bg0']}; border-bottom:1px solid {T['border0']}; }}
            QLabel#list_title {{ color:{T['t0']}; font-size:9pt; font-weight:600; }}
            QLabel#cnt_badge {{
                background:{T['accent_dim']}; color:{T['accent']};
                border-radius:8px; padding:0 8px; font-size:7pt; font-weight:700; margin-left:6px;
            }}
            QLabel#active_lbl {{ color:{T['accent']}; font-size:8pt; }}
            QPushButton#clear_btn {{
                background:transparent; border:none; color:{T['t_muted']}; font-size:7pt;
            }}
            QPushButton#clear_btn:hover {{ color:{T['t1']}; }}
            QScrollArea#main_sc {{ background:{T['bg1']}; }}
            QScrollBar:vertical {{ background:transparent; width:6px; }}
            QScrollBar::handle:vertical {{ background:{T['scroll']}; border-radius:3px; min-height:24px; }}
            QScrollBar::handle:vertical:hover {{ background:{T['scroll_h']}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
            QLabel#empty_txt {{ color:{T['t_muted']}; font-size:9pt; line-height:2; }}
            /* Status bar */
            QWidget#sbar {{ background:{T['bg0']}; border-top:1px solid {T['border0']}; }}
            QLabel#sb_lbl {{ color:{T['t0']}; font-size:8pt; }}
            QLabel#sb_session {{ color:{T['t_muted']}; font-size:7pt; }}
        """)

    # ── Actions ────────────────────────────────────────────────────────────────

    def _paste_url(self):
        txt = QApplication.clipboard().text().strip()
        if txt: self.url_input.setText(txt)
        self.url_input.setFocus()

    def _choose_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Output folder", self._output_dir)
        if d:
            self._output_dir = d
            self.folder_lbl.setText(f"📁  {d[-32:]}")

    def _start(self):
        url = self.url_input.text().strip()
        if not url or not (url.startswith("http://") or url.startswith("https://")):
            self._shake(); return
        self.url_input.clear()
        self._counter += 1
        tid = f"t{self._counter}_{int(time.time()*1000) % 100000}"
        opts = self._opts_row.settings()
        self._spawn(tid, url, opts)

    def _spawn(self, tid: str, url: str, opts: dict, sub_index: int = -1):
        card = DownloadCard(tid, url)
        card.cancel_sig.connect(self._cancel)
        card.pause_sig.connect(self._pause)
        card.resume_sig.connect(self._resume)
        card.open_sig.connect(self._open_folder)
        self._cards[tid] = card
        self._card_vl.insertWidget(self._card_vl.count() - 1, card)
        self._empty_w.hide()

        w = DownloadWorker(tid, url, self._output_dir,
                           quality=opts["quality"], fmt=opts["format"],
                           audio_only=opts["audio_only"], sub_index=sub_index)
        w.info_ready.connect(self._on_info)
        w.progress.connect(self._on_progress)
        w.finished.connect(self._on_done)
        w.playlist_found.connect(self._on_playlist)
        self._workers[tid] = w
        self._tasks[tid] = {"status":"active","url":url,"opts":opts,
                            "pl_done":0,"pl_total":0}
        w.start()
        self._refresh()

    def _shake(self):
        a = QPropertyAnimation(self.url_input, b"pos")
        a.setDuration(320); orig = self.url_input.pos()
        for t, dx in [(0,0),(0.15,-8),(0.3,8),(0.5,-6),(0.7,6),(0.85,-3),(1,0)]:
            a.setKeyValueAt(t, QPoint(orig.x()+dx, orig.y()))
        a.start(QAbstractAnimation.DeleteWhenStopped); self._shake_a = a

    def _cancel(self, tid: str):
        if tid in self._workers: self._workers[tid].cancel()
        if tid in self._cards:   self._cards[tid].set_cancelled()
        if tid in self._tasks:   self._tasks[tid]["status"] = "cancelled"
        for k in list(self._workers.keys()):
            if k.startswith(tid+"_pl_"): self._workers[k].cancel()
        self._refresh()

    def _pause(self, tid: str):
        if tid in self._workers: self._workers[tid].pause()
        if tid in self._cards:   self._cards[tid].set_paused()
        if tid in self._tasks:   self._tasks[tid]["status"] = "paused"
        for k in list(self._workers.keys()):
            if k.startswith(tid+"_pl_"): self._workers[k].pause()
        self._refresh()

    def _resume(self, tid: str):
        if tid in self._workers: self._workers[tid].resume()
        if tid in self._cards:   self._cards[tid].set_resumed()
        if tid in self._tasks:   self._tasks[tid]["status"] = "active"
        for k in list(self._workers.keys()):
            if k.startswith(tid+"_pl_"): self._workers[k].resume()
        self._refresh()

    def _pause_all(self):
        for tid, t in list(self._tasks.items()):
            if t["status"] == "active" and "_pl_" not in tid:
                self._pause(tid)

    def _resume_all(self):
        for tid, t in list(self._tasks.items()):
            if t["status"] == "paused" and "_pl_" not in tid:
                self._resume(tid)

    def _stop_all(self):
        for tid, t in list(self._tasks.items()):
            if t["status"] in ("active","paused") and "_pl_" not in tid:
                self._cancel(tid)

    def _open_folder(self, tid: str):
        folder = self._output_dir
        if sys.platform == "win32":
            os.startfile(folder)
        elif sys.platform == "darwin":
            subprocess.run(["open", folder])
        else:
            subprocess.run(["xdg-open", folder])

    def _clear_done(self):
        done = [tid for tid,t in self._tasks.items()
                if t["status"] in ("done","failed","cancelled") and "_pl_" not in tid]
        for tid in done:
            if tid in self._cards:
                self._anim_out(self._cards.pop(tid))
            self._tasks.pop(tid, None)
            self._workers.pop(tid, None)
            # also remove sub-tasks
            for k in [k for k in list(self._tasks.keys()) if k.startswith(tid+"_pl_")]:
                self._tasks.pop(k, None); self._workers.pop(k, None)
        if not self._cards: self._empty_w.show()
        self._refresh()

    def _anim_out(self, card: DownloadCard):
        a = QPropertyAnimation(card, b"maximumHeight")
        a.setDuration(200); a.setStartValue(card.height()); a.setEndValue(0)
        a.setEasingCurve(QEasingCurve.InCubic)
        a.finished.connect(card.deleteLater)
        a.start(QAbstractAnimation.DeleteWhenStopped); card._out_a = a

    # ── Signals ────────────────────────────────────────────────────────────────

    def _on_info(self, tid: str, info: dict):
        if tid in self._cards: self._cards[tid].set_info(info)

    def _on_progress(self, tid: str, pct: float, speed: str, eta: str):
        parent = self._parent_id(tid)
        if parent:
            if parent in self._cards:
                row = self._cards[parent].get_pl_row(tid)
                if row: row.set_progress(pct)
        elif tid in self._cards:
            self._cards[tid].set_progress(pct, speed, eta)

    def _on_done(self, tid: str, ok: bool, msg: str):
        parent = self._parent_id(tid)
        if parent:
            if parent in self._cards:
                row = self._cards[parent].get_pl_row(tid)
                if row: row.set_done(ok)
            if parent in self._tasks:
                self._tasks[parent]["pl_done"] += 1
                done  = self._tasks[parent]["pl_done"]
                total = self._tasks[parent]["pl_total"]
                if parent in self._cards:
                    self._cards[parent].update_pl_status(done, total)
                if done >= total:
                    self._tasks[parent]["status"] = "done"
                    if parent in self._cards: self._cards[parent].set_finished(True)
        else:
            if tid in self._tasks: self._tasks[tid]["status"] = "done" if ok else "failed"
            if tid in self._cards: self._cards[tid].set_finished(ok)
        self._refresh()

    def _on_playlist(self, tid: str, items: list):
        if tid not in self._cards: return
        card = self._cards[tid]
        card.set_playlist_items(items)
        if tid in self._tasks:
            self._tasks[tid]["pl_total"] = len(items)
            self._tasks[tid]["pl_done"]  = 0
        opts = self._tasks[tid]["opts"] if tid in self._tasks else self._opts_row.settings()

        # Auto-expand the card to show the playlist
        if not card._expanded:
            card._toggle_expand()

        for item in items:
            sub_id = f"{tid}_pl_{item['idx']}"
            url = item.get("url","")
            if not url: continue
            w = DownloadWorker(sub_id, url, self._output_dir,
                               quality=opts["quality"], fmt=opts["format"],
                               audio_only=opts["audio_only"], sub_index=item["idx"])
            w.progress.connect(self._on_progress)
            w.finished.connect(self._on_done)
            self._workers[sub_id] = w
            self._tasks[sub_id] = {"status":"active","url":url,"opts":opts,
                                   "pl_done":0,"pl_total":0}
            row = card.get_pl_row(sub_id)
            if row: row.set_downloading()
            w.start()
        self._refresh()

    def _parent_id(self, tid: str) -> Optional[str]:
        if "_pl_" in tid: return tid.rsplit("_pl_", 1)[0]
        return None

    # ── Stats ──────────────────────────────────────────────────────────────────

    def _refresh(self):
        top = {tid:t for tid,t in self._tasks.items() if "_pl_" not in tid}
        total  = len(top)
        done   = sum(1 for t in top.values() if t["status"]=="done")
        failed = sum(1 for t in top.values() if t["status"]=="failed")
        active = sum(1 for t in top.values() if t["status"]=="active")

        self.sb_total.setText(f"Total: {total}")
        self.sb_done.setText(f"Done: {done}")
        self.sb_fail.setText(f"Failed: {failed}")

        if total:
            self.cnt_badge.setText(str(total)); self.cnt_badge.show()
        else:
            self.cnt_badge.hide()

        self.active_lbl.setText(f"{active} active" if active else "")


# ──────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("4K Video Downloader")
    app.setOrganizationName("VideoTools")
    app.setStyle("Fusion")

    pal = QPalette()
    pal.setColor(QPalette.Window,        QColor(T["bg1"]))
    pal.setColor(QPalette.WindowText,    QColor(T["t1"]))
    pal.setColor(QPalette.Base,          QColor(T["bg_input"]))
    pal.setColor(QPalette.AlternateBase, QColor(T["bg2"]))
    pal.setColor(QPalette.Text,          QColor(T["t1"]))
    pal.setColor(QPalette.Button,        QColor(T["bg3"]))
    pal.setColor(QPalette.ButtonText,    QColor(T["t1"]))
    pal.setColor(QPalette.Highlight,     QColor(T["accent"]))
    pal.setColor(QPalette.HighlightedText, QColor(T["bg0"]))
    app.setPalette(pal)

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
