# Cyber Radio v2.0 Roadmap

## Milestone 1: Dynamic Album Art Lookup
**Goal:** Automatically display high-quality album art for the currently playing track, even for generic radio stations that only provide "Artist - Title" metadata.

**Technical Approach:**
*   **Service:** Create a `src/core/metadata_service.py`.
*   **API:** Use the iTunes Search API (no authentication required) as a primary source.
    *   Endpoint: `https://itunes.apple.com/search?term={query}&entity=song&limit=1`
*   **Fallback:** If no art is found, fall back to the Station Logo.
*   **Caching:** Cache results in memory (or disk) to prevent repeated API calls for the same song.

## Milestone 2: Custom Station Logos
**Goal:** Allow users to assign their own images to custom stations.

**Technical Approach:**
*   **UI Update:** Modify `AddStationDialog` (in `src/ui/dialogs.py`) to include an "Image URL" field or a "File Chooser" button.
*   **Storage:** 
    *   If a URL is provided: Save strictly the URL.
    *   If a local file is chosen: Copy the image to `~/.config/CyberRadio/user_icons/` to ensure persistence.
*   **Data Structure:** Update `cyber_favorites.json` schema. The logic already handles `favicon` fields, so this is mostly a UI and file-handling task.

## Milestone 3: Reactive Synthwave Background
**Goal:** Replace the static background with a dynamic, blurred spectrogram that reacts to the music in real-time.

**Technical Approach:**
*   **Audio Capture (Robust):**
    *   Use `sounddevice` and `numpy` to capture real-time audio from the system's "Monitor" source.
    *   *Dependencies:* `python-numpy`, `python-sounddevice`, `portaudio` (system package).
    *   *Configuration:* Add a setting to allow the user to select the input device (e.g., "Monitor of Analog Stereo" vs "Microphone").
*   **Signal Processing:**
    *   Perform real-time FFT (Fast Fourier Transform) using `numpy.fft` to break the audio signal into frequency bins (Bass, Mids, Highs).
    *   Apply smoothing algorithms (EMA - Exponential Moving Average) to prevent jittery visuals.
*   **Visuals:**
    *   Implement a `ReactiveBackground` widget (subclassing `Gtk.DrawingArea`).
    *   Map low frequencies to large, slow-moving bottom shapes (Bass).
    *   Map high frequencies to shimmering top particles (Treble).
    *   Use `Gtk.Overlay` to place this widget behind the main content.
