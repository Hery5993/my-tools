"""
Snip Pro — modernized snipping tool
Zoom fix: override wheelEvent() directly on QScrollArea subclass.
The eventFilter-on-viewport approach FAILS because QScrollArea.wheelEvent()
is called in parallel and consumes/conflicts with the event.
"""

import sys
import os
import mss
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QLabel, QTextEdit, QToolBar,
    QComboBox, QStatusBar, QFileDialog,
    QSplitter, QScrollArea, QVBoxLayout,
    QHBoxLayout, QSlider, QPushButton,
    QSizePolicy, QButtonGroup, QMenu,
    QDialog, QDialogButtonBox, QSpinBox,
    QFormLayout, QCheckBox, QTabWidget,
    QListWidget, QListWidgetItem, QFrame
)
from PyQt6.QtGui import (
    QAction, QIcon, QPixmap, QImage,
    QColor, QPen, QPainter,
    QGuiApplication, QWheelEvent,
    QFont, QKeySequence, QShortcut,
    QTransform
)
from PyQt6.QtCore import (
    Qt, QRect, QEvent, QSize, QPoint,
    QTimer, QBuffer, QByteArray, pyqtSignal
)


# ─────────────────────────────────────────
# THEME
# ─────────────────────────────────────────
DARK_BG      = "#16181D"
PANEL_BG     = "#1E2028"
TOOLBAR_BG   = "#13151A"
BORDER       = "#2A2D38"
ACCENT       = "#4F8EF7"
TEXT         = "#E8EAF0"
TEXT_MUTED   = "#6B7080"
SUCCESS      = "#3DD68C"
SURFACE      = "#252830"
DANGER       = "#E05C5C"

STYLE = f"""
QMainWindow, QWidget {{
    background: {DARK_BG};
    color: {TEXT};
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}}
QToolBar {{
    background: {TOOLBAR_BG};
    border-bottom: 1px solid {BORDER};
    padding: 5px 8px;
    spacing: 2px;
}}
QToolBar QToolButton {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    color: {TEXT};
    padding: 5px 11px;
    font-size: 12px;
}}
QToolBar QToolButton:hover {{
    background: {SURFACE};
    border-color: {BORDER};
}}
QToolBar QToolButton:pressed, QToolBar QToolButton:checked {{
    background: {ACCENT};
    color: #fff;
    border-color: {ACCENT};
}}
QComboBox {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 6px;
    color: {TEXT};
    padding: 4px 10px;
    min-width: 110px;
}}
QComboBox QAbstractItemView {{
    background: {PANEL_BG};
    border: 1px solid {BORDER};
    color: {TEXT};
    selection-background-color: {ACCENT};
}}
QComboBox::drop-down {{ border: none; width: 18px; }}
QTextEdit {{
    background: {PANEL_BG};
    border: none;
    color: {TEXT};
    font-family: "JetBrains Mono", "Consolas", monospace;
    font-size: 12px;
    padding: 10px;
    selection-background-color: {ACCENT};
}}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{
    background: {DARK_BG}; width: 7px; border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER}; border-radius: 3px; min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{ background: {TEXT_MUTED}; }}
QScrollBar:horizontal {{
    background: {DARK_BG}; height: 7px; border-radius: 3px;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER}; border-radius: 3px;
}}
QScrollBar::add-line, QScrollBar::sub-line {{ width:0; height:0; }}
QSplitter::handle {{ background: {BORDER}; }}
QStatusBar {{
    background: {TOOLBAR_BG};
    border-top: 1px solid {BORDER};
    color: {TEXT_MUTED};
    font-size: 11px;
    padding: 3px 10px;
}}
QSlider::groove:horizontal {{
    background: {BORDER}; height: 4px; border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {ACCENT}; width: 14px; height: 14px;
    margin: -5px 0; border-radius: 7px;
}}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 2px; }}
QPushButton {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 6px;
    color: {TEXT};
    padding: 5px 14px;
}}
QPushButton:hover {{ background: {ACCENT}; border-color: {ACCENT}; color: #fff; }}
QPushButton:pressed {{ background: #3a72d4; }}
QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: 4px;
    background: {PANEL_BG};
}}
QTabBar::tab {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-bottom: none;
    color: {TEXT_MUTED};
    padding: 5px 14px;
    font-size: 12px;
}}
QTabBar::tab:selected {{ background: {PANEL_BG}; color: {TEXT}; }}
QListWidget {{
    background: {PANEL_BG};
    border: 1px solid {BORDER};
    border-radius: 6px;
    color: {TEXT};
}}
QListWidget::item {{ padding: 6px 10px; border-bottom: 1px solid {BORDER}; }}
QListWidget::item:selected {{ background: {ACCENT}; color: #fff; }}
QDialog {{ background: {PANEL_BG}; }}
QLabel#section_title {{
    color: {TEXT_MUTED};
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 1px;
    padding: 8px 12px 5px 12px;
    border-bottom: 1px solid {BORDER};
}}
"""


# ─────────────────────────────────────────
# ZOOM SCROLL AREA — THE CORRECT FIX
# ─────────────────────────────────────────
class ZoomScrollArea(QScrollArea):
    """
    THE FIX: override wheelEvent() directly on the QScrollArea subclass.
    - Ctrl+scroll  → zoom in/out
    - plain scroll → normal scroll (delegated to super)

    Why this works when eventFilter-on-viewport did NOT:
    Qt calls QScrollArea.wheelEvent() on the widget that has keyboard focus
    (or is under the cursor). If you only install an eventFilter on the
    viewport(), the QScrollArea still processes its own wheelEvent() in
    parallel → conflict and unreliable behavior.
    Overriding wheelEvent() here intercepts it cleanly at the right level.
    """

    zoom_changed = pyqtSignal(float)

    def __init__(self):
        super().__init__()
        self._label = QLabel()
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)

        self.setWidget(self._label)
        self.setWidgetResizable(False)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(f"background: {DARK_BG};")

        self._pix_original = None   # original full-res QPixmap
        self._zoom = 1.0

    # ── public API ──────────────────────────────────
    def set_pixmap(self, pix: QPixmap):
        self._pix_original = pix
        self._zoom = 1.0
        self._repaint()
        self.zoom_changed.emit(self._zoom)

    @property
    def zoom(self):
        return self._zoom

    def set_zoom(self, value: float):
        self._zoom = max(0.05, min(10.0, value))
        self._repaint()
        self.zoom_changed.emit(self._zoom)

    def zoom_fit(self):
        """Fit image to viewport."""
        if not self._pix_original:
            return
        vw = self.viewport().width()
        vh = self.viewport().height()
        sx = vw / self._pix_original.width()
        sy = vh / self._pix_original.height()
        self.set_zoom(min(sx, sy))

    def zoom_reset(self):
        self.set_zoom(1.0)

    # ── THE FIX ─────────────────────────────────────
    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # Ctrl+scroll → zoom
            delta = event.angleDelta().y()
            factor = 1.12 if delta > 0 else (1 / 1.12)
            self.set_zoom(self._zoom * factor)
            event.accept()          # ← stop here, do NOT scroll
        else:
            super().wheelEvent(event)   # normal scroll

    # ── internal ────────────────────────────────────
    def _repaint(self):
        if not self._pix_original:
            return
        w = max(1, int(self._pix_original.width()  * self._zoom))
        h = max(1, int(self._pix_original.height() * self._zoom))
        scaled = self._pix_original.scaled(
            w, h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self._label.setPixmap(scaled)
        self._label.resize(scaled.size())


# ─────────────────────────────────────────
# SELECTION OVERLAY
# ─────────────────────────────────────────
class Overlay(QWidget):

    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)

        screens = QGuiApplication.screens()
        x1 = min(s.geometry().left()   for s in screens)
        y1 = min(s.geometry().top()    for s in screens)
        x2 = max(s.geometry().right()  for s in screens)
        y2 = max(s.geometry().bottom() for s in screens)
        self.setGeometry(QRect(x1, y1, x2 - x1, y2 - y1))

        self._start = None
        self._rect  = QRect()
        self.show()

    def mousePressEvent(self, e):
        self._start = e.globalPosition().toPoint()

    def mouseMoveEvent(self, e):
        cur = e.globalPosition().toPoint()
        self._rect = QRect(
            self.mapFromGlobal(self._start),
            self.mapFromGlobal(cur)
        ).normalized()
        self.update()

    def mouseReleaseEvent(self, e):
        end = e.globalPosition().toPoint()
        self.close()
        self.callback(self._start.x(), self._start.y(), end.x(), end.y())

    def paintEvent(self, _):
        p = QPainter(self)
        # dim background
        p.fillRect(self.rect(), QColor(0, 0, 0, 80))
        if not self._rect.isEmpty():
            # clear selection
            p.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_Clear)
            p.fillRect(self._rect, Qt.GlobalColor.transparent)
            p.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_SourceOver)
            # blue border
            p.setPen(QPen(QColor(79, 142, 247), 2))
            p.drawRect(self._rect)
            # size label
            txt = f"{self._rect.width()} × {self._rect.height()}"
            p.setPen(QColor(255, 255, 255, 200))
            p.setFont(QFont("Segoe UI", 9))
            p.drawText(self._rect.left() + 5, self._rect.top() - 7, txt)


# ─────────────────────────────────────────
# HISTORY SIDEBAR
# ─────────────────────────────────────────
class HistoryItem:
    def __init__(self, pix: QPixmap, text: str, label: str):
        self.pix   = pix
        self.text  = text
        self.label = label


class HistoryPanel(QWidget):

    item_selected = pyqtSignal(object)   # emits HistoryItem

    def __init__(self):
        super().__init__()
        self.setFixedWidth(130)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title = QLabel("HISTORY")
        title.setObjectName("section_title")
        layout.addWidget(title)

        self._list = QListWidget()
        self._list.setIconSize(QSize(110, 70))
        self._list.itemClicked.connect(self._on_click)
        layout.addWidget(self._list)

        self._items: list[HistoryItem] = []

    def add(self, item: HistoryItem):
        self._items.append(item)
        thumb = item.pix.scaled(
            110, 70,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        li = QListWidgetItem(QIcon(thumb), item.label)
        li.setData(Qt.ItemDataRole.UserRole, len(self._items) - 1)
        self._list.addItem(li)
        self._list.setCurrentItem(li)

    def _on_click(self, li: QListWidgetItem):
        idx = li.data(Qt.ItemDataRole.UserRole)
        self.item_selected.emit(self._items[idx])


# ─────────────────────────────────────────
# IMAGE ADJUSTMENT DIALOG
# ─────────────────────────────────────────
class AdjustDialog(QDialog):

    def __init__(self, pix: QPixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Adjust Image")
        self.setMinimumWidth(380)
        self._original_pix = pix
        self._result_pix   = pix

        layout = QVBoxLayout(self)

        # preview
        self._preview = QLabel()
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setFixedHeight(200)
        thumb = pix.scaled(340, 200,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation)
        self._preview.setPixmap(thumb)
        layout.addWidget(self._preview)

        form = QFormLayout()
        form.setSpacing(8)

        def make_slider(lo, hi, val):
            s = QSlider(Qt.Orientation.Horizontal)
            s.setRange(lo, hi)
            s.setValue(val)
            s.valueChanged.connect(self._update_preview)
            return s

        self._brightness = make_slider(10, 300, 100)
        self._contrast   = make_slider(10, 300, 100)
        self._sharpness  = make_slider(0,  300, 100)
        self._rotate     = make_slider(0,  360, 0)

        form.addRow("Brightness", self._brightness)
        form.addRow("Contrast",   self._contrast)
        form.addRow("Sharpness",  self._sharpness)
        form.addRow("Rotate °",   self._rotate)

        self._grayscale = QCheckBox("Grayscale")
        self._grayscale.stateChanged.connect(self._update_preview)
        form.addRow("", self._grayscale)

        layout.addLayout(form)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _update_preview(self):
        img = self._pix_to_pil(self._original_pix)
        img = ImageEnhance.Brightness(img).enhance(self._brightness.value() / 100)
        img = ImageEnhance.Contrast(img).enhance(self._contrast.value() / 100)
        img = ImageEnhance.Sharpness(img).enhance(self._sharpness.value() / 100)
        if self._rotate.value():
            img = img.rotate(-self._rotate.value(), expand=True)
        if self._grayscale.isChecked():
            img = img.convert("L").convert("RGB")
        self._result_pix = self._pil_to_pix(img)
        thumb = self._result_pix.scaled(340, 200,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation)
        self._preview.setPixmap(thumb)

    def result_pixmap(self) -> QPixmap:
        return self._result_pix

    @staticmethod
    def _pix_to_pil(pix: QPixmap) -> Image.Image:
        buf = QBuffer()
        buf.open(QBuffer.OpenModeFlag.ReadWrite)
        pix.save(buf, "PNG")
        from io import BytesIO
        return Image.open(BytesIO(buf.data().data())).convert("RGB")

    @staticmethod
    def _pil_to_pix(img: Image.Image) -> QPixmap:
        from io import BytesIO
        buf = BytesIO()
        img.save(buf, "PNG")
        pix = QPixmap()
        pix.loadFromData(buf.getvalue())
        return pix


# ─────────────────────────────────────────
# MAIN WINDOW
# ─────────────────────────────────────────
class SnippingTool(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Snip Pro")
        self.setGeometry(160, 90, 1400, 800)
        self.setMinimumSize(900, 560)
        self.setStyleSheet(STYLE)

        self._pix   : QPixmap | None = None
        self._text  : str            = ""
        self._capture_count          = 0

        self._build_ui()
        self._build_shortcuts()

    # ══════════════════════════════════════
    # UI CONSTRUCTION
    # ══════════════════════════════════════
    def _build_ui(self):

        # ── Toolbar ─────────────────────────────────
        tb = QToolBar("Main")
        tb.setMovable(False)
        tb.setIconSize(QSize(16, 16))
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, tb)

        def act(label, slot, tip=""):
            a = QAction(label, self)
            a.triggered.connect(slot)
            if tip:
                a.setToolTip(tip)
            return a

        self._act_capture = act("⊹ Capture",   self.start_capture, "Ctrl+Shift+S")
        self._act_adjust  = act("✦ Adjust",    self.open_adjust,   "Edit brightness, contrast…")
        self._act_ocr     = act("⌨ Re-OCR",    self.rerun_ocr,     "Re-run OCR on current image")
        self._act_copy_i  = act("⎘ Copy Image",self.copy_image)
        self._act_copy_t  = act("⎘ Copy Text", self.copy_text)
        self._act_save    = act("↓ Save",       self.save_image,    "Ctrl+S")
        self._act_fit     = act("⤢ Fit",        self._zoom_fit,     "Fit to window")
        self._act_1x      = act("1×",           self._zoom_reset,   "Reset zoom")

        for a in [self._act_capture, None,
                  self._act_adjust, self._act_ocr, None,
                  self._act_copy_i, self._act_copy_t, None,
                  self._act_save, None,
                  self._act_fit, self._act_1x]:
            if a is None:
                tb.addSeparator()
            else:
                tb.addAction(a)

        # spacer
        sp = QWidget()
        sp.setSizePolicy(QSizePolicy.Policy.Expanding,
                         QSizePolicy.Policy.Preferred)
        tb.addWidget(sp)

        # zoom % label in toolbar
        self._zoom_display = QLabel("—")
        self._zoom_display.setStyleSheet(
            f"color:{TEXT_MUTED}; font-size:11px; padding:0 10px;")
        tb.addWidget(self._zoom_display)

        self._mode_box = QComboBox()
        self._mode_box.addItems(["Rectangle", "Fullscreen"])
        tb.addWidget(self._mode_box)

        # ── Central area ────────────────────────────
        # left: history panel
        self._history = HistoryPanel()
        self._history.item_selected.connect(self._load_history_item)

        # center: zoom scroll area
        self._scroll = ZoomScrollArea()
        self._scroll.zoom_changed.connect(
            lambda z: self._zoom_display.setText(f"{int(z*100)}%"))

        center_wrap = QWidget()
        cl = QVBoxLayout(center_wrap)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)
        t = QLabel("PREVIEW")
        t.setObjectName("section_title")
        cl.addWidget(t)
        cl.addWidget(self._scroll)

        # right: tabs (OCR + info)
        self._text_edit = QTextEdit()
        self._text_edit.setPlaceholderText("OCR text will appear here…")

        self._info_label = QLabel("No capture yet.")
        self._info_label.setStyleSheet(
            f"color:{TEXT_MUTED}; padding:12px; font-size:12px;")
        self._info_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._info_label.setWordWrap(True)

        tabs = QTabWidget()
        tabs.addTab(self._text_edit, "OCR Text")
        tabs.addTab(self._info_label, "Info")
        tabs.setMinimumWidth(320)

        right_wrap = QWidget()
        rl = QVBoxLayout(right_wrap)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)
        t2 = QLabel("OUTPUT")
        t2.setObjectName("section_title")
        rl.addWidget(t2)
        rl.addWidget(tabs)

        # main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._history)
        splitter.addWidget(center_wrap)
        splitter.addWidget(right_wrap)
        splitter.setSizes([130, 820, 350])
        splitter.setHandleWidth(1)
        self.setCentralWidget(splitter)

        # ── Status bar ──────────────────────────────
        self._status = QStatusBar()
        self.setStatusBar(self._status)

        hint = QLabel("Ctrl+Scroll = zoom  ·  Ctrl+Shift+S = capture")
        hint.setStyleSheet(f"color:{TEXT_MUTED}; font-size:11px;")
        self._status.addPermanentWidget(hint)
        self._status.showMessage("Ready")

    def _build_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+Shift+S"), self).activated.connect(self.start_capture)
        QShortcut(QKeySequence("Ctrl+S"),       self).activated.connect(self.save_image)
        QShortcut(QKeySequence("Ctrl+Shift+C"), self).activated.connect(self.copy_image)
        QShortcut(QKeySequence("Ctrl+Shift+T"), self).activated.connect(self.copy_text)
        QShortcut(QKeySequence("Ctrl+0"),       self).activated.connect(self._zoom_reset)
        QShortcut(QKeySequence("Ctrl+F"),       self).activated.connect(self._zoom_fit)
        QShortcut(QKeySequence("Ctrl+="),       self).activated.connect(
            lambda: self._scroll.set_zoom(self._scroll.zoom * 1.2))
        QShortcut(QKeySequence("Ctrl+-"),       self).activated.connect(
            lambda: self._scroll.set_zoom(self._scroll.zoom / 1.2))

    # ══════════════════════════════════════
    # CAPTURE
    # ══════════════════════════════════════
    def start_capture(self):
        mode = self._mode_box.currentText()
        if mode == "Fullscreen":
            self._do_fullscreen_capture()
        else:
            self._status.showMessage("Draw a selection…")
            self.overlay = Overlay(self._process_capture)

    def _do_fullscreen_capture(self):
        self._status.showMessage("Capturing fullscreen…")
        QTimer.singleShot(300, self.__fullscreen_grab)

    def __fullscreen_grab(self):
        screen = QGuiApplication.primaryScreen()
        geo = screen.geometry()
        self._process_capture(
            geo.left(), geo.top(),
            geo.right(), geo.bottom()
        )

    def _process_capture(self, x1, y1, x2, y2):
        self._status.showMessage("Grabbing…")
        with mss.mss() as sct:
            mon = {
                "left":   min(x1, x2),
                "top":    min(y1, y2),
                "width":  abs(x2 - x1) or 1,
                "height": abs(y2 - y1) or 1,
            }
            shot = sct.grab(mon)
            img  = Image.frombytes("RGB", shot.size, shot.rgb)

        self._status.showMessage("Running OCR…")
        text = pytesseract.image_to_string(img)

        # convert PIL → QPixmap without temp file
        from io import BytesIO
        buf = BytesIO()
        img.save(buf, "PNG")
        pix = QPixmap()
        pix.loadFromData(buf.getvalue())

        self._capture_count += 1
        label = f"#{self._capture_count}  {mon['width']}×{mon['height']}"

        self._scroll.set_pixmap(pix)
        self._text_edit.setText(text)
        self._pix  = pix
        self._text = text

        self._history.add(HistoryItem(pix, text, label))
        self._update_info(pix, text, mon)
        self._status.showMessage(f"Done ✔  —  {label}")

    def _update_info(self, pix, text, mon):
        words = len(text.split())
        chars = len(text)
        info  = (
            f"<b>Size:</b> {pix.width()} × {pix.height()} px<br>"
            f"<b>Region:</b> {mon['left']}, {mon['top']} → "
            f"{mon['left']+mon['width']}, {mon['top']+mon['height']}<br><br>"
            f"<b>OCR words:</b> {words}<br>"
            f"<b>OCR chars:</b> {chars}<br>"
        )
        self._info_label.setText(info)

    # ══════════════════════════════════════
    # ACTIONS
    # ══════════════════════════════════════
    def copy_image(self):
        if self._pix:
            QApplication.clipboard().setPixmap(self._pix)
            self._status.showMessage("Image copied ✔")

    def copy_text(self):
        if self._text:
            QApplication.clipboard().setText(self._text)
            self._status.showMessage("Text copied ✔")

    def save_image(self):
        if not self._pix:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Image", f"capture_{self._capture_count}.png",
            "PNG (*.png);;JPEG (*.jpg);;BMP (*.bmp)"
        )
        if path:
            self._pix.save(path)
            self._status.showMessage(f"Saved → {path}")

    def open_adjust(self):
        if not self._pix:
            self._status.showMessage("Capture something first.")
            return
        dlg = AdjustDialog(self._pix, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_pix = dlg.result_pixmap()
            self._pix = new_pix
            self._scroll.set_pixmap(new_pix)
            self._status.showMessage("Adjustments applied ✔")

    def rerun_ocr(self):
        if not self._pix:
            return
        self._status.showMessage("Re-running OCR…")
        img = AdjustDialog._pix_to_pil(self._pix)
        self._text = pytesseract.image_to_string(img)
        self._text_edit.setText(self._text)
        self._status.showMessage("OCR complete ✔")

    def _zoom_fit(self):
        self._scroll.zoom_fit()

    def _zoom_reset(self):
        self._scroll.zoom_reset()

    def _load_history_item(self, item: HistoryItem):
        self._pix  = item.pix
        self._text = item.text
        self._scroll.set_pixmap(item.pix)
        self._text_edit.setText(item.text)
        self._status.showMessage(f"Loaded: {item.label}")


# ─────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = SnippingTool()
    win.show()
    sys.exit(app.exec())