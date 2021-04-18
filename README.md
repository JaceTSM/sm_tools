# sm_tools
Tools to interact with stepmania and it's related filetypes (.sm in particular)

### Motivation
There has been desire to do Data Science projects on stepmania data, like song difficulty modeling. The first tool in this repo is a `step_parser`, which will extract a feature set from a song directory to build models off of.

### How to use
```shell
python src/step_parser/step_parser.py \
    /path/to/your/stepmania/songs \
    /path/to/output.csv
```
