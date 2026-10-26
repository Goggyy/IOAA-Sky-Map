"""Reusable PyQt6 application shell for every training exercise."""

from __future__ import annotations

import argparse
import random
import secrets
import sys
import time
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Callable

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QFrame, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from .activity_api import QuestionUnavailable, SkyActivity
from .analysis_ui import AnalysisWindow
from .astronomy import CACHE_DIRECTORY, AstronomyData, SkyMapCalculator
from .generation_settings import load_generation_settings
from .models import QuestionBundle
from .random_sky import RandomSkyGenerator
from .rendering import RenderOptions, SkyMapRenderer
from .theme import apply_night_theme


class ActivityApplication(QWidget):
    """Blind-map question flow used by all exercises."""

    MAX_RANDOM_ATTEMPTS = 12

    def __init__(
        self,
        activity: SkyActivity,
        *,
        analysis_navigator: Callable[[QuestionBundle, SkyActivity], None] | None = None,
    ) -> None:
        super().__init__()
        self.activity = activity
        self._analysis_navigator = analysis_navigator
        self.setWindowTitle(activity.title)
        self.resize(1180, 780); self.setMinimumSize(880, 620)
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ioaa-sky-question")
        self._calculator = SkyMapCalculator(AstronomyData())
        self._generation_settings = load_generation_settings()
        self._random_sky = RandomSkyGenerator(generation_settings=self._generation_settings)
        self._bundle: QuestionBundle | None = None
        self._answer_revealed = False; self._answer_seen = False; self._generation = 0; self._question_count = 0
        self._timer_started_at: float | None = None; self._timer_elapsed_seconds = 0.0
        self._future: Future[QuestionBundle] | None = None; self._future_generation = 0
        self._analysis_windows: list[AnalysisWindow] = []
        self._build_ui(); apply_night_theme(self, self._generation_settings.night_mode)

        self._generation_poll = QTimer(self); self._generation_poll.setInterval(80); self._generation_poll.timeout.connect(self._poll_future)
        self._exercise_timer = QTimer(self); self._exercise_timer.setInterval(100); self._exercise_timer.timeout.connect(self._update_timer)
        reveal_action = QAction(self); reveal_action.setShortcut(QKeySequence("Space")); reveal_action.triggered.connect(self.reveal_answer); self.addAction(reveal_action)
        new_action = QAction(self); new_action.setShortcut(QKeySequence("Ctrl+N")); new_action.triggered.connect(self.new_question); self.addAction(new_action)
        QTimer.singleShot(150, self.new_question)

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self); layout.setContentsMargins(12,12,12,12); layout.setSpacing(12)
        panel = QFrame(); panel.setObjectName("Card"); panel.setFixedWidth(290)
        pl = QVBoxLayout(panel); pl.setContentsMargins(16,16,16,16); pl.setSpacing(12)
        title = QLabel(self.activity.title); title.setObjectName("PageTitle"); title.setWordWrap(True); pl.addWidget(title)
        self.option_combos: dict[str, QComboBox] = {}
        for option in self.activity.activity_options:
            option_row = QHBoxLayout()
            option_row.addWidget(QLabel(option.label))
            combo = QComboBox()
            for key, label in option.choices:
                combo.addItem(label, key)
            selected = self.activity.selected_option(option.key)
            selected_index = combo.findData(selected)
            combo.setCurrentIndex(max(0, selected_index))
            self.activity.set_option(option.key, str(combo.currentData()))
            combo.currentIndexChanged.connect(
                lambda _index, key=option.key: self._activity_option_changed(key)
            )
            option_row.addWidget(combo, 1)
            pl.addLayout(option_row)
            self.option_combos[option.key] = combo

        question_card = QFrame(); question_card.setObjectName("Card"); ql = QVBoxLayout(question_card)
        self.question_heading = QLabel("Question"); self.question_heading.setObjectName("SectionTitle"); ql.addWidget(self.question_heading)
        self.prompt_label = QLabel("Generating a random blind sky…"); self.prompt_label.setWordWrap(True); self.prompt_label.setObjectName("QuestionText"); ql.addWidget(self.prompt_label)
        self.timer_label = QLabel("Time: 00:00.0"); self.timer_label.setObjectName("Muted"); ql.addWidget(self.timer_label)
        pl.addWidget(question_card)

        self.answer_card = QFrame(); self.answer_card.setObjectName("Card")
        al = QVBoxLayout(self.answer_card)
        answer_heading = QLabel("Answer"); answer_heading.setObjectName("SectionTitle"); al.addWidget(answer_heading)
        self.answer_label = QLabel(""); self.answer_label.setWordWrap(True); al.addWidget(self.answer_label)
        self.answer_card.setVisible(False); pl.addWidget(self.answer_card)

        self.reveal_button = QPushButton("Reveal"); self.reveal_button.setProperty("primary", True); self.reveal_button.clicked.connect(self.reveal_answer); self.reveal_button.setEnabled(False); pl.addWidget(self.reveal_button)
        self.new_button = QPushButton("New"); self.new_button.clicked.connect(self.new_question); self.new_button.setEnabled(False); pl.addWidget(self.new_button)
        self.analysis_button = QPushButton("Analyse"); self.analysis_button.clicked.connect(self.open_analysis); self.analysis_button.setEnabled(False); pl.addWidget(self.analysis_button)
        pl.addStretch(1)
        layout.addWidget(panel)

        chart = QFrame(); chart.setObjectName("Card"); cl = QVBoxLayout(chart); cl.setContentsMargins(8,8,8,8)
        self.figure = Figure(figsize=(8.2,7.2), dpi=100); self.renderer = SkyMapRenderer(self.figure); self.renderer.set_night_mode(self._generation_settings.night_mode)
        self.canvas = FigureCanvasQTAgg(self.figure); self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding); cl.addWidget(self.canvas,1)
        self.figure.set_facecolor(self.renderer.BACKGROUND); self.renderer.axes.set_facecolor(self.renderer.BACKGROUND); self.renderer.axes.set_axis_off(); self.canvas.draw_idle()
        layout.addWidget(chart,1)

    def new_question(self) -> None:
        self._stop_timer(); self._timer_elapsed_seconds = 0.0; self.timer_label.setText("Time: 00:00.0")
        self._generation += 1; generation = self._generation; self._bundle = None; self._answer_revealed = False; self._answer_seen = False
        self.prompt_label.setText("Generating a random blind sky…"); self.answer_label.setText(""); self.answer_label.setMinimumHeight(0); self.answer_card.setVisible(False)
        self.reveal_button.setText("Reveal"); self.reveal_button.setEnabled(False); self.new_button.setEnabled(False); self.analysis_button.setEnabled(False)
        for combo in self.option_combos.values(): combo.setEnabled(False)
        self._future = self._executor.submit(self._build_random_question); self._future_generation = generation; self._generation_poll.start()

    def _build_random_question(self) -> QuestionBundle:
        seed = secrets.randbits(63); rng = random.Random(seed)
        for _attempt in range(1, self.MAX_RANDOM_ATTEMPTS+1):
            settings = self._random_sky.generate(rng)
            model = self._calculator.calculate(settings)
            try: question = self.activity.create_question(model, rng)
            except QuestionUnavailable:
                continue
            return QuestionBundle(seed=seed, model=model, question=question)
        raise RuntimeError(f"Could not build a suitable question after {self.MAX_RANDOM_ATTEMPTS} random skies.")

    def _poll_future(self) -> None:
        if self._future_generation != self._generation or self._future is None:
            self._generation_poll.stop(); return
        if not self._future.done(): return
        self._generation_poll.stop()
        try: bundle = self._future.result()
        except Exception as error:
            self.new_button.setEnabled(True)
            for combo in self.option_combos.values(): combo.setEnabled(True)
            QMessageBox.critical(self, "Could not generate question", f"{type(error).__name__}: {error}\n\nThe first run requires internet access to download the Hipparcos catalogue and Stellarium constellation data.")
            return
        self._bundle = bundle; self._question_count += 1; self.prompt_label.setText(bundle.question.prompt); self.question_heading.setText(f"Question {self._question_count}")
        self._draw_current_map(); self._start_timer(); self.reveal_button.setEnabled(True); self.new_button.setEnabled(False)
        for combo in self.option_combos.values(): combo.setEnabled(True)

    def _activity_option_changed(self, option_key: str) -> None:
        combo = self.option_combos[option_key]
        self.activity.set_option(option_key, str(combo.currentData()))
        self.new_question()

    def _draw_current_map(self) -> None:
        if self._bundle is None: return
        def overlay(renderer: SkyMapRenderer, model) -> None:
            self.activity.draw_question(renderer, model, self._bundle.question)
            if self._answer_revealed: self.activity.draw_answer(renderer, model, self._bundle.question)
        self.renderer.draw(
            self._bundle.model,
            RenderOptions(
                show_solar_system_objects=self._bundle.model.settings.include_solar_system_objects,
                hidden_star_hips=(
                    frozenset()
                    if self._answer_revealed
                    else self.activity.hidden_star_hips(self._bundle.question)
                ),
            ),
            answer_overlay=overlay,
        )
        self.canvas.draw_idle()

    def reveal_answer(self) -> None:
        if self._bundle is None: return
        if self._answer_revealed:
            self._answer_revealed = False
            self.answer_label.setText("")
            self.answer_label.setMinimumHeight(0)
            self.answer_card.setVisible(False)
            self.reveal_button.setText("Reveal")
            self._draw_current_map()
            return

        self._answer_revealed = True
        if not self._answer_seen:
            self._answer_seen = True
            self._stop_timer()
            self.new_button.setEnabled(True)
            self.analysis_button.setEnabled(True)
        self.answer_label.setText(self._bundle.question.answer_text)
        answer_lines = self._bundle.question.answer_text.count("\n") + 1
        self.answer_label.setMinimumHeight(min(180, answer_lines * 18))
        self.answer_card.setVisible(True)
        self.reveal_button.setText("Hide")
        self._draw_current_map()

    @staticmethod
    def _format_elapsed(seconds: float) -> str:
        tenths=max(0,int(round(seconds*10))); minutes,rem=divmod(tenths,600); secs,tenth=divmod(rem,10)
        if minutes>=60: hours,minutes=divmod(minutes,60); return f"{hours:d}:{minutes:02d}:{secs:02d}.{tenth}"
        return f"{minutes:02d}:{secs:02d}.{tenth}"

    def _start_timer(self) -> None:
        self._stop_timer(); self._timer_elapsed_seconds=0.0; self._timer_started_at=time.perf_counter(); self._update_timer(); self._exercise_timer.start()

    def _update_timer(self) -> None:
        if self._timer_started_at is None or self._answer_revealed: return
        self._timer_elapsed_seconds=time.perf_counter()-self._timer_started_at; self.timer_label.setText(f"Time: {self._format_elapsed(self._timer_elapsed_seconds)}")

    def _stop_timer(self) -> None:
        self._exercise_timer.stop() if hasattr(self, "_exercise_timer") else None
        if self._timer_started_at is not None:
            self._timer_elapsed_seconds=time.perf_counter()-self._timer_started_at; self._timer_started_at=None; self.timer_label.setText(f"Time: {self._format_elapsed(self._timer_elapsed_seconds)}")

    def open_analysis(self) -> None:
        if self._bundle is None or not self._answer_seen:
            return
        if self._analysis_navigator is not None:
            self._analysis_navigator(self._bundle, self.activity)
            return
        # Directly launched exercise modules retain a standalone analysis view.
        # The main launcher supplies ``analysis_navigator`` and therefore keeps
        # this view inside the existing application window.
        window = AnalysisWindow(
            self,
            self._bundle,
            self.activity,
            night_mode=self._generation_settings.night_mode,
        )
        window.setWindowFlag(Qt.WindowType.Window, True)
        self._analysis_windows.append(window)
        window.destroyed.connect(
            lambda _obj=None, w=window: self._analysis_windows.remove(w)
            if w in self._analysis_windows else None
        )
        window.show()

    def closeEvent(self, event) -> None:  # noqa: N802
        self._stop_timer(); self._generation += 1; self._generation_poll.stop(); self._executor.shutdown(wait=False, cancel_futures=True); event.accept()


def dependency_check(activity: SkyActivity) -> int:
    print("Python:", sys.version.split()[0]); print("UI: PyQt6"); print("Exercise:", activity.title); print("Cache directory:", CACHE_DIRECTORY); print("Core imports succeeded."); return 0


def run_activity(activity: SkyActivity) -> int:
    parser=argparse.ArgumentParser(description=activity.description); parser.add_argument("--check", action="store_true", help="check imports without opening a PyQt6 window"); args=parser.parse_args()
    if args.check: return dependency_check(activity)
    app=QApplication.instance() or QApplication(sys.argv); window=ActivityApplication(activity); window.show(); return app.exec()
