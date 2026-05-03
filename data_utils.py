import pandas as pd
import streamlit as st


def ensure_datetime(df, col):
    if df is not None and col in df.columns:
        df = df.copy()
        df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


@st.cache_data
def load_data():
    runs = pd.read_csv("runs_raw.csv")
    batches = pd.read_csv("batches_raw.csv")
    changes = pd.read_csv("changes_raw.csv")
    downtime = pd.read_csv("downtime_raw.csv")

    # -----------------------------
    # Clean runs_raw
    # -----------------------------
    if "run_date" in runs.columns:
        runs["run_date_raw"] = runs["run_date"].astype(str).str.strip()
        dt_try_1 = pd.to_datetime(runs["run_date_raw"], dayfirst=True, errors="coerce")
        dt_try_2 = pd.to_datetime(runs["run_date_raw"], yearfirst=True, errors="coerce")
        runs["run_date"] = dt_try_1.fillna(dt_try_2)

    for col in ["bins_run", "retip"]:
        if col in runs.columns:
            runs[col] = pd.to_numeric(runs[col], errors="coerce")

    for col in ["start_time", "end_time"]:
        if col in runs.columns:
            runs[col] = runs[col].astype(str).str.strip()

    if all(col in runs.columns for col in ["run_date", "start_time", "end_time"]):
        safe_date = pd.to_datetime(runs["run_date"], errors="coerce")

        runs["start_dt"] = pd.to_datetime(
            safe_date.dt.strftime("%Y-%m-%d") + " " + runs["start_time"],
            errors="coerce"
        )
        runs["end_dt"] = pd.to_datetime(
            safe_date.dt.strftime("%Y-%m-%d") + " " + runs["end_time"],
            errors="coerce"
        )

        overnight_mask = runs["end_dt"] < runs["start_dt"]
        runs.loc[overnight_mask, "end_dt"] = runs.loc[overnight_mask, "end_dt"] + pd.Timedelta(days=1)

        runs["run_hours"] = (runs["end_dt"] - runs["start_dt"]).dt.total_seconds() / 3600
        runs["total_bins_with_retip"] = runs["bins_run"].fillna(0) + runs["retip"].fillna(0)
        runs["bins_per_hour_row"] = runs["total_bins_with_retip"] / runs["run_hours"]
        runs.loc[runs["run_hours"] <= 0, "bins_per_hour_row"] = pd.NA
    else:
        runs["run_hours"] = pd.NA
        runs["total_bins_with_retip"] = runs["bins_run"].fillna(0) + runs["retip"].fillna(0)
        runs["bins_per_hour_row"] = pd.NA

    for col in ["grower", "variety", "batch_id", "run_id"]:
        if col in runs.columns:
            runs[col] = (
                runs[col]
                .fillna("")
                .astype(str)
                .str.strip()
                .replace("", pd.NA)
            )

    # -----------------------------
    # Clean batches_raw
    # -----------------------------
    for col in ["grower", "variety", "decfile_version", "defect_1", "defect_2", "defect_3", "batch_id"]:
        if col in batches.columns:
            batches[col] = (
                batches[col]
                .fillna("")
                .astype(str)
                .str.strip()
                .replace("", pd.NA)
            )

    # -----------------------------
    # Clean changes_raw
    # -----------------------------
    changes = changes.drop(columns=[c for c in changes.columns if c.startswith("Unnamed")], errors="ignore")

    if "change_time" in changes.columns:
        changes["change_time"] = pd.to_datetime(changes["change_time"], errors="coerce")

    for col in ["boundary_before", "boundary_after"]:
        if col in changes.columns:
            changes[col] = pd.to_numeric(changes[col], errors="coerce")

    for col in [
        "reason", "mode", "check_class", "action",
        "variety", "grower", "run_id", "batch_id",
        "sensitivity", "accuracy"
    ]:
        if col in changes.columns:
            changes[col] = (
                changes[col]
                .fillna("")
                .astype(str)
                .str.strip()
                .replace("", pd.NA)
            )

    # -----------------------------
    # Clean downtime_raw
    # -----------------------------
    if "run_date" in downtime.columns:
        downtime["run_date_raw"] = downtime["run_date"].astype(str).str.strip()
        dt_try_1 = pd.to_datetime(downtime["run_date_raw"], dayfirst=True, errors="coerce")
        dt_try_2 = pd.to_datetime(downtime["run_date_raw"], yearfirst=True, errors="coerce")
        downtime["run_date"] = dt_try_1.fillna(dt_try_2)

    if "duration_hours" in downtime.columns:
        downtime["duration_hours"] = pd.to_numeric(downtime["duration_hours"], errors="coerce")
    elif "duration_minutes" in downtime.columns:
        downtime["duration_minutes"] = pd.to_numeric(downtime["duration_minutes"], errors="coerce")
        downtime["duration_hours"] = downtime["duration_minutes"] / 60

    for col in ["downtime_area", "downtime_reason", "run_id"]:
        if col in downtime.columns:
            downtime[col] = (
                downtime[col]
                .fillna("")
                .astype(str)
                .str.strip()
                .replace("", pd.NA)
            )

    return runs, batches, changes, downtime
