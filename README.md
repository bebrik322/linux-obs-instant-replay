# linux-obs-instant-replay
A script and guide to replicate NVIDIA ShadowPlay's 'Instant Replay' feature on Linux using OBS Studio, obs-cmd, and global hotkeys. It uses OBS Studio for hardware-accelerated recording, an `obs-cmd` utility to control it, and a Python script to tie everything together. Pressing the hotkey will automatically launch OBS (if not running) and save the last N seconds of your screen.

## Requirements

*   **OBS Studio**
*   **`obs-cmd`**: A command-line tool to control OBS.
*   **Python**
*   **KDE Plasma** (for the global hotkey instructions).

## 1. Installation & Dependencies

1.  **Install OBS Studio** :
    ```bash
    flatpak install flathub com.obsproject.Studio
    ```

2.  **Install `obs-cmd`**:
    *For Arch:*
    ```bash
    yay -S obs-cmd
    ```

## 2. Configuration

### Configure OBS Studio

1.  **Enable WebSocket Server**:
    *   Go to `Tools -> WebSocket Server Settings`.
    *   Check **Enable WebSocket Server**.
    *   You can disable authentication for simplicity. The default port is `4455`.

2.  **Enable Replay Buffer**:
    *   Go to the **Replay Buffer** tab.
    *   Check **Enable Replay Buffer**.
    *   Set the **Maximum Replay Time** (e.g., 60 seconds).

3.  **Set Hardware Encoder**:
    *   Go to the **Recording** tab.
    *   Set your hardware encoder.


After configuring, **you must manually click "Start Replay Buffer"** in the main OBS window once to initialize it. The script will handle this on subsequent uses if OBS is closed.

### Set up the Script & Hotkey

1.  **Place the Script**:
    *   Save the `obs.py` script and add it to autostart

2.  **Create Global Hotkey in KDE Plasma**:
    *   Go to `System Settings -> Keyboard -> Shortcuts -> Add New`.
    *   Click `Command or Script`, add command:
    ```bash
        obs-cmd replay save
    ```
    *   Set your desired hotkey (e.g., `Alt+F10`).

## 3. Usage

Simply press your configured global hotkey (e.g.,`Alt+F10`) to save the replay. The video file will appear in the recording path you specified in the OBS settings.
