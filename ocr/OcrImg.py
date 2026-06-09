import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import subprocess
import os
import cv2

class OCRApp:
    def __init__(self, root):
        self.root = root
        self.root.title("OCR Zoom + Tesseract (symboles améliorés)")

        # ---------- UI SPLIT ----------
        self.top = tk.Frame(root)
        self.top.pack(fill=tk.BOTH, expand=True)

        self.bottom = tk.Frame(root, height=200)
        self.bottom.pack(fill=tk.BOTH)

        self.canvas = tk.Canvas(self.top, bg="black", cursor="cross")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.text = tk.Text(self.bottom, height=10)
        self.text.pack(fill=tk.BOTH, expand=True)

        btn = tk.Frame(self.bottom)
        btn.pack()

        tk.Button(btn, text="Charger image", command=self.load_image).pack(side=tk.LEFT)

        # ---------- IMAGE ----------
        self.image = None
        self.image_path = None
        self.tk_image = None

        # ---------- ZOOM / PAN ----------
        self.zoom = 1.0
        self.offset_x = 0
        self.offset_y = 0

        # ---------- SELECTION ----------
        self.start_x = self.start_y = 0
        self.end_x = self.end_y = 0
        self.rect = None

        # ---------- EVENTS ----------
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        self.canvas.bind("<MouseWheel>", self.zoom_mouse)
        self.canvas.bind("<Button-4>", self.zoom_linux)
        self.canvas.bind("<Button-5>", self.zoom_linux)

    # ======================================================
    # IMAGE
    # ======================================================
    def load_image(self):
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp")]
        )
        if not path:
            return

        self.image_path = path
        self.image = Image.open(path)

        self.zoom = 1.0
        self.offset_x = 0
        self.offset_y = 0

        self.render()

    def render(self):
        if not self.image:
            return

        w, h = self.image.size
        img = self.image.resize((int(w * self.zoom), int(h * self.zoom)))

        self.tk_image = ImageTk.PhotoImage(img)

        self.canvas.delete("all")
        self.canvas.create_image(self.offset_x, self.offset_y, anchor="nw", image=self.tk_image)

    # ======================================================
    # ZOOM (CENTRÉ SOURIS)
    # ======================================================
    def zoom_at(self, factor, mx, my):
        old_zoom = self.zoom
        new_zoom = self.zoom * factor
        new_zoom = max(0.2, min(new_zoom, 6))

        factor = new_zoom / old_zoom
        self.zoom = new_zoom

        self.offset_x = mx - (mx - self.offset_x) * factor
        self.offset_y = my - (my - self.offset_y) * factor

        self.render()

    def zoom_mouse(self, event):
        factor = 1.1 if event.delta > 0 else 0.9
        self.zoom_at(factor, event.x, event.y)

    def zoom_linux(self, event):
        mx = self.canvas.winfo_pointerx() - self.canvas.winfo_rootx()
        my = self.canvas.winfo_pointery() - self.canvas.winfo_rooty()

        if event.num == 4:
            self.zoom_at(1.1, mx, my)
        else:
            self.zoom_at(0.9, mx, my)

    # ======================================================
    # SELECTION
    # ======================================================
    def on_press(self, event):
        self.start_x, self.start_y = event.x, event.y
        self.rect = None

    def on_drag(self, event):
        if self.rect:
            self.canvas.delete(self.rect)

        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y,
            event.x, event.y,
            outline="red", width=2
        )

    def on_release(self, event):
        self.end_x, self.end_y = event.x, event.y
        self.run_ocr()

    # ======================================================
    # OCR (AMÉLIORÉ SYMBOLS)
    # ======================================================
    def run_ocr(self):
        if not self.image:
            return

        if self.start_x == self.end_x or self.start_y == self.end_y:
            return

        # conversion canvas -> image
        x1 = int((self.start_x - self.offset_x) / self.zoom)
        y1 = int((self.start_y - self.offset_y) / self.zoom)
        x2 = int((self.end_x - self.offset_x) / self.zoom)
        y2 = int((self.end_y - self.offset_y) / self.zoom)

        x1, x2 = sorted([x1, x2])
        y1, y2 = sorted([y1, y2])

        cropped = self.image.crop((x1, y1, x2, y2))

        tmp_file = "tmp_crop.png"
        cropped.save(tmp_file)

        # --- PREPROCESSING (améliore Ø, °, etc.) ---
        img = cv2.imread(tmp_file)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        cv2.imwrite(tmp_file, gray)

        # --- CONFIG TESSERACT AMÉLIORÉ ---
        config = (
            "-l eng+fra --psm 11 "
            "-c tessedit_char_whitelist="
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
            "0123456789Øø°+-=/"
        )

        result = subprocess.run(
            ["tesseract", tmp_file, "stdout"] + config.split(),
            capture_output=True,
            text=True
        )

        os.remove(tmp_file)

        text = result.stdout.strip()

        self.text.delete("1.0", tk.END)
        self.text.insert(tk.END, text if text else "[Aucun texte détecté]")

# RUN
root = tk.Tk()
app = OCRApp(root)
root.mainloop()