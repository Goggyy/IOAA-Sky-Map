"""Reusable Tkinter application shell for every training activity."""

from __future__ import annotations

import argparse
import queue
import random
import secrets
import sys
import tkinter as tk
from concurrent.futures import Future, ThreadPoolExecutor
from tkinter import messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from .activity_api import QuestionUnavailable, SkyActivity
from .analysis_ui import AnalysisWindow
from .astronomy import CACHE_DIRECTORY, AstronomyData, SkyMapCalculator
from .models import QuestionBundle
from .random_sky import RandomSkyGenerator
from .rendering import RenderOptions, SkyMapRenderer


class ActivityApplication(tk.Tk):
    """Blind-map question flow used by all activities."""

    MAX_RANDOM_ATTEMPTS = 12

    def __init__(self, activity: SkyActivity) -> None:
        super().__init__()
        self.activity = activity
        self.title(activity.title)
        self.geometry("1160x780")
        self.minsize(900, 650)

        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="ioaa-sky-question",
        )
        self._calculator = SkyMapCalculator(AstronomyData())
        self._random_sky = RandomSkyGenerator()
        self._progress_messages: queue.SimpleQueue[str] = queue.SimpleQueue()
        self._bundle: QuestionBundle | None = None
        self._answer_revealed = False
        self._generation = 0
        self._question_count = 0

        self._build_variables()
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(150, self.new_question)

    def _build_variables(self) -> None:
        self.prompt_var = tk.StringVar(value="Generating a random blind sky…")
        self.answer_text_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Starting…")
        self.question_number_var = tk.StringVar(value="Question")

    def _build_ui(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        controls = ttk.Frame(self, padding=14)
        controls.grid(row=0, column=0, sticky="nsew")
        controls.columnconfigure(0, weight=1)

        ttk.Label(
            controls,
            text=self.activity.title,
            font=("TkDefaultFont", 15, "bold"),
            wraplength=300,
            justify="left",
        ).grid(row=0, column=0, sticky="ew")
        ttk.Label(
            controls,
            text=self.activity.description,
            wraplength=300,
            justify="left",
        ).grid(row=1, column=0, sticky="ew", pady=(5, 14))

        self.prompt_frame = ttk.LabelFrame(controls, text="Question", padding=12)
        self.prompt_frame.grid(row=2, column=0, sticky="ew")
        self.prompt_frame.columnconfigure(0, weight=1)
        prompt_frame = self.prompt_frame
        ttk.Label(
            prompt_frame,
            textvariable=self.prompt_var,
            wraplength=285,
            justify="left",
            font=("TkDefaultFont", 11, "bold"),
        ).grid(row=0, column=0, sticky="ew")
        ttk.Label(
            prompt_frame,
            textvariable=self.answer_text_var,
            wraplength=285,
            justify="left",
        ).grid(row=1, column=0, sticky="ew", pady=(9, 0))

        actions = ttk.Frame(controls)
        actions.grid(row=3, column=0, sticky="ew", pady=(14, 0))
        actions.columnconfigure(0, weight=1)

        self.reveal_button = ttk.Button(
            actions,
            text="Reveal answer",
            command=self.reveal_answer,
            state="disabled",
        )
        self.reveal_button.grid(row=0, column=0, sticky="ew")

        self.new_button = ttk.Button(
            actions,
            text="New random question",
            command=self.new_question,
            state="disabled",
        )
        self.new_button.grid(row=1, column=0, sticky="ew", pady=(7, 0))

        self.analysis_button = ttk.Button(
            actions,
            text="Analyse current sky…",
            command=self.open_analysis,
            state="disabled",
        )
        self.analysis_button.grid(row=2, column=0, sticky="ew", pady=(7, 0))

        ttk.Separator(controls).grid(row=4, column=0, sticky="ew", pady=14)
        ttk.Label(
            controls,
            textvariable=self.status_var,
            wraplength=300,
            justify="left",
        ).grid(row=5, column=0, sticky="ew")

        ttk.Label(
            controls,
            text=(
                "The question chart intentionally shows only stars and the horizon. "
                "Coordinates, directions, grids, labels, location, and time remain hidden.\n\n"
                "The chart orientation is also random, so north is not necessarily at the top.\n\n"
                "After revealing the answer, open the analysis page to toggle the full set of layers."
            ),
            wraplength=300,
            justify="left",
        ).grid(row=6, column=0, sticky="ew", pady=(14, 0))

        chart_frame = ttk.Frame(self, padding=(0, 8, 8, 8))
        chart_frame.grid(row=0, column=1, sticky="nsew")
        chart_frame.columnconfigure(0, weight=1)
        chart_frame.rowconfigure(0, weight=1)

        self.figure = Figure(figsize=(8.2, 7.2), dpi=100)
        self.renderer = SkyMapRenderer(self.figure)
        self.canvas = FigureCanvasTkAgg(self.figure, master=chart_frame)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        # Display an empty dark chart immediately while the first catalogue load runs.
        self.figure.set_facecolor(self.renderer.BACKGROUND)
        self.renderer.axes.set_facecolor(self.renderer.BACKGROUND)
        self.renderer.axes.set_axis_off()
        self.canvas.draw_idle()

        self.bind("<space>", lambda _event: self.reveal_answer())
        self.bind("<Control-n>", lambda _event: self.new_question())

    def new_question(self) -> None:
        self._generation += 1
        generation = self._generation
        self._bundle = None
        self._answer_revealed = False
        self.prompt_var.set("Generating a random blind sky…")
        self.answer_text_var.set("")
        self.status_var.set("Calculating star positions…")
        self.reveal_button.configure(state="disabled")
        self.new_button.configure(state="disabled")
        self.analysis_button.configure(state="disabled")

        while True:
            try:
                self._progress_messages.get_nowait()
            except queue.Empty:
                break

        future = self._executor.submit(self._build_random_question)
        self.after(80, lambda: self._poll_future(future, generation))

    def _build_random_question(self) -> QuestionBundle:
        seed = secrets.randbits(63)
        rng = random.Random(seed)

        for attempt in range(1, self.MAX_RANDOM_ATTEMPTS + 1):
            settings = self._random_sky.generate(rng)

            def progress(message: str) -> None:
                self._progress_messages.put(message)

            model = self._calculator.calculate(settings, progress)
            try:
                question = self.activity.create_question(model, rng)
            except QuestionUnavailable as error:
                self._progress_messages.put(
                    f"Random sky unsuitable ({error}); trying another…"
                )
                continue
            return QuestionBundle(seed=seed, model=model, question=question)

        raise RuntimeError(
            f"Could not build a suitable question after {self.MAX_RANDOM_ATTEMPTS} random skies."
        )

    def _poll_future(
        self,
        future: Future[QuestionBundle],
        generation: int,
    ) -> None:
        if generation != self._generation or not self.winfo_exists():
            return

        latest_message: str | None = None
        while True:
            try:
                latest_message = self._progress_messages.get_nowait()
            except queue.Empty:
                break
        if latest_message is not None:
            self.status_var.set(latest_message)

        if not future.done():
            self.after(80, lambda: self._poll_future(future, generation))
            return

        try:
            bundle = future.result()
        except Exception as error:
            self.status_var.set("Question generation failed.")
            self.new_button.configure(state="normal")
            messagebox.showerror(
                "Could not generate question",
                (
                    f"{type(error).__name__}: {error}\n\n"
                    "The first run requires internet access to download the Hipparcos "
                    "catalogue and Stellarium constellation data."
                ),
                parent=self,
            )
            return

        self._bundle = bundle
        self._question_count += 1
        self.prompt_var.set(bundle.question.prompt)
        self.question_number_var.set(f"Question {self._question_count}")
        self.prompt_frame.configure(text=self.question_number_var.get())
        self._draw_current_map()
        self.reveal_button.configure(state="normal")
        self.new_button.configure(state="disabled")
        self.status_var.set(
            f"Blind sky ready with {len(bundle.model.stars.hip):,} visible stars."
        )

    def _draw_current_map(self) -> None:
        if self._bundle is None:
            return
        overlay = None
        if self._answer_revealed:
            overlay = lambda renderer, model: self.activity.draw_answer(
                renderer,
                model,
                self._bundle.question,
            )
        self.renderer.draw(
            self._bundle.model,
            RenderOptions.blind(),
            answer_overlay=overlay,
        )
        self.canvas.draw_idle()

    def reveal_answer(self) -> None:
        if self._bundle is None or self._answer_revealed:
            return
        self._answer_revealed = True
        self.answer_text_var.set(self._bundle.question.answer_text)
        self.reveal_button.configure(state="disabled")
        self.new_button.configure(state="normal")
        self.analysis_button.configure(state="normal")
        self.status_var.set("Answer revealed. Generate another question or analyse this sky.")
        self._draw_current_map()

    def open_analysis(self) -> None:
        if self._bundle is None or not self._answer_revealed:
            return
        AnalysisWindow(self, self._bundle, self.activity)

    def _on_close(self) -> None:
        self._generation += 1
        self._executor.shutdown(wait=False, cancel_futures=True)
        self.destroy()


def dependency_check(activity: SkyActivity) -> int:
    print("Python:", sys.version.split()[0])
    print("Activity:", activity.title)
    print("Cache directory:", CACHE_DIRECTORY)
    print("Core imports succeeded.")
    return 0


def run_activity(activity: SkyActivity) -> int:
    parser = argparse.ArgumentParser(description=activity.description)
    parser.add_argument(
        "--check",
        action="store_true",
        help="check imports without opening a Tkinter window",
    )
    args = parser.parse_args()
    if args.check:
        return dependency_check(activity)

    app = ActivityApplication(activity)
    app.mainloop()
    return 0
