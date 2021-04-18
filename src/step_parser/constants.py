import os


ROOT_DIR = os.path.abspath(os.sep)
LOG_DIR = os.path.join(ROOT_DIR, "var", "log")
ERROR_LOG = os.path.join(LOG_DIR, "sm_tools_error.log")

# These numbers in a stepchart indicate notes that require stepping on
# 1 = note, 2 = hold, 4 = roll
NOTE_TYPES = ["1", "2", "4"]
