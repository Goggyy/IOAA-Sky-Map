import os
import random
import tkinter as tk
from PIL import Image, ImageTk, ImageDraw


class FlashcardApp:
    def __init__(self, root, image_folder):
        self.root = root
        self.root.title("Constellation Flashcards")

        # ~10% smaller window (matches second program)
        self.size = 720

        self.image_folder = image_folder
        self.images = self.load_images(image_folder)

        if not self.images:
            raise ValueError("No .png images found in folder")

        # UI
        self.canvas = tk.Label(root)
        self.canvas.pack(padx=10, pady=10)

        self.label = tk.Label(root, text="", font=("Arial", 16))
        self.label.pack(pady=5)

        self.button = tk.Button(root, text="Reveal", command=self.on_button)
        self.button.pack(pady=10)

        # state
        self.current_image_path = None
        self.current_photo = None
        self.revealed = False

        self.next_card()

    # -------------------- Data loading --------------------
    def load_images(self, folder):
        return [
            os.path.join(folder, f)
            for f in os.listdir(folder)
            if f.lower().endswith(".png")
        ]

    # -------------------- Transform --------------------
    def transform_image(self, path):
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

        return img

    # -------------------- Circular mask --------------------
    def circular_mask(self, img):
        mask = Image.new("L", (self.size, self.size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, self.size, self.size), fill=255)
        img.putalpha(mask)
        return img

    # -------------------- Flashcard logic --------------------
    def next_card(self):
        self.revealed = False
        self.label.config(text="")
        self.button.config(text="Reveal")

        self.current_image_path = random.choice(self.images)

        img = self.transform_image(self.current_image_path)
        img = self.circular_mask(img)

        self.current_photo = ImageTk.PhotoImage(img)
        self.canvas.config(image=self.current_photo)

    # -------------------- Reveal --------------------
    def reveal(self):
        name = os.path.splitext(os.path.basename(self.current_image_path))[0]
        self.label.config(text=name)

        self.revealed = True
        self.button.config(text="Continue")

    # -------------------- UI handler --------------------
    def on_button(self):
        if self.revealed:
            self.next_card()
        else:
            self.reveal()


if __name__ == "__main__":
    IMAGE_FOLDER = "images"

    root = tk.Tk()
    app = FlashcardApp(root, IMAGE_FOLDER)
    root.mainloop()