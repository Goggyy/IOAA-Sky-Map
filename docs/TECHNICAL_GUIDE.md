# Technical guide: app structure and extension

This is a short guide to the application around the sky-map calculations. The [sky map technical guide](SKY_MAP_TECHNICAL_GUIDE.md) is reserved for the author.

## Entry points and layout

- `main.py` starts the PyQt6 launcher, discovers exercises and tools, and hosts their views. `python main.py --check` checks imports and discovery without opening a window.
- `activities/activity_*.py` contains exercise classes. `tools/tool_*.py` contains tool metadata and view factories. The `*.py.example` files in those folders are starting templates.
- `ioaa_trainer/activity_ui.py` handles the shared question, timer, answer, and analysis workflow. `analysis_ui.py`, `generator_ui.py`, and `coordinate_converter_ui.py` implement their named views. `help_ui.py` renders `HELP.md` inside the app.
- `ioaa_trainer/activity_api.py`, `tool_api.py`, and `models.py` define the interfaces and shared data types. `widgets.py` and `theme.py` hold shared UI helpers.
- `requirements.txt` lists Python dependencies. `run_macos_linux.sh` and `run_windows.bat` provide optional launchers; `sky_map_generator.py` is a direct launcher for the generator.

## Settings and local files

`generation_settings.py` validates and saves exercise generation settings in `~/.ioaa_sky_trainer/generation_settings.json`. `random_sky.py` turns those settings into a question's observer, time, and view. `local_time.py` finds a civil time zone for coordinates. Astronomy catalogue downloads are cached in the same user directory, outside the source tree. Do not commit that cache or a `.venv` directory.

## Adding an exercise

1. Copy `activities/activity_template.py.example` to a new file named `activity_your_topic.py`.
2. Give its `SkyActivity` subclass a unique `activity_id`, title, and description. Implement `create_question()` and `draw_answer()`. Return an `ActivityQuestion` with prompt, answer text, and any target data needed later.
3. Optionally implement `draw_question()` for a blind-map marker, `hidden_star_hips()` for a missing-star question, or `activity_options` for dropdowns. Raise `QuestionUnavailable` when the current sky has no suitable target; the shared workflow will try another sky.
4. Export the class as `ACTIVITY_CLASS`. Run `python main.py --check` to confirm discovery, then test the question, reveal/hide, and analysis flow in the app.

The constellation selector is defined in `activities/activity_constellation.py`; the bright-star pools are in `ioaa_trainer/star_sets.py`.

## Adding a tool

Copy `tools/tool_template.py.example` to `tool_your_tool.py`. Define a `SkyTool` subclass with a unique `tool_id`, title, and description, export it as `TOOL_CLASS`, and implement `create_widget()` to return a Qt widget for the launcher's navigation stack. A separate `run_tool()` can support direct launch. Check discovery with `python main.py --check` and open the tool from the app.

## Documentation and distribution

`README.md` is the short project entry point; `docs/USER_GUIDE.md` covers operation; `ioaa_trainer/HELP.md` is the brief in-app help. `LICENSE`, `LICENSE-MIT-legacy`, and `THIRD_PARTY_NOTICES.md` record code and data terms. Review these notices before bundling downloaded catalogues or distributing executables.
