import os
import sys

# Determine if running as a script or frozen executable
if getattr(sys, 'frozen', False):
    # If the application is run as a bundle/frozen executable, the Project Root is the sys._MEIPASS
    PROJECT_ROOT = sys._MEIPASS # type: ignore
else:
    # If run as a script, the Project Root is the parent directory of 'autogif'
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RESOURCES_DIR = os.path.join(PROJECT_ROOT, "resources")
FONTS_DIR = os.path.join(PROJECT_ROOT, "autogif", "fonts") # autogif/fonts as per spec
EFFECTS_PLUGINS_DIR = os.path.join(PROJECT_ROOT, "autogif", "effects", "plugins")

# Define paths to executables - ensure these are in the resources directory
YT_DLP_PATH = os.path.join(RESOURCES_DIR, "yt-dlp.exe" if os.name == 'nt' else "yt-dlp")
FFMPEG_PATH = os.path.join(RESOURCES_DIR, "ffmpeg.exe" if os.name == 'nt' else "ffmpeg")
FFPROBE_PATH = os.path.join(RESOURCES_DIR, "ffprobe.exe" if os.name == 'nt' else "ffprobe")

TEMP_DIR_NAME = "_autogif_temp"
TEMP_DIR = os.path.join(PROJECT_ROOT, TEMP_DIR_NAME)

# User configuration path (cross-platform)
if os.name == 'nt':
    USER_CONFIG_DIR = os.path.join(os.getenv('USERPROFILE', ''), '.autogif')
else:
    USER_CONFIG_DIR = os.path.join(os.path.expanduser('~'), '.autogif')
USER_CONFIG_FILE = os.path.join(USER_CONFIG_DIR, 'config.json')

def ensure_directories_exist():
    """Ensures that necessary directories exist."""
    os.makedirs(FONTS_DIR, exist_ok=True)
    os.makedirs(EFFECTS_PLUGINS_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)
    os.makedirs(USER_CONFIG_DIR, exist_ok=True)
    # Resources directory is expected to be provided by the user/setup

ensure_directories_exist()

# Sanity checks for executables (optional, but good for development)
# These will print warnings if executables are not found at startup.
# In a real app, you might handle this more gracefully or in the functions that use them.
if not os.path.exists(YT_DLP_PATH):
    print(f"WARNING: yt-dlp not found at expected path: {YT_DLP_PATH}")
    print(f"Please ensure yt-dlp is placed in the '{RESOURCES_DIR}' directory.")

if not os.path.exists(FFMPEG_PATH):
    print(f"WARNING: ffmpeg not found at expected path: {FFMPEG_PATH}")
    print(f"Please ensure ffmpeg is placed in the '{RESOURCES_DIR}' directory.")

if not os.path.exists(FFPROBE_PATH):
    print(f"WARNING: ffprobe not found at expected path: {FFPROBE_PATH}")
    print(f"Please ensure ffprobe is placed in the '{RESOURCES_DIR}' directory.") 