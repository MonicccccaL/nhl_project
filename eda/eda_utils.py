"""Shared setup for the Phase 3 EDA notebooks.

Each notebook in eda/ starts with:

    from eda_utils import *
    con, q = connect()
    save = figure_saver("3a_teams")

`connect()` opens DuckDB on the Phase 1 Parquet files in data/clean/ and adds the helper
views listed in HELPER_VIEWS. Every view covers 2010-11 to 2019-20, the Phase 1 window.
"""
from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
from matplotlib.patches import Arc, Circle, Rectangle

__all__ = ["ROOT", "CLEAN", "FIGURES", "MIN_GP", "MIN_GOALIE_GP", "COLORS", "POS_COLORS",
           "BLUE", "RUST", "GREY", "GOLD", "GREEN", "connect", "figure_saver", "draw_rink",
           "pct_axis", "np", "pd", "plt", "mtick", "duckdb"]


def _find_root():
    """Walk up from the current folder until we find data/clean (works from eda/ or the project root)."""
    here = Path.cwd().resolve()
    for folder in [here, *here.parents]:
        if (folder / "data" / "clean").is_dir():
            return folder
    raise FileNotFoundError("Could not find data/clean. Open the nhl_project folder in VS Code "
                            "and run the Phase 1 notebook first.")


ROOT = _find_root()
CLEAN = ROOT / "data" / "clean"
FIGURES = ROOT / "outputs" / "figures"

MIN_GP = 20            # a skater-season counts as "regular" with at least this many regular-season games
MIN_GOALIE_GP = 20     # same threshold for goalies

# ---------------------------------------------------------------- chart style
BLUE, RUST, GREY, GOLD, GREEN = "#4a7c9b", "#b85c38", "#8c8c8c", "#c9a227", "#5b8c5a"
COLORS = [BLUE, RUST, GOLD, GREEN, "#7b6ca8", GREY]
POS_COLORS = {"F": BLUE, "D": RUST, "G": GOLD}

plt.rcParams.update({
    "figure.dpi": 110, "axes.spines.top": False, "axes.spines.right": False,
    "axes.titleweight": "bold", "axes.titlesize": 12, "axes.grid": True,
    "grid.alpha": 0.25, "font.size": 10, "axes.prop_cycle": plt.cycler(color=COLORS)})
pd.set_option("display.max_columns", 60)
pd.set_option("display.width", 220)
pd.set_option("display.float_format", lambda v: f"{v:,.3f}")


def figure_saver(notebook_name):
    """Return save(fig, name), which writes outputs/figures/<notebook_name>/<name>.png."""
    folder = FIGURES / notebook_name
    folder.mkdir(parents=True, exist_ok=True)

    def save(fig, name):
        fig.savefig(folder / f"{name}.png", bbox_inches="tight", dpi=150)
    return save


def pct_axis(ax, axis="y", decimals=0, step=None):
    """Format an axis holding proportions (0.54) as percentages (54%).

    step sets the tick spacing (0.02 = a tick every 2 percentage points), which avoids repeated
    labels when the range is narrow."""
    target = ax.yaxis if axis == "y" else ax.xaxis
    if step:
        target.set_major_locator(mtick.MultipleLocator(step))
    target.set_major_formatter(mtick.PercentFormatter(1, decimals=decimals))


# ---------------------------------------------------------------- data
TABLES = ["dim_player", "dim_team", "fact_game", "fact_player_game", "fact_team_game",
          "fact_play", "bridge_play_player"]

HELPER_VIEWS = {
    # One row per team id, with the franchise's current abbreviation (Atlanta -> WPG, Phoenix -> ARI)
    "franchise": """
        SELECT team_id, franchise_id, team_abbrev,
               last_value(team_abbrev) OVER (PARTITION BY franchise_id ORDER BY last_season
                   ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS franchise,
               last_value(team_full_name) OVER (PARTITION BY franchise_id ORDER BY last_season
                   ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS franchise_name
        FROM dim_team""",

    # League averages per team-game, by season and game type, for putting stats in context
    "league_season": """
        SELECT season, game_type, count(DISTINCT game_id) AS games,
               avg(goals_for) AS goals_pg, avg(shots_for) AS shots_pg,
               sum(goals_for) / CAST(sum(shots_for) AS BIGINT) AS shooting_pct,
               sum(pp_goals) / CAST(sum(pp_opportunities) AS BIGINT) AS pp_pct,
               avg(pp_opportunities) AS pp_opps_pg, avg(hits) AS hits_pg, avg(pim) AS pim_pg,
               avg(blocked_shots) AS blocks_pg, avg(giveaways) AS giveaways_pg, avg(takeaways) AS takeaways_pg
        FROM fact_team_game GROUP BY ALL""",

    # One row per skater per regular season (zero-TOI games left out), with per-60 rates and age
    "skater_season": """
        WITH s AS (
            SELECT player_id, season, CAST(substr(season, 1, 4) AS INT) AS season_start_year,
                   count(*) AS gp, count(DISTINCT team_id) AS teams, sum(toi_seconds) / 60.0 AS toi_min,
                   sum(toi_even_seconds) / 60.0 AS toi_ev_min, sum(toi_pp_seconds) / 60.0 AS toi_pp_min,
                   sum(toi_sh_seconds) / 60.0 AS toi_sh_min,
                   CAST(sum(goals) AS BIGINT) AS goals, CAST(sum(assists) AS BIGINT) AS assists, CAST(sum(points) AS BIGINT) AS points, CAST(sum(shots) AS BIGINT) AS shots,
                   CAST(sum(pp_goals) AS BIGINT) AS pp_goals, CAST(sum(pp_assists) AS BIGINT) AS pp_assists,
                   CAST(sum(sh_goals) AS BIGINT) AS sh_goals, CAST(sum(sh_assists) AS BIGINT) AS sh_assists,
                   CAST(sum(hits) AS BIGINT) AS hits, CAST(sum(blocked_shots) AS BIGINT) AS blocks, CAST(sum(takeaways) AS BIGINT) AS takeaways,
                   CAST(sum(giveaways) AS BIGINT) AS giveaways, CAST(sum(pim) AS BIGINT) AS pim, CAST(sum(plus_minus) AS BIGINT) AS plus_minus,
                   CAST(sum(faceoff_wins) AS BIGINT) AS faceoff_wins, CAST(sum(faceoffs_taken) AS BIGINT) AS faceoffs_taken
            FROM fact_player_game
            WHERE player_role = 'Skater' AND game_type = 'Regular' AND NOT zero_toi_flag
            GROUP BY ALL)
        SELECT s.*, p.full_name, p.primary_position, p.position_group, p.shoots_catches,
               date_diff('day', p.birth_date, make_date(s.season_start_year + 1, 2, 1)) / 365.25 AS age,
               s.toi_min / s.gp AS avg_toi, s.points / s.gp AS points_pg,
               60 * s.goals / s.toi_min AS goals_60,   60 * s.assists / s.toi_min AS assists_60,
               60 * s.points / s.toi_min AS points_60, 60 * s.shots / s.toi_min AS shots_60,
               60 * s.hits / s.toi_min AS hits_60,     60 * s.blocks / s.toi_min AS blocks_60,
               60 * s.takeaways / s.toi_min AS takeaways_60, 60 * s.giveaways / s.toi_min AS giveaways_60,
               60 * s.pim / s.toi_min AS pim_60,
               CASE WHEN s.shots > 0 THEN s.goals / s.shots END AS shooting_pct,
               CASE WHEN s.faceoffs_taken > 0 THEN s.faceoff_wins / s.faceoffs_taken END AS faceoff_pct
        FROM s JOIN dim_player p USING (player_id)""",

    # One row per goalie per regular season
    "goalie_season": """
        WITH s AS (
            SELECT player_id, season, CAST(substr(season, 1, 4) AS INT) AS season_start_year,
                   count(*) AS gp, sum(toi_seconds) / 60.0 AS toi_min,
                   count(*) FILTER (WHERE goalie_decision = 'W') AS wins,
                   count(*) FILTER (WHERE goalie_decision = 'L') AS losses,
                   CAST(sum(shots_against) AS BIGINT) AS shots_against, CAST(sum(saves) AS BIGINT) AS saves,
                   CAST(sum(even_shots_against) AS BIGINT) AS ev_shots_against, CAST(sum(even_saves) AS BIGINT) AS ev_saves,
                   CAST(sum(pp_shots_against) AS BIGINT) AS pp_shots_against, CAST(sum(pp_saves) AS BIGINT) AS pp_saves,
                   CAST(sum(sh_shots_against) AS BIGINT) AS sh_shots_against, CAST(sum(sh_saves) AS BIGINT) AS sh_saves
            FROM fact_player_game
            WHERE player_role = 'Goalie' AND game_type = 'Regular' AND NOT zero_toi_flag
            GROUP BY ALL)
        SELECT s.*, p.full_name, p.shoots_catches AS catches,
               date_diff('day', p.birth_date, make_date(s.season_start_year + 1, 2, 1)) / 365.25 AS age,
               s.saves / nullif(s.shots_against, 0) AS save_pct,
               s.ev_saves / nullif(s.ev_shots_against, 0) AS ev_save_pct,
               60 * (s.shots_against - s.saves) / s.toi_min AS gaa,
               60 * s.shots_against / s.toi_min AS shots_against_60
        FROM s JOIN dim_player p USING (player_id)""",
}


def connect(threads=None):
    """Open DuckDB on the clean Parquet files and create the helper views. Returns (con, q)."""
    con = duckdb.connect()
    con.execute("SET TimeZone = 'UTC'")
    if threads:
        con.execute(f"SET threads = {int(threads)}")
    missing = []
    for t in TABLES:
        path = CLEAN / f"{t}.parquet"
        if path.exists():
            con.execute(f"CREATE OR REPLACE VIEW {t} AS SELECT * FROM read_parquet('{path.as_posix()}')")
        else:
            missing.append(t)
    required = {"dim_player", "dim_team", "fact_game", "fact_player_game", "fact_team_game"}
    if required & set(missing):
        raise FileNotFoundError(f"Missing {sorted(required & set(missing))} in {CLEAN}. "
                                "Run the Phase 1 notebook again to create them.")
    for name, sql in HELPER_VIEWS.items():
        con.execute(f"CREATE OR REPLACE VIEW {name} AS {sql}")

    def q(sql):
        """Run a SQL query and return a pandas DataFrame."""
        return con.sql(sql).df()

    if missing:
        print(f"Note: {', '.join(missing)} not found; play-level analysis will be unavailable.")
    return con, q


# ---------------------------------------------------------------- rink drawing
def draw_rink(ax=None, half=False, color="#9aa5ad", lw=1.2):
    """Draw an NHL rink in the play-by-play coordinate system (feet, centre ice at 0,0).

    The full rink spans x -100..100 and y -42.5..42.5. With half=True only the offensive half
    (x 0..100) is drawn, which suits standardized coordinates (st_x, st_y) where the attacking
    net is always at x = 89.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 4.4) if not half else (6, 5))
    kw = dict(color=color, lw=lw, fill=False)
    x0 = 0 if half else -100
    # boards with rounded corners (radius 28 ft)
    r = 28
    ax.plot([x0 if half else -100 + r, 100 - r], [42.5, 42.5], color=color, lw=lw)
    ax.plot([x0 if half else -100 + r, 100 - r], [-42.5, -42.5], color=color, lw=lw)
    ax.plot([100, 100], [-42.5 + r, 42.5 - r], color=color, lw=lw)
    ax.add_patch(Arc((100 - r, 42.5 - r), 2 * r, 2 * r, theta1=0, theta2=90, color=color, lw=lw))
    ax.add_patch(Arc((100 - r, -42.5 + r), 2 * r, 2 * r, theta1=270, theta2=360, color=color, lw=lw))
    if not half:
        ax.plot([-100, -100], [-42.5 + r, 42.5 - r], color=color, lw=lw)
        ax.add_patch(Arc((-100 + r, 42.5 - r), 2 * r, 2 * r, theta1=90, theta2=180, color=color, lw=lw))
        ax.add_patch(Arc((-100 + r, -42.5 + r), 2 * r, 2 * r, theta1=180, theta2=270, color=color, lw=lw))
    # centre line, blue lines, goal lines
    ax.axvline(0, color="#c96b6b", lw=lw * 1.5, alpha=0.6)
    for side in ([1] if half else [-1, 1]):
        ax.axvline(25 * side, color="#6b8fc9", lw=lw * 2, alpha=0.6)
        ax.plot([89 * side, 89 * side], [-37, 37], color="#c96b6b", lw=lw, alpha=0.7)
        ax.add_patch(Rectangle((89 * side if side > 0 else -93, -3), 4, 6, **kw))           # net
        ax.add_patch(Arc((89 * side, 0), 12, 12, theta1=90 if side > 0 else -90,
                         theta2=270 if side > 0 else 90, color="#6b8fc9", lw=lw))        # crease
        for fy in (22, -22):                                                             # end-zone circles
            ax.add_patch(Circle((69 * side, fy), 15, **kw))
            ax.plot(69 * side, fy, "o", color="#c96b6b", ms=3)
        for fy in (22, -22):                                                             # neutral-zone dots
            ax.plot(20 * side, fy, "o", color="#c96b6b", ms=3)
    ax.add_patch(Circle((0, 0), 15, color="#6b8fc9", lw=lw, fill=False))
    ax.set_xlim(x0 - 2, 102)
    ax.set_ylim(-44, 44)
    ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    return ax
