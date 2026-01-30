# Cyber Radio Hyprland Integration

This document provides configuration examples for integrating Cyber Radio with the Hyprland desktop environment.

## 1. Dedicated "Music" Scratchpad

To have Cyber Radio appear on a dedicated "special" workspace that you can toggle with a keybinding, add the following to your `~/.config/hypr/hyprland.conf`:

```ini
# hyprland.conf

# 1. Define the CyberRadio scratchpad
# This rule moves the Cyber Radio window to a special workspace named "music".
windowrulev2 = workspace special:music, class:^(com.example.CyberRadio)$

# 2. Bind a key to toggle the scratchpad
# Pressing SUPER + M will now toggle the Cyber Radio window.
bind = SUPER, M, togglespecialworkspace, music
```

## 2. Global Media Keybindings

You can control Cyber Radio's playback from anywhere in Hyprland using your media keys. Add the following to your `hyprland.conf`:

```ini
# hyprland.conf

# Media keybindings for Cyber Radio
bind = , XF86AudioPlay, exec, python3 ~/Apps/CyberRadio/native_radio.py --play-pause
bind = , XF86AudioNext, exec, python3 ~/Apps/CyberRadio/native_radio.py --next-station
bind = , XF86AudioPrev, exec, python3 ~/Apps/CyberRadio/native_radio.py --prev-station
```
*Note: Adjust the path `~/Apps/CyberRadio/native_radio.py` if you have installed the application in a different location.*

## 3. Waybar / Status Bar Integration

To display the currently playing song in your Waybar status bar, add the following `custom` module to your `~/.config/waybar/config`:

```json
// waybar/config
"custom/now-playing": {
    "format": " {}",
    "return-type": "json",
    "exec": "cat ~/.config/CyberRadio/now_playing.txt",
    "on-click": "hyprctl dispatch togglespecialworkspace music",
    "escape": true
}
```
This module will display the content of the `now_playing.txt` file that Cyber Radio generates. Clicking on the module will toggle the Cyber Radio window.

## 4. Theming and Transparency

The application now features a dedicated **"Hyprland Kath Ricer"** aesthetic out of the box. This includes:

*   **Catppuccin Mocha-inspired Palette:** Deep dark blues, soft pastels (Pink, Mauve, Sky Blue).
*   **Floating Gaps Layout:** The sidebar and player panels now float with gaps (`10px`) and rounded corners (`16px`), mimicking the tiling window manager "gaps" aesthetic.
*   **Nerd Fonts:** The UI defaults to `JetBrainsMono Nerd Font` (or `FiraCode`) for that authentic terminal vibe.
*   **Pill Styling:** List items and buttons feature rounded "pill" styling with subtle hover effects.
*   **Translucency:** Optimized for Hyprland's blur (try `decoration:blur = true` in your `hyprland.conf`).
*   **Enhanced Visuals:** The "Vector Cat" visualization now features:
    *   Smoother animations (bouncier tail, happy eyes).
    *   A heart/note particle system when playing.
    *   Dynamic "uwu" blinking logic.

No further configuration is needed to enable this theme; it is now the default. Ensure your compositor supports transparency for the best effect.
