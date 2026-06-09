import sys
import os
import mss
import pytesseract
from PIL import Image

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QLabel, QTextEdit, QToolBar,
    QComboBox, QStatusBar, QFileDialog,
    QSplitter, QScrollArea, QVBoxLayout,
    QHBoxLayout, QFrame, QPushButton,
    QSizePolicy
)

from PyQt6.QtGui import (
    QAction, QIcon, QPixmap,
    QColor, QPen, QPainter,
    QGuiApplication, QWheelEvent,
    QFont, QPalette
)

from PyQt6.QtCore import Qt, QRect, QEvent, QSize, QPoint
from PyQt6.QtSvg import QSvgRenderer


# =========================
# THEME CONSTANTS
# =========================
DARK_BG       = "#16181D"
PANEL_BG      = "#1E2028"
TOOLBAR_BG    = "#13151A"
BORDER_COLOR  = "#2A2D38"
ACCENT        = "#4F8EF7"
ACCENT_HOVER  = "#6BA3FF"
TEXT_PRIMARY  = "#E8EAF0"
TEXT_MUTED    = "#6B7080"
SUCCESS       = "#3DD68C"
SURFACE       = "#252830"

GLOBAL_STYLE = f"""
    QMainWindow, QWidget {{
        background-color: {DARK_BG};
        color: {TEXT_PRIMARY};
        font-family: "Segoe UI", "Inter", "SF Pro Display", sans-serif;
        font-size: 13px;
    }}

    QToolBar {{
        background-color: {TOOLBAR_BG};
        border-bottom: 1px solid {BORDER_COLOR};
        padding: 6px 8px;
        spacing: 4px;
    }}

    QToolBar QToolButton {{
        background-color: transparent;
        border: 1px solid transparent;
        border-radius: 6px;
        color: {TEXT_PRIMARY};
        padding: 6px 12px;
        font-size: 12px;
        min-width: 80px;
    }}

    QToolBar QToolButton:hover {{
        background-color: {SURFACE};
        border-color: {BORDER_COLOR};
    }}

    QToolBar QToolButton:pressed {{
        background-color: {ACCENT};
        color: white;
    }}

    QComboBox {{
        background-color: {SURFACE};
        border: 1px solid {BORDER_COLOR};
        border-radius: 6px;
        color: {TEXT_PRIMARY};
        padding: 4px 10px;
        min-width: 120px;
    }}

    QComboBox::drop-down {{
        border: none;
        width: 20px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {PANEL_BG};
        border: 1px solid {BORDER_COLOR};
        color: {TEXT_PRIMARY};
        selection-background-color: {ACCENT};
    }}

    QTextEdit {{
        background-color: {PANEL_BG};
        border: none;
        color: {TEXT_PRIMARY};
        font-family: "JetBrains Mono", "Consolas", "Courier New", monospace;
        font-size: 12px;
        padding: 12px;
        line-height: 1.6;
    }}

    QScrollArea {{
        border: none;
        background-color: transparent;
    }}

    QScrollBar:vertical {{
        background-color: {DARK_BG};
        width: 8px;
        border-radius: 4px;
    }}

    QScrollBar::handle:vertical {{
        background-color: {BORDER_COLOR};
        border-radius: 4px;
        min-height: 20px;
    }}

    QScrollBar::handle:vertical:hover {{
        background-color: {TEXT_MUTED};
    }}

    QScrollBar:horizontal {{
        background-color: {DARK_BG};
        height: 8px;
        border-radius: 4px;
    }}

    QScrollBar::handle:horizontal {{
        background-color: {BORDER_COLOR};
        border-radius: 4px;
    }}

    QScrollBar::add-line, QScrollBar::sub-line {{
        width: 0; height: 0;
    }}

    QSplitter::handle {{
        background-color: {BORDER_COLOR};
        width: 1px;
    }}

    QStatusBar {{
        background-color: {TOOLBAR_BG};
        border-top: 1px solid {BORDER_COLOR};
        color: {TEXT_MUTED};
        padding: 4px 12px;
        font-size: 11px;
    }}

    QLabel#zoom_label {{
        color: {TEXT_MUTED};
        font-size: 11px;
        padding: 0 8px;
    }}

    QLabel#panel_title {{
        color: {TEXT_MUTED};
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 1.2px;
        padding: 8px 12px 4px 12px;
        text-transform: uppercase;
        border-bottom: 1px solid {BORDER_COLOR};
    }}

    QLabel#empty_state {{
        color: {TEXT_MUTED};
        font-size: 14px;
    }}
"""


# =========================
# SVG ICON LOADER
# =========================
def load_svg_icon(path, size=20):
    base = os.path.dirname(os.path.abspath(__file__))
    full = os.path.join(base, path)
    if not os.path.exists(full):
        return QIcon()
    return QIcon(full)


# =========================
# IMAGE FRAME — ZOOM FIXED
# =========================
class ImageFrame(QLabel):
    """
    Root cause of the broken zoom:
    QLabel does NOT forward wheelEvent through its normal chain when placed
    directly inside a QScrollArea — the scroll area's viewport intercepts it.
    Fix: install an eventFilter on the VIEWPORT of the parent scroll area,
    and handle WheelEvent there instead of overriding wheelEvent on QLabel.
    """

    def __init__(self, scroll_area: "ZoomScrollArea"):
        super().__init__()
        self.scroll_area = scroll_area
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(1, 1)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.pix = None
        self.zoom = 1.0

    def set_image(self, pix: QPixmap):
        self.pix = pix
        self.zoom = 1.0
        self._render()

    def adjust_zoom(self, delta: float):
        if not self.pix:
            return
        self.zoom = max(0.1, min(8.0, self.zoom + delta))
        self._render()

    def _render(self):
        if not self.pix:
            return
        w = int(self.pix.width() * self.zoom)
        h = int(self.pix.height() * self.zoom)
        scaled = self.pix.scaled(
            w, h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        super().setPixmap(scaled)
        self.resize(scaled.size())


class ZoomScrollArea(QScrollArea):
    """
    Wraps ImageFrame and installs an eventFilter on its own viewport
    to intercept Ctrl+Wheel — the correct place to catch it.
    """

    def __init__(self):
        super().__init__()
        self.image_frame = ImageFrame(self)

        self.setWidget(self.image_frame)
        self.setWidgetResizable(False)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(f"background-color: {DARK_BG};")

        # ✅ THE FIX: filter events on the viewport, not on the QLabel
        self.viewport().installEventFilter(self)

        self._zoom_label = None  # will be set by main window

    def eventFilter(self, obj, event):
        if obj is self.viewport() and event.type() == QEvent.Type.Wheel:
            if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                delta = 0.15 if event.angleDelta().y() > 0 else -0.15
                self.image_frame.adjust_zoom(delta)
                if self._zoom_label:
                    pct = int(self.image_frame.zoom * 100)
                    self._zoom_label.setText(f"{pct}%")
                return True  # consumed
        return super().eventFilter(obj, event)


# =========================
# TEXT PANEL
# =========================
class TextPanel(QWidget):

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title = QLabel("OCR TEXT")
        title.setObjectName("panel_title")
        layout.addWidget(title)

        self.text = QTextEdit()
        self.text.setPlaceholderText("Extracted text will appear here…")
        layout.addWidget(self.text)


# =========================
# OVERLAY — MULTI SCREEN
# =========================
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
        x1 = min(s.geometry().left() for s in screens)
        y1 = min(s.geometry().top() for s in screens)
        x2 = max(s.geometry().right() for s in screens)
        y2 = max(s.geometry().bottom() for s in screens)

        self.setGeometry(QRect(x1, y1, x2 - x1, y2 - y1))

        self.start = None
        self.rect = QRect()
        self.show()

    def mousePressEvent(self, e):
        self.start = e.globalPosition().toPoint()

    def mouseMoveEvent(self, e):
        cur = e.globalPosition().toPoint()
        self.rect = QRect(
            self.mapFromGlobal(self.start),
            self.mapFromGlobal(cur)
        ).normalized()
        self.update()

    def mouseReleaseEvent(self, e):
        end = e.globalPosition().toPoint()
        self.close()
        self.callback(self.start.x(), self.start.y(), end.x(), end.y())

    def paintEvent(self, e):
        p = QPainter(self)

        # dim overlay
        p.fillRect(self.rect.united(self.rect), QColor(0, 0, 0, 60))

        # selection rect — cut-out feel
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        p.fillRect(self.rect, Qt.GlobalColor.transparent)

        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        pen = QPen(QColor(79, 142, 247), 2)
        pen.setStyle(Qt.PenStyle.SolidLine)
        p.setPen(pen)
        p.drawRect(self.rect)

        # size hint
        if self.rect.width() > 60 and self.rect.height() > 30:
            p.setPen(QColor(255, 255, 255, 180))
            font = QFont("Segoe UI", 9)
            p.setFont(font)
            p.drawText(
                self.rect.left() + 4,
                self.rect.top() - 6,
                f"{self.rect.width()} × {self.rect.height()}"
            )


# =========================
# MAIN WINDOW
# =========================
class SnippingTool(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Snip")
        self.setGeometry(180, 100, 1300, 760)
        self.setMinimumSize(800, 500)
        self.setStyleSheet(GLOBAL_STYLE)

        self.current_pix = None
        self.current_text = ""

        self._build_ui()

    # --------------------------------------------------
    def _build_ui(self):

        # ── Image panel ──────────────────────────────
        self.zoom_scroll = ZoomScrollArea()

        img_container = QWidget()
        img_layout = QVBoxLayout(img_container)
        img_layout.setContentsMargins(0, 0, 0, 0)
        img_layout.setSpacing(0)

        img_title = QLabel("PREVIEW")
        img_title.setObjectName("panel_title")
        img_layout.addWidget(img_title)
        img_layout.addWidget(self.zoom_scroll)

        # zoom label lives in the status bar
        self.zoom_label = QLabel("100%")
        self.zoom_label.setObjectName("zoom_label")
        self.zoom_scroll._zoom_label = self.zoom_label

        # ── Text panel ───────────────────────────────
        self.text_panel = TextPanel()

        # ── Splitter ─────────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(img_container)
        splitter.addWidget(self.text_panel)
        splitter.setSizes([780, 420])
        splitter.setHandleWidth(1)

        self.setCentralWidget(splitter)

        # ── Toolbar ──────────────────────────────────
        tb = QToolBar("Main")
        tb.setMovable(False)
        tb.setIconSize(QSize(16, 16))
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, tb)

        self.act_capture = QAction("⊹  Capture", self)
        self.act_capture.setShortcut("Ctrl+Shift+S")
        self.act_capture.triggered.connect(self.start_capture)

        self.act_copy_img = QAction("⎘  Copy Image", self)
        self.act_copy_img.setShortcut("Ctrl+Shift+C")
        self.act_copy_img.triggered.connect(self.copy_image)

        self.act_copy_txt = QAction("⎘  Copy Text", self)
        self.act_copy_txt.setShortcut("Ctrl+Shift+T")
        self.act_copy_txt.triggered.connect(self.copy_text)

        self.act_save = QAction("↓  Save", self)
        self.act_save.setShortcut("Ctrl+S")
        self.act_save.triggered.connect(self.save_image)

        tb.addAction(self.act_capture)
        tb.addSeparator()
        tb.addAction(self.act_copy_img)
        tb.addAction(self.act_copy_txt)
        tb.addSeparator()
        tb.addAction(self.act_save)

        # spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tb.addWidget(spacer)

        self.mode_box = QComboBox()
        self.mode_box.addItems(["Rectangle", "Window", "Fullscreen"])
        self.mode_box.setToolTip("Capture mode")
        tb.addWidget(self.mode_box)

        # ── Status bar ───────────────────────────────
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.addPermanentWidget(self.zoom_label)

        hint = QLabel("Ctrl+Scroll to zoom")
        hint.setObjectName("zoom_label")
        self.status.addPermanentWidget(hint)

        self.status.showMessage("Ready — press Ctrl+Shift+S to capture")

    # --------------------------------------------------
    def start_capture(self):
        self.status.showMessage("Draw a selection…")
        self.overlay = Overlay(self.process_capture)

    def process_capture(self, x1, y1, x2, y2):
        self.status.showMessage("Capturing…")

        with mss.mss() as sct:
            monitor = {
                "left":   min(x1, x2),
                "top":    min(y1, y2),
                "width":  abs(x2 - x1),
                "height": abs(y2 - y1),
            }
            shot = sct.grab(monitor)
            img = Image.frombytes("RGB", shot.size, shot.rgb)

        self.status.showMessage("Running OCR…")
        text = pytesseract.image_to_string(img)

        img.save("capture.png")
        pix = QPixmap("capture.png")

        self.zoom_scroll.image_frame.set_image(pix)
        self.zoom_label.setText("100%")
        self.text_panel.text.setText(text)

        self.current_pix = pix
        self.current_text = text

        self.status.showMessage("Done ✔  —  Ctrl+Scroll to zoom")

    def copy_image(self):
        if self.current_pix:
            QApplication.clipboard().setPixmap(self.current_pix)
            self.status.showMessage("Image copied ✔")

    def copy_text(self):
        if self.current_text:
            QApplication.clipboard().setText(self.current_text)
            self.status.showMessage("Text copied ✔")

    def save_image(self):
        if not self.current_pix:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Image", "capture.png",
            "PNG (*.png);;JPEG (*.jpg)"
        )
        if path:
            self.current_pix.save(path)
            self.status.showMessage(f"Saved → {path}")


# =========================
# RUN
# =========================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = SnippingTool()
    win.show()
    sys.exit(app.exec())