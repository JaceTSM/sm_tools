# sm_tools
Tools to interact with stepmania and it's related filetypes (.sm in particular)

## Motivation
There has been desire to do Data Science projects on stepmania data, like song difficulty modeling. The first tool in this repo is a `step_parser`, which will extract a feature set from a song directory to build models off of.

## How to use
### With checked out repo: 
```shell
git clone git@github.com:JaceTSM/sm_tools.git
cd sm_tools

python src/sm_tools/step_parser/parser.py \
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
from sm_tools import analyze_stepchart, batch_analysis

analyze_stepchart("<sm_file_path>")

batch_analysis("<path_to_sm_song_dir") 
```
