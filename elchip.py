import os
import random
import threading
import sys
import tkinter as tk
from tkinter import messagebox

try:
    import pygame
except ImportError:
    pygame = None

from PIL import Image, ImageTk
import pystray


class ElChipApp:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.image_paths = [
            os.path.join(self.base_dir, f"elchip{i}.png") for i in (1, 2, 3)
        ]
        self.sound_path = os.path.join(self.base_dir, "elchip.mp3")
        self.slug = "ElChip UCN"
        self.difficulty = 1
        self.overlay = None
        self.stop_event = threading.Event()
        self.audio_available = False

        self._load_image()
        self._init_audio()
        self._create_tk_root()
        self._create_tray_icon()

    def _load_image(self):
        missing = [path for path in self.image_paths if not os.path.exists(path)]
        if missing:
            raise FileNotFoundError(
                f"Could not find overlay image(s) in {self.base_dir}: {', '.join(os.path.basename(p) for p in missing)}."
            )

        base_image = Image.open(self.image_paths[0])
        self.overlay_image = None
        self.overlay_photo = None
        self.icon_image = base_image.copy()
        self.icon_image.thumbnail((64, 64), Image.LANCZOS)

    def _init_audio(self):
        if pygame is None or not os.path.exists(self.sound_path):
            return

        try:
            pygame.mixer.init()
            pygame.mixer.music.load(self.sound_path)
            self.audio_available = True
        except Exception:
            self.audio_available = False

    def _select_overlay_image(self):
        chosen_path = random.choice(self.image_paths)
        return Image.open(chosen_path)

    def _create_tk_root(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)

    def _create_tray_icon(self):
        menu = pystray.Menu(
            pystray.MenuItem(
                "Difficulty",
                pystray.Menu(*[pystray.MenuItem(
                    str(level),
                    lambda *args, level=level: self.set_difficulty(level),
                    checked=lambda *args, level=level: self.difficulty == level,
                ) for level in range(1, 21)]),
            ),
            pystray.MenuItem("Show now", lambda *args: self.show_overlay()),
            pystray.MenuItem("Exit", lambda *args: self.on_exit()),
        )

        self.tray_icon = pystray.Icon(
            "elchip",
            self.icon_image,
            self.slug,
            menu,
        )

    def set_difficulty(self, level):
        self.difficulty = level
        if self.tray_icon:
            self.tray_icon.title = f"{self.slug} - Difficulty {level}"

    def show_overlay(self):
        if self.overlay is not None:
            return

        image = self._select_overlay_image()

        self.overlay = tk.Toplevel(self.root)
        self.overlay.overrideredirect(True)
        self.overlay.attributes("-topmost", True)
        self.overlay.configure(background="black")

        screen_width = self.overlay.winfo_screenwidth()
        screen_height = self.overlay.winfo_screenheight()
        self.overlay.geometry(f"{screen_width}x{screen_height}+0+0")

        image = image.resize((screen_width, screen_height), Image.LANCZOS)
        self.overlay_photo = ImageTk.PhotoImage(image)

        self._play_sound()

        self.overlay.bind("<Button-1>", self.on_overlay_click)
        self.overlay.bind("<Escape>", self.on_overlay_click)

        label = tk.Label(self.overlay, image=self.overlay_photo, bg="black")
        label.pack(expand=True, fill="both")
        label.bind("<Button-1>", self.on_overlay_click)

        self.overlay.after(60000, self._auto_close_overlay)

        # Prevent the overlay window from stealing focus permanently
        self.overlay.focus_force()

    def on_overlay_click(self, event=None):
        if self.overlay is not None:
            self.overlay.destroy()
            self.overlay = None
            self.overlay_photo = None
            if self.audio_available:
                try:
                    pygame.mixer.music.stop()
                except Exception:
                    pass

    def _auto_close_overlay(self):
        if self.overlay is not None:
            self.on_overlay_click()

    def _play_sound(self):
        if not self.audio_available:
            return

        try:
            pygame.mixer.music.play()
        except Exception:
            pass

    def run(self):
        tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        tray_thread.start()

        self.root.after(1000, self._run_random_overlay)
        self.root.mainloop()
        self.stop_event.set()

    def _run_random_overlay(self):
        if self.stop_event.is_set():
            return

        if self.overlay is None:
            probability = min(max(self.difficulty / 40.0, 0.025), 0.5)
            if random.random() < probability:
                self.show_overlay()

        interval = random.randint(800, 1800)
        self.root.after(interval, self._run_random_overlay)

    def on_exit(self, event=None):
        if messagebox.askokcancel("Exit", "Do you want to close ElChip?"):
            if self.tray_icon:
                try:
                    self.tray_icon.stop()
                except Exception:
                    pass
            self.stop_event.set()
            if self.root:
                self.root.quit()
            sys.exit(0)


if __name__ == "__main__":
    try:
        app = ElChipApp()
        app.run()
    except Exception as exc:
        print("Error: ", exc)
        sys.exit(1)
