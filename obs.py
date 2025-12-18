#!/usr/bin/python
import subprocess
import threading
import time
import logging
import os
from pathlib import Path

# --- Configuration ---
OBS_FLATPAK_COMMAND = ["flatpak", "run", "com.obsproject.Studio", "--disable-shutdown-check"]
OBS_CMD_CHECK_COMMAND = ["obs-cmd", "info"]
OBS_CMD_TOGGLE_COMMAND = ["obs-cmd", "replay", "toggle"]

MAX_WAIT_TIME_SECONDS = 60
CHECK_INTERVAL_SECONDS = 1

OBS_SENTINEL_PATH = Path.home() / ".var/app/com.obsproject.Studio/config/obs-studio/.sentinel"
# ---------------------

# --- Logger Setup ---
# Configure logger to output to console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(threadName)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)
# --------------------

# Global variable to store the OBS process
obs_process = None

def clean_sentinel_files():
    """
    Deletes 'run_*' files from .sentinel folder before the start.
    This prevents 'Safe Mode' window from appearing on start.
    """
    try:
        if OBS_SENTINEL_PATH.exists():
            logger.info(f"Check crash markers in: {OBS_SENTINEL_PATH}")
            for item in OBS_SENTINEL_PATH.iterdir():
                if item.is_file() and item.name.startswith("run_"):
                    logger.info(f"Deleting old startup markers: {item.name}")
                    item.unlink()
        else:
            logger.debug("Folder .sentinel not found, skipping deletion.")
    except Exception as e:
        logger.error(f"Error when deleting .sentinel: {e}")

def run_obs_in_thread():
    """
    Runs OBS Studio in a separate process.
    This function is intended to be run in a separate thread.
    """
    global obs_process

    clean_sentinel_files()

    logger.info(f"Attempting to start OBS Studio with: {' '.join(OBS_FLATPAK_COMMAND)}")
    try:
        obs_process = subprocess.Popen(OBS_FLATPAK_COMMAND)
        logger.info(f"OBS Studio process started with PID: {obs_process.pid}. It will continue running after this script exits.")
    except FileNotFoundError:
        logger.error("Error: 'flatpak' command not found. Is Flatpak installed and in your PATH?")
        # obs_process will remain None, handled by main thread
    except Exception as e:
        logger.error(f"An error occurred while trying to start OBS: {e}")
        # obs_process might be None or an invalid Popen object if an error occurred during Popen itself

def is_obs_responsive():
    """
    Checks if OBS (via obs-websocket) is responsive by running a simple obs-cmd.
    """
    try:
        # Use a short timeout for the check command itself
        result = subprocess.run(
            OBS_CMD_CHECK_COMMAND,
            check=True,
            capture_output=True,
            text=True,
            timeout=5
        )
        logger.debug(f"OBS responsive check successful. Version: {result.stdout.strip()}")
        return True
    except FileNotFoundError:
        logger.error("Error: 'obs-cmd' not found. Please install it (yay -S obs-cmd) and ensure it's in your PATH.")
        return False # Treat as fatal for this check's purpose
    except subprocess.CalledProcessError as e:
        # This usually means obs-cmd connected but got an error, or obs-websocket is not ready.
        logger.debug(f"obs-cmd check failed (CalledProcessError): {e.stderr.strip() if e.stderr else e.stdout.strip()}")
        return False
    except subprocess.TimeoutExpired:
        logger.debug("obs-cmd check timed out.")
        return False
    except Exception as e:
        logger.warning(f"Unexpected error checking OBS responsiveness: {e}")
        return False

def main():
    logger.info("--- OBS Starter and Replay Toggler Script ---")

    # 1. Start OBS in a separate thread
    logger.info("Creating thread to start OBS Studio.")
    obs_thread = threading.Thread(target=run_obs_in_thread, name="OBSLauncherThread", daemon=True)
    obs_thread.start()
    logger.info("OBS launcher thread started.")

    # Give it a moment to actually try and launch the process
    time.sleep(2) # Allow Popen to be called and obs_process to be set (or fail)

    if obs_process is None:
        logger.error("OBS process object not created. This likely means 'flatpak' was not found or another critical error occurred in the OBS starting thread.")
        logger.info("Script will exit.")
        return
    elif obs_process.poll() is not None: # Check if process already exited
        logger.error(f"OBS process (PID: {obs_process.pid}) started but exited immediately with code {obs_process.returncode}. Check OBS logs or flatpak errors.")
        logger.info("Script will exit.")
        return
    else:
        logger.info(f"OBS process (PID: {obs_process.pid}) appears to be running.")


    # 2. Wait for OBS to become responsive
    logger.info(f"Waiting for OBS (via obs-websocket) to become responsive (max {MAX_WAIT_TIME_SECONDS} seconds)...")
    start_time = time.time()
    obs_is_ready = False
    while time.time() - start_time < MAX_WAIT_TIME_SECONDS:
        logger.info("Checking OBS responsiveness...")
        if is_obs_responsive():
            logger.info("OBS is responsive!")
            obs_is_ready = True
            break
        logger.info(f"OBS not yet responsive. Retrying in {CHECK_INTERVAL_SECONDS}s...")
        time.sleep(CHECK_INTERVAL_SECONDS)

        # Check if the OBS process itself has unexpectedly died during the wait
        if obs_process and obs_process.poll() is not None:
            logger.warning(f"OBS process (PID: {obs_process.pid}) seems to have terminated unexpectedly with code {obs_process.returncode} while waiting for responsiveness.")
            obs_is_ready = False
            break

    if not obs_is_ready:
        logger.error("OBS did not become responsive within the time limit.")
        if obs_process and obs_process.poll() is None:
            logger.warning("OBS process might still be starting or stuck. You may need to manage it manually.")
        logger.info("Script will exit without toggling replay.")
        return

    # 3. Run obs-cmd replay toggle
    logger.info(f"Attempting to toggle replay buffer with command: {' '.join(OBS_CMD_TOGGLE_COMMAND)}")
    try:
        result = subprocess.run(
            OBS_CMD_TOGGLE_COMMAND,
            check=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        logger.info("Successfully sent 'replay toggle' command.")
        if result.stdout:
            logger.info(f"obs-cmd output: {result.stdout.strip()}")
        if result.stderr: # Should be empty on success, but log if present
            logger.warning(f"obs-cmd errors (though command succeeded): {result.stderr.strip()}")
    except FileNotFoundError:
        logger.error("Error: 'obs-cmd' not found. Cannot toggle replay.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing 'obs-cmd replay toggle':")
        logger.error(f"  Return code: {e.returncode}")
        if e.stdout: logger.error(f"  Stdout: {e.stdout.strip()}")
        if e.stderr: logger.error(f"  Stderr: {e.stderr.strip()}")
        logger.warning("  This could mean OBS isn't configured for replays, the replay buffer isn't active, or another obs-websocket issue.")
    except subprocess.TimeoutExpired:
        logger.error("'obs-cmd replay toggle' command timed out.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while toggling replay: {e}")

    logger.info("--- Script finished ---")
    logger.info("OBS Studio (if started successfully) should still be running in the background.")

if __name__ == "__main__":
    # Ensure obs-cmd can find its configuration if needed (e.g., if port/password is non-default)
    # You might set environment variables here if necessary, e.g.:
    # os.environ["OBS_WEBSOCKET_PORT"] = "4444"
    # os.environ["OBS_WEBSOCKET_PASSWORD"] = "your_password"
    # logger.info(f"OBS_WEBSOCKET_PORT: {os.getenv('OBS_WEBSOCKET_PORT', 'Not Set (default 4455)')}")
    # logger.info(f"OBS_WEBSOCKET_PASSWORD: {'Set' if os.getenv('OBS_WEBSOCKET_PASSWORD') else 'Not Set (default none)'}")
    main()
