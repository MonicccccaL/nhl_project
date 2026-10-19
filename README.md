# NHL Player Analytics

Phase 1 of the project audits the Kaggle NHL Game Data, cleans it, and saves a small set of clean tables for the later phases. Phase 3 explores those tables to set up the clustering and salary model. Each phase is one notebook.

## Data

This project uses the [NHL Game Data](https://www.kaggle.com/datasets/martinellis/nhl-game-data) dataset by Martin Ellis on Kaggle. The data is not included in this repository. Download the CSVs from Kaggle and place them in `data/raw/` before running the notebook.

## What's in this folder

```
nhl_project/
├── phase1_data_audit_and_cleaning.ipynb   the whole of Phase 1, top to bottom
├── eda/
│   ├── eda_utils.py                       shared setup imported by every Phase 3 notebook
│   └── 3a_teams.ipynb                     Phase 3A: season recap and team analysis
├── requirements.txt                       Python packages to install
├── README.md                              this file
├── data/
│   ├── raw/      put the Kaggle CSVs here
│   └── clean/    the notebook saves the clean tables here
└── outputs/
    └── figures/  charts saved by the Phase 3 notebooks, one folder per notebook
```

The notebook already contains the results from my run, so you can read it right away. To run it yourself, follow the setup below once.

## One-time setup in VS Code (Mac with Anaconda)

1. **Install VS Code.** Download it from [code.visualstudio.com](https://code.visualstudio.com) if it isn't in Applications yet.
2. **Open the folder.** In VS Code choose **File → Open Folder…**, select `nhl_project`, and click Open. If it asks whether you trust the authors, click **Yes**.
3. **Install the extensions.** Click **Install All** on the pop-up that recommends extensions. If you missed it, open the Extensions icon in the left sidebar (four small squares) and install **Python** and **Jupyter**, both by Microsoft.
4. **Create a Python environment.** Choose **Terminal → New Terminal** and run these lines one at a time:
   ```bash
   conda create -n nhl python=3.12 -y
   conda activate nhl
   pip install -r requirements.txt
   ```
   If you see `conda: command not found`, run `~/anaconda3/bin/conda init zsh`, close the terminal, open a new one, and try again.
5. **Add the data.** Copy the Kaggle CSVs into `data/raw/` and keep their original names (`game.csv`, `player_info.csv`, `game_skater_stats.csv`, and so on). `game_plays.csv` and `game_shifts.csv` are optional; the notebook uses them if they're there.

## Running the notebook

1. Click `phase1_data_audit_and_cleaning.ipynb` in the Explorer on the left.
2. Click **Select Kernel** in the top-right corner, then **Python Environments**, then **nhl**.
3. Click **Run All** in the notebook toolbar.

It takes about a minute without `game_plays.csv`, and a few minutes with it. When it finishes, `data/clean/` contains:

| File | One row per |
|---|---|
| `dim_player.parquet` | player |
| `dim_team.parquet` | team |
| `fact_game.parquet` | game (2010-11 to 2019-20, regular season and playoffs) |
| `fact_player_game.parquet` | player per game (skaters and goalies) |
| `fact_team_game.parquet` | team per game, with the opponent's stats on the same row |
| `fact_play.parquet` | play or event (only if `game_plays.csv` was provided) |
| `bridge_play_player.parquet` | player role in a play (shooter, goalie, scorer, and so on) |
| `reconciliation_log.csv` | every record that was excluded, relabelled, or flagged, and why |

## Phase 3: exploratory analysis

Phase 3 is split into several notebooks in `eda/`, each one focused on a single topic: teams, skaters, shots and expected goals, goalies, home ice, hits, and icing. They all use 2010-11 to 2019-20 and start with the same two lines:

```python
from eda_utils import *
con, q = connect()
```

`connect()` opens the Phase 1 tables in `data/clean/` and adds a few shared views: `franchise` (relocated teams under their current name), `league_season` (league averages per season), `skater_season` and `goalie_season` (one row per player per regular season). `eda_utils.py` also sets the chart style and has `draw_rink()` for shot and hit maps. Each notebook saves its charts to `outputs/figures/<notebook name>/`.

## Changing the season range

The audit looks at every season, but the clean tables keep only 2010-11 onward, because hits, blocks, takeaways, giveaways, and playoff games are not recorded before then. To change this, edit `ANALYSIS_START_SEASON` in the first code cell and run the notebook again.

## If something goes wrong

`ModuleNotFoundError: No module named 'duckdb'` means the notebook is using a different Python. Select the **nhl** kernel again (step 2 above).

`AssertionError: game.csv is missing` means a required CSV isn't in `data/raw/`, or Finder renamed it (for example `game (1).csv`).
