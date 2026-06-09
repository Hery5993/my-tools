import sys
import os
import mss
import pytesseract
from PIL import Image

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QLabel, QTextEdit, QToolBar,
    QComboBox, QSplitter, QStatusBar
)

from PyQt6.QtGui import (
    QAction, QIcon, QPixmap, QPainter,
    QColor, QPen, QGuiApplication
)

from PyQt6.QtCore import Qt, QRect
from PyQt6.QtSvg import QSvgRenderer


# =========================
# LOAD SVG ICON
# =========================
def load_svg_icon(path, size=24):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(base_dir, path)

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    renderer = QSvgRenderer(full_path)
    renderer.render(painter)
    painter.end()

    return QIcon(pixmap)


# =========================
# OVERLAY (MULTI SCREEN + RUBBERBAND FIX)
# =========================
class Overlay(QWidget):

    def __init__(self, callback):
        super().__init__()
        self.callback = callback

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )

        self.setWindowOpacity(0.25)
        self.setCursor(Qt.CursorShape.CrossCursor)

        screens = QGuiApplication.screens()

        x_min = min(s.geometry().left() for s in screens)
        y_min = min(s.geometry().top() for s in screens)
        x_max = max(s.geometry().right() for s in screens)
        y_max = max(s.geometry().bottom() for s in screens)

        self.setGeometry(QRect(
            x_min, y_min,
            x_max - x_min,
            y_max - y_min
        ))

        self.start_global = None
        self.rect = QRect()

        self.show()

    def mousePressEvent(self, e):
        self.start_global = e.globalPosition().toPoint()
        self.rect = QRect(self.mapFromGlobal(self.start_global), self.mapFromGlobal(self.start_global))
        self.update()

    def mouseMoveEvent(self, e):
        current = e.globalPosition().toPoint()

        self.rect = QRect(
            self.mapFromGlobal(self.start_global),
            self.mapFromGlobal(current)
        ).normalized()

        self.update()

    def mouseReleaseEvent(self, e):
        end = e.globalPosition().toPoint()
        self.close()

        x1 = min(self.start_global.x(), end.x())
        y1 = min(self.start_global.y(), end.y())
        x2 = max(self.start_global.x(), end.x())
        y2 = max(self.start_global.y(), end.y())

        self.callback(x1, y1, x2, y2)

    def paintEvent(self, e):
        painter = QPainter(self)
        pen = QPen(QColor(0, 180, 255), 2)
        painter.setPen(pen)
        painter.drawRect(self.rect)


# =========================
# MAIN WINDOW
# =========================
class SnippingTool(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Snipping Tool Pro")
        self.setGeometry(200, 120, 1200, 700)

        # =========================
        # CENTRAL SPLITTER
        # =========================
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.text_box = QTextEdit()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.image_label)
        splitter.addWidget(self.text_box)
        splitter.setSizes([700, 500])

        self.setCentralWidget(splitter)

        # =========================
        # TOOLBAR
        # =========================
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)

        self.act_capture = QAction("Capture", self)
        self.act_capture.triggered.connect(self.start_capture)

        self.act_quit = QAction("Quitter", self)
        self.act_quit.triggered.connect(self.close)

        toolbar.addAction(self.act_capture)

        self.mode_box = QComboBox()
        self.mode_box.addItems(["Rectangle", "Fenêtre", "Écran complet"])
        self.mode_box.currentTextChanged.connect(self.set_mode)

        toolbar.addWidget(self.mode_box)
        toolbar.addSeparator()
        toolbar.addAction(self.act_quit)

        self.mode = "Rectangle"

        # =========================
        # STATUS BAR
        # =========================
        self.status = QStatusBar()
        self.setStatusBar(self.status)

        self.status.showMessage("Prêt")

    # =========================
    def set_mode(self, mode):
        self.mode = mode
        self.status.showMessage(f"Mode sélectionné : {mode}")

    # =========================
    def start_capture(self):
        self.status.showMessage("Sélection en cours...")
        self.overlay = Overlay(self.process_capture)
        self.overlay.show()

    # =========================
    def process_capture(self, x1, y1, x2, y2):

        self.status.showMessage("Capture en cours...")

        with mss.MSS() as sct:
            monitor = {
                "left": x1,
                "top": y1,
                "width": x2 - x1,
                "height": y2 - y1
            }

            shot = sct.grab(monitor)
            img = Image.frombytes("RGB", shot.size, shot.rgb)

        self.status.showMessage("OCR en cours...")

        text = pytesseract.image_to_string(img)

        img.save("capture.png")

        pix = QPixmap("capture.png")
        self.image_label.setPixmap(
            pix.scaled(
                800, 600,
                Qt.AspectRatioMode.KeepAspectRatio
            )
        )

        self.text_box.setText(text)

        self.status.showMessage("Terminé ✔")


# =========================
# RUN
# =========================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = SnippingTool()
    win.show()
    sys.exit(app.exec())