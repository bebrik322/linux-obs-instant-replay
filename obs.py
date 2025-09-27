#!/usr/bin/python
import subprocess
import threading
import time
import logging

# --- Configuration ---
OBS_FLATPAK_COMMAND = ["flatpak", "run", "com.obsproject.Studio", "--disable-shutdown-check"]
OBS_CMD_CHECK_COMMAND = ["obs-cmd", "info"]
OBS_CMD_TOGGLE_COMMAND = ["obs-cmd", "replay", "toggle"]

MAX_WAIT_TIME_SECONDS = 60
CHECK_INTERVAL_SECONDS = 1
# ---------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(threadName)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

obs_process = None

def run_obs_in_thread():
    """
    Runs OBS Studio in a separate process.
    This function is intended to be run in a separate thread.
    """
    global obs_process
    logger.info(f"Attempting to start OBS Studio with: {' '.join(OBS_FLATPAK_COMMAND)}")
    try:
        obs_process = subprocess.Popen(OBS_FLATPAK_COMMAND)
        logger.info(f"OBS Studio process started with PID: {obs_process.pid}. It will continue running after this script exits.")
    except FileNotFoundError:
        logger.error("Error: 'flatpak' command not found. Is Flatpak installed and in your PATH?")
    except Exception as e:
        logger.error(f"An error occurred while trying to start OBS: {e}")

def is_obs_responsive():
    """
    Checks if OBS (via obs-websocket) is responsive by running a simple obs-cmd.
    """
    try:
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
        return False
    except subprocess.CalledProcessError as e:
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

    logger.info("Creating thread to start OBS Studio.")
    obs_thread = threading.Thread(target=run_obs_in_thread, name="OBSLauncherThread", daemon=True)
    obs_thread.start()
    logger.info("OBS launcher thread started.")

    time.sleep(2)

    if obs_process is None:
        logger.error("OBS process object not created. This likely means 'flatpak' was not found or another critical error occurred in the OBS starting thread.")
        logger.info("Script will exit.")
        return
    elif obs_process.poll() is not None:
        logger.error(f"OBS process (PID: {obs_process.pid}) started but exited immediately with code {obs_process.returncode}. Check OBS logs or flatpak errors.")
        logger.info("Script will exit.")
        return
    else:
        logger.info(f"OBS process (PID: {obs_process.pid}) appears to be running.")

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
        if result.stderr:
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
    main()
