import os
import git


repo = git.Repo(__file__, search_parent_directories=True)

ROOT_DIR = repo.git.rev_parse("--show-toplevel")
RESOURCE_DIR = os.path.join(ROOT_DIR, "resources")
LOG_DIR = os.path.join(ROOT_DIR, "log")
ERROR_LOG = os.path.join(LOG_DIR, "error.log")

# These numbers in a stepchart indicate notes that require stepping on
# 1 = note, 2 = hold, 4 = roll
NOTE_TYPES = ["1", "2", "4"]
