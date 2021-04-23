# sm_tools
Tools to interact with stepmania and it's related filetypes (.sm in particular)

## Motivation
There has been desire to do Data Science projects on stepmania data, like song difficulty modeling. The first tool in this repo is a `step_parser`, which will extract a feature set from a song directory to build models off of.

## How to use
### With checked out repo: 
```shell
git clone git@github.com:JaceTSM/sm_tools.git
cd sm_tools

python src/step_parser/cli.py \
    /path/to/your/stepmania/songs \
    /path/to/output.csv
```

### As package (coming soon):
```shell
pip install sm_tools

step_parser /path/to/your/stepmania/songs /path/to/output.csv
```
In python:
```python
import os
from step_parser import analyze_stepchart, batch_analysis

# Get DF for all songs in a dir (recursive search)
sm_song_dir = "/mnt/c/Games/StepMania 5/Songs"
batch_analysis(sm_song_dir)

# Get DF for single .sm file
sample_stepchart = os.path.join(
    sm_song_dir,
    "Jimmy Jawns/Dreadnought - [Aoreo]/Dreadnought.sm"
)
analyze_stepchart(sample_stepchart)
```
