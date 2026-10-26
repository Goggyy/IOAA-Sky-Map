# Sky Map Trainer: user guide

This guide covers the PyQt6 desktop app's exercises, analysis view, map generator, coordinate converter, and settings. For installation, start with the [README](../README.md). The shorter **Help** page inside the app is available from the top bar.

## Start and navigate

Run `main.py` from the project folder as described in the README. The sidebar has **Exercises**, **Tools**, and **Settings**. Select **Start** on an exercise card or **Open** on a tool card. **Help** opens the short in-app guide. Use **← Back** above an open view to return to the previous page. The first sky calculation downloads star and constellation data, so allow extra time and an internet connection on first use; later calculations use the local cache.

The sky map is centred on the zenith. The circle at 90° coverage reaches the horizon; a larger coverage can show sky below it. The ordinary exercise map hides most reference markings so you can solve from the star pattern. Magnitude is an astronomy scale: *smaller* numbers mean brighter stars.

## Work through an exercise

1. Open an exercise and wait for the question and blind chart. The timer starts when the question is ready, not while the map is calculating.
2. Where offered, choose a **Set** or **Missing** count above the question. Changing an option generates a new question and resets the timer.
3. Solve the prompt using the map. **Reveal** shows a separate answer panel and draws that exercise's answer on the chart. It stops the timer.
4. **Hide** removes the answer panel and highlight so you can study the blind map again. The timer remains stopped after its first reveal. Press **Reveal** again whenever needed.
5. Select **Analyse** to inspect the same sky with optional reference layers, or **New** for another question. These buttons become available after the first reveal.

Press **Space** to toggle Reveal/Hide, or **Ctrl+N** for a new question. On a Mac, the app still registers the `Ctrl+N` shortcut, not `Command+N`.

Some fixed locations, times, or narrow magnitude/coverage settings leave too few suitable targets. If generation fails, loosen those settings or use random location and time, then select **New**. Changing a set also asks the app to generate a new question.

### The eight exercises

| Exercise | What to do | What Reveal shows |
| --- | --- | --- |
| **Celestial Pole and Related** | Mark the celestial equator, N/S/E/W, one celestial pole, and estimate latitude. | Equator and directions, the relevant pole, and the observer's latitude. |
| **Ecliptic** | Trace the ecliptic from the star pattern. | Highlighted ecliptic plus visible zodiac constellation diagrams and names. |
| **Find Constellation** | Locate the named constellation in the blind map. | Its highlighted line diagram. |
| **Name Constellation** | Identify the constellation in the circled area. | Its name and highlighted diagram. |
| **Name Star** | Identify the circled star by name, if it has one, and Bayer designation. | The star's identity and marked position. |
| **Name Star from Alt/Az** | Use the stated altitude and azimuth to identify a star and its Bayer designation. Cardinal directions are shown. | Its identity and marked position. Azimuth runs north → east → south → west. |
| **Estimate LST** | Estimate local sidereal time from familiar stars near the drawn meridian. | The calculated LST and up to three useful bright-star RA references. |
| **Missing Stars** | Work out which 1–7 stars were removed from an otherwise normal map. | The stars restored at their usual map size, numbered highlights, and their names and Bayer designations in the answer panel. |

**Find Constellation** and **Name Constellation** have six selectable pools: All, Zodiac, Northern Constellations, Southern Constellations, Winter Sky, and Summer Sky. The zodiac set includes Ophiuchus. The seasonal sets are study groups, not a promise that every member is visible in a particular sky. **Ecliptic** always uses the zodiac constellations for its answer.

| Set | Constellations in the pool |
| --- | --- |
| **All** | Any suitable visible constellation. |
| **Zodiac** | Aries, Taurus, Gemini, Cancer, Leo, Virgo, Libra, Scorpius, Ophiuchus, Sagittarius, Capricornus, Aquarius, Pisces. |
| **Northern Constellations** | Ursa Major, Ursa Minor, Cassiopeia, Cepheus, Draco, Boötes, Canes Venatici, Corona Borealis, Coma Berenices, Leo Minor, Camelopardalis, Lynx, Hercules, Lacerta. |
| **Southern Constellations** | Crux, Centaurus, Carina, Vela, Puppis, Dorado, Tucana, Eridanus, Musca, Triangulum Australe, Ara, Norma, Pavo, Grus, Hydrus, Octans. |
| **Winter Sky** | Orion, Taurus, Gemini, Canis Major, Canis Minor, Auriga, Perseus, Lepus, Monoceros, Eridanus, Columba, Puppis, Cancer, Cetus. |
| **Summer Sky** | Cygnus, Lyra, Aquila, Hercules, Ophiuchus, Serpens, Scutum, Sagitta, Vulpecula, Delphinus, Sagittarius, Scorpius, Corona Australis, Capricornus, Aquarius, Pegasus, Andromeda, Triangulum, Pisces. |

**Name Star**, **Name Star from Alt/Az**, and **Missing Stars** offer **Top 60** and **Extended** star sets. Extended adds familiar Bayer stars, including stars from the zodiac and other recognisable constellations. A star without a common proper name is identified by its Bayer designation. **Missing Stars** also has a **Missing** dropdown from 1 to 7; its selection tries to include bright stars rather than only faint ones.

## Analyse a revealed sky

Open **Analyse** after revealing an exercise answer. This view keeps that question's location, time, chart, and answer text. Its left panel separates **Question** from **Answer** and shows the sky's latitude, longitude, UTC time, LST, map rotation, and random seed under **Revealed sky**.

Use **Layers** to switch on only the references you need:

| Control | Adds to the chart |
| --- | --- |
| Directions; Alt/Az grid | Cardinal labels; horizontal coordinate grid. |
| RA/Dec grid | Equatorial coordinate grid. |
| Ecliptic; Celestial equator; Galactic equator | The named reference curves. |
| Constellations; Constellation names | Line diagrams; names. |
| Star names | Labels for selected bright stars. |
| Solar system; Solar labels | Visible Sun, Moon, and planets; their labels separately. Turn on **Solar system** to see the objects. |
| Zenith; Details | Zenith marker; observation information on the chart. |
| Answer | The exercise's answer highlight. |

The **Stars → Magnitude limit** slider can hide fainter stars from this already calculated sky. It cannot reveal stars fainter than the question's original limit. Layers begin off, except that **Solar system** follows the setting used for the question. The analysis toolbar provides standard chart navigation. **Save PNG…** exports the current chart with its selected layers; inspect the image before sharing it and keep the data credits in mind. Use **← Back** to return to the exercise.

## Sky Map Generator

Open **Tools → Sky Map Generator** to make a labelled or unlabelled map for a chosen position and time. The chart is calculated on opening and recalculates shortly after you edit observation inputs. Wait for its status to finish before saving. The left panel has **Observation**, **Layers**, and **View** tabs.

### Observation: observer and time

Leave **Position** on **Observer + time** to enter latitude and longitude, or click the small world map under **Pick location**. **Expand map** opens a larger picker. North and east are positive; south and west are negative. The displayed time zone follows the selected coordinates, not your computer's location.

The **Time** menu offers:

- **UTC date/time:** Enter a UTC date (`YYYY-MM-DD`) and 24-hour time (`HH:MM:SS`).
- **Local date/time:** Enter civil time at the selected coordinates. The app finds that place's time zone and applies daylight-saving rules before calculating the sky. If a clock time is ambiguous or nonexistent at a daylight-saving change, choose another time or enter UTC.
- **LST + UTC date:** Enter an LST in hours or `HH:MM:SS`, plus a UTC reference date. The selected longitude is used to find a matching UTC instant.
- **MJD:** Enter a Modified Julian Date.

Switching between UTC and local time converts the entered date/time so it represents the same instant. Review the fields after switching, especially if you changed location. The **Details** box reports the resolved coordinates, UTC, MJD, LST, and rotation.

### Observation: direct zenith

Choose **Direct zenith** to centre the chart on an RA/Dec position without picking an Earth location. Use the celestial-sphere control, enter exact RA and Dec then select **Apply**, or click/drag the chart to reposition its centre. The UTC date helps resolve the calculation. This is a way to choose the map's centre, not a separate set of observer coordinates. The chart preview may update while dragging; allow the final calculation to finish afterward.

The mouse wheel or trackpad gesture over the chart changes sky coverage. You can also set coverage precisely in **View**.

### Layers and view

The **Layers** tab offers directions, Alt/Az and RA/Dec grids, the ecliptic and equators, constellation lines and names, star names, solar-system objects and their separate labels, zenith, and details. **All off** clears these layers; **Study view** switches them all on. The Solar system switch controls whether object dots are shown; **Solar labels** controls their text. Saved exercise settings provide the initial solar-object choice when the generator opens.

The **View** tab controls inverted colours, coverage from the zenith, magnitude limit, marker size, and chart rotation. At **90°**, coverage reaches the horizon; **180°** displays the full sphere. A lower magnitude limit keeps only brighter stars. Marker size changes how large the plotted star dots look. **Rotate map** enables the angle control; **North up** sets it to zero, and **Random** chooses an angle. Changes to layers and view generally redraw the existing calculated sky without a new observation calculation. Night mode follows the saved app setting.

When the map is ready, select **Save PNG…**. This saves the current view, including whichever layers are visible. The generator's toolbar also provides chart navigation. The file is an image, not a saved editable observation.

## Coordinate Converter

Open **Tools → Coordinate Converter**. Choose **RA / Dec → Alt / Az** to enter latitude, right ascension, declination, and either LST or hour angle. Choose **Alt / Az → RA / Dec** to enter latitude, altitude, azimuth, and either LST or RA. Results update after a short pause while you type; the status text reports incomplete or invalid input.

RA, LST, and hour angle use hours; latitude, declination, altitude, and azimuth use degrees. You can enter decimal values or colon-separated hours/degrees, minutes, and seconds. Azimuth is measured from north through east: N=0°, E=90°, S=180°, W=270°. Positive hour angle is west of the meridian. The celestial-sphere diagram shows the P–Z–★ triangle for the entered values. **Copy** places available values on the clipboard; **Clear** empties the fields. The two tabs share their values.

## Settings for exercises

Open **Settings** in the sidebar, adjust the controls, then select **Save**. **Reset** restores defaults in the form; select **Save** again to keep them. Newly opened exercises load the saved settings. An exercise that is already open keeps the settings it started with, including for its next question. Opening an exercise or tool also saves the currently entered settings, and invalid fields produce an error.

- **Location:** Random, or fixed latitude and longitude in degrees. Valid ranges are −90° to +90° latitude and −180° to +180° longitude.
- **Time:** Random, fixed UTC, fixed LST with a date, or fixed MJD. The visible fields depend on the mode. Settings use UTC rather than a local-time input; local time is available in the generator.
- **Sun, Moon and planets:** Adds visible solar-system dots to exercise maps. Analysis and the generator initialise their solar-object switch from this setting. Solar labels are a separate layer.
- **Invert colours:** Switches chart colours. **Night mode** changes the interface and charts to a red observing palette.
- **Random rotation:** Rotates new exercise charts by a random angle. Switch it off for a consistent orientation.
- **Coverage:** Angular distance from zenith, 0°–180°; 90° is the horizon.
- **Magnitude limit:** Faintest plotted stars, −1.5 to 8.0. The default is 5.5.
- **Star size:** Scales marker size without changing which stars qualify.

Settings and downloaded catalogues live under `~/.ioaa_sky_trainer`, outside the app folder. Deleting this directory also removes your saved settings and means the large catalogues must be downloaded again. The generator's temporary layer and view changes do not replace the saved exercise settings.

## If something does not work

- **No sky appears on first use:** Check the internet connection and wait for the catalogue downloads. The next calculation should use cached files.
- **No suitable question:** Choose a wider coverage or fainter magnitude limit, or return location/time to Random. A small set and a fixed sky can leave no eligible target.
- **Unexpected local time:** Check the selected latitude/longitude and displayed time zone. Use UTC near a daylight-saving transition.
- **Installation fails:** Check that the terminal is in the folder containing `requirements.txt` and that the environment's Python installed its dependencies as shown in the README.

For code, catalogue, and map-data licences, see [Third-party notices](../THIRD_PARTY_NOTICES.md). In particular, ESA's Hipparcos data carries a noncommercial licence and requests **Credit: ESA**.
