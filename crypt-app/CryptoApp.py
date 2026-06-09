import os
import customtkinter as ctk
from tkinter import filedialog, messagebox

from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class CryptoApp:

    def __init__(self, root):
        self.root = root
        self.root.title("Secure File Encryptor")
        self.root.geometry("750x450")

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.encrypt_file_path = ""
        self.decrypt_file_path = ""

        self.encrypt_password_visible = False
        self.decrypt_password_visible = False

        title = ctk.CTkLabel(
            root,
            text="🔐 Secure File Encryptor",
            font=("Arial", 24, "bold")
        )
        title.pack(pady=15)

        # Tabs
        self.tabs = ctk.CTkTabview(root)
        self.tabs.pack(fill="both", expand=True, padx=20, pady=10)

        self.encrypt_tab = self.tabs.add("Encrypt")
        self.decrypt_tab = self.tabs.add("Decrypt")

        self.build_encrypt_tab()
        self.build_decrypt_tab()

    # =========================
    # KEY DERIVATION
    # =========================
    def derive_key(self, password, salt):
        kdf = Scrypt(
            salt=salt,
            length=32,
            n=2**14,
            r=8,
            p=1
        )
        return kdf.derive(password.encode())

    # =========================
    # ENCRYPT TAB
    # =========================
    def build_encrypt_tab(self):

        ctk.CTkButton(
            self.encrypt_tab,
            text="📁 Choisir un fichier",
            command=self.select_encrypt_file
        ).pack(pady=15)

        self.encrypt_label = ctk.CTkLabel(
            self.encrypt_tab,
            text="Aucun fichier sélectionné"
        )
        self.encrypt_label.pack()

        # password frame
        frame = ctk.CTkFrame(self.encrypt_tab, fg_color="transparent")
        frame.pack(pady=20)

        self.encrypt_password = ctk.CTkEntry(
            frame,
            width=300,
            show="*",
            placeholder_text="Mot de passe"
        )
        self.encrypt_password.pack(side="left")

        self.encrypt_eye_btn = ctk.CTkButton(
            frame,
            text="👁",
            width=40,
            command=self.toggle_encrypt_password
        )
        self.encrypt_eye_btn.pack(side="left", padx=5)

        ctk.CTkButton(
            self.encrypt_tab,
            text="🔒 Crypter",
            command=self.encrypt_file
        ).pack(pady=10)

    # =========================
    # DECRYPT TAB
    # =========================
    def build_decrypt_tab(self):

        ctk.CTkButton(
            self.decrypt_tab,
            text="📂 Choisir un fichier .enc",
            command=self.select_decrypt_file
        ).pack(pady=15)

        self.decrypt_label = ctk.CTkLabel(
            self.decrypt_tab,
            text="Aucun fichier sélectionné"
        )
        self.decrypt_label.pack()

        # password frame
        frame = ctk.CTkFrame(self.decrypt_tab, fg_color="transparent")
        frame.pack(pady=20)

        self.decrypt_password = ctk.CTkEntry(
            frame,
            width=300,
            show="*",
            placeholder_text="Mot de passe"
        )
        self.decrypt_password.pack(side="left")

        self.decrypt_eye_btn = ctk.CTkButton(
            frame,
            text="👁",
            width=40,
            command=self.toggle_decrypt_password
        )
        self.decrypt_eye_btn.pack(side="left", padx=5)

        ctk.CTkButton(
            self.decrypt_tab,
            text="🔓 Décrypter",
            command=self.decrypt_file
        ).pack(pady=10)

    # =========================
    # FILE SELECT
    # =========================
    def select_encrypt_file(self):
        path = filedialog.askopenfilename()
        if path:
            self.encrypt_file_path = path
            self.encrypt_label.configure(text=os.path.basename(path))

    def select_decrypt_file(self):
        path = filedialog.askopenfilename(filetypes=[("Encrypted", "*.enc")])
        if path:
            self.decrypt_file_path = path
            self.decrypt_label.configure(text=os.path.basename(path))

    # =========================
    # TOGGLE PASSWORD
    # =========================
    def toggle_encrypt_password(self):
        self.encrypt_password_visible = not self.encrypt_password_visible

        if self.encrypt_password_visible:
            self.encrypt_password.configure(show="")
            self.encrypt_eye_btn.configure(text="🙈")
        else:
            self.encrypt_password.configure(show="*")
            self.encrypt_eye_btn.configure(text="👁")

    def toggle_decrypt_password(self):
        self.decrypt_password_visible = not self.decrypt_password_visible

        if self.decrypt_password_visible:
            self.decrypt_password.configure(show="")
            self.decrypt_eye_btn.configure(text="🙈")
        else:
            self.decrypt_password.configure(show="*")
            self.decrypt_eye_btn.configure(text="👁")

    # =========================
    # ENCRYPT
    # =========================
    def encrypt_file(self):

        if not self.encrypt_file_path:
            messagebox.showerror("Erreur", "Sélectionnez un fichier.")
            return

        password = self.encrypt_password.get()
        if not password:
            messagebox.showerror("Erreur", "Mot de passe requis.")
            return

        try:
            with open(self.encrypt_file_path, "rb") as f:
                data = f.read()

            salt = os.urandom(16)
            nonce = os.urandom(12)

            key = self.derive_key(password, salt)
            aes = AESGCM(key)

            encrypted = aes.encrypt(nonce, data, None)

            output_file = self.encrypt_file_path + ".enc"

            with open(output_file, "wb") as f:
                f.write(salt)
                f.write(nonce)
                f.write(encrypted)

            messagebox.showinfo("Succès", f"Fichier crypté:\n{output_file}")

        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    # =========================
    # DECRYPT
    # =========================
    def decrypt_file(self):

        if not self.decrypt_file_path:
            messagebox.showerror("Erreur", "Sélectionnez un fichier .enc")
            return

        password = self.decrypt_password.get()
        if not password:
            messagebox.showerror("Erreur", "Mot de passe requis.")
            return

        try:
            with open(self.decrypt_file_path, "rb") as f:
                salt = f.read(16)
                nonce = f.read(12)
                encrypted = f.read()

            key = self.derive_key(password, salt)
            aes = AESGCM(key)

            decrypted = aes.decrypt(nonce, encrypted, None)

            output_file = self.decrypt_file_path.replace(".enc", "")

            with open(output_file, "wb") as f:
                f.write(decrypted)

            messagebox.showinfo("Succès", f"Fichier restauré:\n{output_file}")

        except Exception:
            messagebox.showerror(
                "Erreur",
                "Mot de passe incorrect ou fichier corrompu."
            )


if __name__ == "__main__":
    root = ctk.CTk()
    app = CryptoApp(root)
    root.mainloop()