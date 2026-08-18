import os
import random
import tkinter as tk
from PIL import Image, ImageTk, ImageDraw


class FlashcardApp:
    def __init__(self, root, question_folder, answer_folder):
        self.root = root
        self.root.title("Image Pair Flashcards")

        # ~10% smaller than 800
        self.size = 720

        self.q_folder = question_folder
        self.a_folder = answer_folder

        self.pairs = self.load_pairs()
        if not self.pairs:
            raise ValueError("No matching image pairs found")

        # UI
        self.label = tk.Label(root)
        self.label.pack(padx=10, pady=10)

        self.info_label = tk.Label(root, text="", font=("Arial", 12))
        self.info_label.pack(pady=5)

        self.button = tk.Button(root, text="Reveal", command=self.on_button)
        self.button.pack(pady=10)

        self.revealed = False
        self.next_card()

    # ---------------- Load pairs ----------------
    def load_pairs(self):
        q_files = {
            os.path.splitext(f)[0]: os.path.join(self.q_folder, f)
            for f in os.listdir(self.q_folder)
            if f.lower().endswith(".png")
        }

        a_files = {
            os.path.splitext(f)[0]: os.path.join(self.a_folder, f)
            for f in os.listdir(self.a_folder)
            if f.lower().endswith(".png")
        }

        return [(k, q_files[k], a_files[k]) for k in q_files if k in a_files]

    # ---------------- COVER transform ----------------
    def cover_transform(self, path):
        img = Image.open(path).convert("RGBA")
        size = self.size

        z_min = 1.0
        z_max = 1.5
        zoom = random.uniform(z_min, z_max)

        w, h = img.size
        scale = max(size / w, size / h) * zoom

        img = img.resize(
            (int(w * scale), int(h * scale)),
            Image.Resampling.LANCZOS
        )

        angle = random.uniform(0, 360)
        img = img.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)

        w, h = img.size
        left = (w - size) // 2
        top = (h - size) // 2

        img = img.crop((left, top, left + size, top + size))

        return img, angle, zoom

    # ---------------- Apply same transform ----------------
    def apply_same_transform(self, path, angle, zoom):
        img = Image.open(path).convert("RGBA")
        size = self.size

        w, h = img.size
        scale = max(size / w, size / h) * zoom

        img = img.resize(
            (int(w * scale), int(h * scale)),
            Image.Resampling.LANCZOS
        )

        img = img.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)

        w, h = img.size
        left = (w - size) // 2
        top = (h - size) // 2

        img = img.crop((left, top, left + size, top + size))

        return img

    # ---------------- Mask ----------------
    def circular_mask(self, img):
        mask = Image.new("L", (self.size, self.size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, self.size, self.size), fill=255)
        img.putalpha(mask)
        return img

    # ---------------- Logic ----------------
    def next_card(self):
        self.revealed = False
        self.button.config(text="Reveal")

        self.current_id, q_path, a_path = random.choice(self.pairs)

        q_img, angle, zoom = self.cover_transform(q_path)
        a_img = self.apply_same_transform(a_path, angle, zoom)

        self.q_img = self.circular_mask(q_img)
        self.a_img = self.circular_mask(a_img)

        self.info_label.config(text="")
        self.show_question()

    # ---------------- Display ----------------
    def show_question(self):
        self.photo = ImageTk.PhotoImage(self.q_img)
        self.label.config(image=self.photo)
        self.label.image = self.photo

    def show_answer(self):
        self.photo = ImageTk.PhotoImage(self.a_img)
        self.label.config(image=self.photo)
        self.label.image = self.photo

    # ---------------- Button ----------------
    def on_button(self):
        name = self.current_id

        if not self.revealed:
            self.show_answer()
            self.revealed = True
            self.button.config(text="Continue")
            self.info_label.config(text=f"img id: {name} (solution)")
        else:
            self.next_card()


if __name__ == "__main__":
    root = tk.Tk()

    app = FlashcardApp(
        root,
        question_folder="questions",
        answer_folder="answers"
    )

    root.mainloop()