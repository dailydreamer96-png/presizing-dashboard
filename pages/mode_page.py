import streamlit as st
import pandas as pd

from data_utils import load_data

runs, batches, changes, downtime = load_data()


# ============================================================
# LOCAL HELPERS
# ============================================================
def ensure_datetime(df, col):
    if df is not None and col in df.columns:
        df = df.copy()
        df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def apply_dashboard_style():
    st.markdown("""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Sora:wght@300;400;600;700&display=swap');

      :root {
        --bg:        #0f1117;
        --surface:   #181c27;
        --border:    #252a3a;
        --amber:     #f5a623;
        --emerald:   #34d399;
        --rose:      #fb7185;
        --slate:     #94a3b8;
        --white:     #e8eaf2;
      }

      html, body, [data-testid="stAppViewContainer"] {
        background: var(--bg) !important;
        color: var(--white) !important;
        font-family: 'Sora', sans-serif !important;
      }

      [data-testid="stHeader"] {
        background: transparent !important;
      }

      .block-container {
        padding-top: 1rem;
        padding-bottom: 1.5rem;
        padding-left: 1.4rem;
        padding-right: 1.4rem;
      }

      section[data-testid="stSidebar"] {
        background-color: #0f172a;
      }

      section[data-testid="stSidebar"] * {
        color: #e5e7eb !important;
      }

      [data-testid="stSelectbox"] label,
      [data-testid="stRadio"] label,
      .stSelectbox label {
        color: var(--slate) !important;
        font-size: 0.72rem !important;
        letter-spacing: 0.05em;
        text-transform: uppercase;
      }

      [data-testid="stSelectbox"] > div > div {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: 6px !important;
        color: var(--white) !important;
      }

      [data-testid="stDataFrame"] {
        background: var(--surface) !important;
        border-radius: 8px !important;
        border: 1px solid var(--border) !important;
        overflow: hidden;
      }

      h1, h2, h3 {
        letter-spacing: -0.02em;
      }

      .section-title {
        font-size: 0.68rem;
        font-weight: 600;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: var(--amber);
        margin-bottom: 10px;
        border-bottom: 1px solid var(--border);
        padding-bottom: 6px;
      }

      .kpi-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-top: 3px solid var(--amber);
        border-radius: 8px;
        padding: 18px 22px;
        margin-bottom: 10px;
      }

      .kpi-label {
        font-size: 0.65rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--slate);
        margin-bottom: 4px;
      }

      .kpi-value {
        font-family: 'DM Mono', monospace;
        font-size: 1.6rem;
        font-weight: 500;
        color: var(--white);
      }

      .kpi-delta {
        font-family: 'DM Mono', monospace;
        font-size: 0.7rem;
        margin-top: 4px;
      }

      .kpi-delta.up { color: var(--emerald); }
      .kpi-delta.down { color: var(--rose); }
      .kpi-delta.neu { color: var(--slate); }

      .page-header {
        display: flex;
        align-items: baseline;
        gap: 16px;
        margin-bottom: 20px;
        border-bottom: 1px solid var(--border);
        padding-bottom: 14px;
      }

      .page-header h1 {
        font-family: 'Sora', sans-serif;
        font-size: 1.35rem;
        font-weight: 700;
        color: var(--white);
        margin: 0;
        letter-spacing: -0.01em;
      }

      .page-header span {
        font-family: 'DM Mono', monospace;
        font-size: 0.7rem;
        color: var(--slate);
      }

      .mode-card {
        border: 1px solid #374151;
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 12px;
        background-color: #111827;
      }

      .mode-card-title {
        font-size: 16px;
        font-weight: 600;
        margin-bottom: 6px;
        color: #ffffff;
      }

      .mode-card-meta {
        font-size: 14px;
        color: #d1d5db;
      }
    </style>
    """, unsafe_allow_html=True)


def section_title(title: str):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)


def kpi_html(label, value, delta="", direction="neu"):
    delta_html = f'<div class="kpi-delta {direction}">{delta}</div>' if delta else ""
    return f"""
    <div class="kpi-card">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{value}</div>
      {delta_html}
    </div>
    """


def summarize_boundaries(series):
    vals = pd.to_numeric(series, errors="coerce").dropna().tolist()
    vals = sorted(set(vals))
    if not vals:
        return "", ""

    def fmt(v):
        return str(int(v)) if float(v).is_integer() else str(v)

    top_3 = ", ".join(fmt(v) for v in vals[:3])
    all_vals = ", ".join(fmt(v) for v in vals)
    return top_3, all_vals


# ============================================================
# PREP
# ============================================================
runs = ensure_datetime(runs, "run_date")
apply_dashboard_style()

st.markdown(
    """
    <div class="page-header">
      <h1>⚙️ Mode Investigation</h1>
      <span>Operator workflow · adjustment reference · grower completion</span>
    </div>
    """,
    unsafe_allow_html=True,
)

if changes is None:
    st.info("changes_raw.csv not found.")
    st.stop()

mode_df = changes.copy()
batches_df = batches.copy() if batches is not None else None
runs_df = runs.copy()

# ============================================================
# JOIN DATA
# ============================================================
if "run_id" in mode_df.columns and "run_id" in runs_df.columns:
    join_cols = [c for c in ["run_id", "batch_id", "grower", "variety", "run_date"] if c in runs_df.columns]
    mode_df = mode_df.merge(
        runs_df[join_cols],
        on="run_id",
        how="left",
        suffixes=("", "_run")
    )

if batches_df is not None and "batch_id" in mode_df.columns and "batch_id" in batches_df.columns:
    batch_link_cols = [
        c for c in ["batch_id", "grower", "variety", "decfile_version", "defect_1", "defect_2", "defect_3"]
        if c in batches_df.columns
    ]
    mode_df = mode_df.merge(
        batches_df[batch_link_cols],
        on="batch_id",
        how="left",
        suffixes=("", "_batch")
    )

# ============================================================
# CLEANING
# ============================================================
for col in [
    "grower", "variety", "decfile_version", "mode", "check_class",
    "reason", "action", "sensitivity", "accuracy"
]:
    if col in mode_df.columns:
        mode_df[col] = (
            mode_df[col]
            .fillna("")
            .astype(str)
            .str.strip()
            .replace("", pd.NA)
        )

for col in ["boundary_before", "boundary_after"]:
    if col in mode_df.columns:
        mode_df[col] = pd.to_numeric(mode_df[col], errors="coerce")

if batches_df is not None:
    for col in ["grower", "variety", "decfile_version", "defect_1", "defect_2", "defect_3"]:
        if col in batches_df.columns:
            batches_df[col] = (
                batches_df[col]
                .fillna("")
                .astype(str)
                .str.strip()
                .replace("", pd.NA)
            )

# ============================================================
# SIDEBAR FILTERS
# ============================================================
with st.sidebar:
    st.header("Mode Filters")

    available_varieties = ["All"]
    if "variety" in mode_df.columns:
        available_varieties += sorted(mode_df["variety"].dropna().astype(str).unique().tolist())

    selected_mode_variety = st.selectbox(
        "Variety",
        available_varieties,
        key="mode_variety_selector"
    )

    filtered_mode = mode_df.copy()
    if selected_mode_variety != "All" and "variety" in filtered_mode.columns:
        filtered_mode = filtered_mode[
            filtered_mode["variety"].astype(str) == selected_mode_variety
        ]

    available_growers = ["All"]
    if "grower" in filtered_mode.columns:
        available_growers += sorted(filtered_mode["grower"].dropna().astype(str).unique().tolist())

    selected_mode_grower = st.selectbox(
        "Grower",
        available_growers,
        key="mode_grower_selector"
    )

    if selected_mode_grower != "All" and "grower" in filtered_mode.columns:
        filtered_mode = filtered_mode[
            filtered_mode["grower"].astype(str) == selected_mode_grower
        ]

    available_versions = ["All"]
    if "decfile_version" in filtered_mode.columns:
        available_versions += sorted(filtered_mode["decfile_version"].dropna().astype(str).unique().tolist())

    selected_version = st.selectbox(
        "Version",
        available_versions,
        key="mode_version_selector"
    )

    if selected_version != "All" and "decfile_version" in filtered_mode.columns:
        filtered_mode = filtered_mode[
            filtered_mode["decfile_version"].astype(str) == selected_version
        ]

# ============================================================
# KPI OVERVIEW
# ============================================================
total_changes = len(filtered_mode)
adjustments_count = 0
checks_count = 0
unique_modes = filtered_mode["mode"].dropna().nunique() if "mode" in filtered_mode.columns else 0

if "action" in filtered_mode.columns:
    adjustments_count = filtered_mode["action"].astype(str).str.lower().str.startswith("a").sum()
    checks_count = filtered_mode["action"].astype(str).str.lower().str.startswith("c").sum()

k1, k2, k3, k4 = st.columns(4)

with k1:
    st.markdown(kpi_html("Total Changes", f"{total_changes:,}"), unsafe_allow_html=True)
with k2:
    st.markdown(kpi_html("Adjustments", f"{adjustments_count:,}", "boundary changed"), unsafe_allow_html=True)
with k3:
    st.markdown(kpi_html("Checks", f"{checks_count:,}", "boundary verified"), unsafe_allow_html=True)
with k4:
    st.markdown(kpi_html("Unique Modes", f"{unique_modes:,}"), unsafe_allow_html=True)

st.markdown("---")

# ============================================================
# TOP ROW
# ============================================================
top_left, top_right = st.columns([1.15, 0.85])

with top_left:
    section_title("Top Adjusted Modes")

    adjusted_mode_table = pd.DataFrame(
        columns=[
            "Check",
            "Mode",
            "Check Class",
            "Count",
            "Reference Boundaries",
            "Sensitivity",
            "Accuracy"
        ]
    )

    if "mode" in filtered_mode.columns and "action" in filtered_mode.columns:
        adjusted = filtered_mode[
            filtered_mode["action"].astype(str).str.lower().str.startswith("a")
        ].copy()

        if not adjusted.empty:
            rows = []
            group_cols = ["mode"]
            if "check_class" in adjusted.columns:
                group_cols.append("check_class")

            for keys, grp in adjusted.groupby(group_cols, dropna=False):
                if isinstance(keys, tuple):
                    mode_name = keys[0]
                    check_class = keys[1]
                else:
                    mode_name = keys
                    check_class = ""

                _, allb = summarize_boundaries(grp["boundary_after"]) if "boundary_after" in grp.columns else ("", "")

                sensitivity_text = ""
                if "sensitivity" in grp.columns:
                    sensitivity_vals = sorted(set(grp["sensitivity"].dropna().astype(str)))
                    sensitivity_text = ", ".join(sensitivity_vals)

                accuracy_text = ""
                if "accuracy" in grp.columns:
                    accuracy_vals = sorted(set(grp["accuracy"].dropna().astype(str)))
                    accuracy_text = ", ".join(accuracy_vals)

                rows.append({
                    "Check": False,
                    "Mode": mode_name,
                    "Check Class": check_class,
                    "Count": len(grp),
                    "Reference Boundaries": allb,
                    "Sensitivity": sensitivity_text,
                    "Accuracy": accuracy_text,
                })

            adjusted_mode_table = (
                pd.DataFrame(rows)
                .sort_values(["Count", "Mode", "Check Class"], ascending=[False, True, True])
                .reset_index(drop=True)
            )

    if not adjusted_mode_table.empty:
        st.data_editor(
            adjusted_mode_table,
            use_container_width=True,
            height=360,
            hide_index=True,
            column_config={"Check": st.column_config.CheckboxColumn("Check")},
            disabled=["Mode", "Check Class", "Count", "Reference Boundaries", "Sensitivity", "Accuracy"]
        )
    else:
        st.info("No adjusted mode data available for the current filters.")

with top_right:
    section_title("Top Defects")

    top_defects_mode = pd.DataFrame(columns=["Defect", "Count"])

    if batches_df is not None:
        filtered_batches = batches_df.copy()

        if selected_mode_variety != "All" and "variety" in filtered_batches.columns:
            filtered_batches = filtered_batches[
                filtered_batches["variety"].astype(str) == selected_mode_variety
            ]

        if selected_mode_grower != "All" and "grower" in filtered_batches.columns:
            filtered_batches = filtered_batches[
                filtered_batches["grower"].astype(str) == selected_mode_grower
            ]

        if selected_version != "All" and "decfile_version" in filtered_batches.columns:
            filtered_batches = filtered_batches[
                filtered_batches["decfile_version"].astype(str) == selected_version
            ]

        defect_cols = [c for c in ["defect_1", "defect_2", "defect_3"] if c in filtered_batches.columns]
        if defect_cols:
            mode_defects = (
                filtered_batches[defect_cols]
                .melt(value_name="defect")["defect"]
                .dropna()
                .astype(str)
                .str.strip()
            )
            mode_defects = mode_defects[mode_defects != ""]
            if not mode_defects.empty:
                top_defects_mode = mode_defects.value_counts().reset_index()
                top_defects_mode.columns = ["Defect", "Count"]

    if not top_defects_mode.empty:
        st.dataframe(top_defects_mode, use_container_width=True, height=360)
    else:
        st.info("No defect data available for the current filters.")

st.markdown("---")

# ============================================================
# STEP 1
# ============================================================
section_title("Step 1 — Select the defect to investigate")

available_reason_items = []
if "reason" in filtered_mode.columns:
    split_reasons = (
        filtered_mode["reason"]
        .dropna()
        .astype(str)
        .str.split(",")
        .explode()
        .astype(str)
        .str.strip()
    )
    split_reasons = split_reasons[split_reasons != ""]
    available_reason_items = sorted(split_reasons.unique().tolist())

selected_reason = st.selectbox(
    "Select defect / reason",
    ["All"] + available_reason_items,
    key="mode_reason_selector"
)

related_modes = pd.DataFrame()

if selected_reason != "All":
    reason_related_df = filtered_mode.copy()

    reason_related_df["reason_item"] = (
        reason_related_df["reason"]
        .fillna("")
        .astype(str)
        .str.split(",")
    )
    reason_related_df = reason_related_df.explode("reason_item")
    reason_related_df["reason_item"] = reason_related_df["reason_item"].astype(str).str.strip()

    reason_related_df = reason_related_df[
        reason_related_df["reason_item"] == selected_reason
    ].copy()

    if not reason_related_df.empty:
        rows = []
        for keys, grp in reason_related_df.groupby(["mode", "check_class"], dropna=False):
            mode_name = keys[0]
            check_class = keys[1]

            _, allb = summarize_boundaries(grp["boundary_after"]) if "boundary_after" in grp.columns else ("", "")

            sensitivity_text = ""
            if "sensitivity" in grp.columns:
                sensitivity_vals = sorted(set(grp["sensitivity"].dropna().astype(str)))
                sensitivity_text = ", ".join(sensitivity_vals)

            accuracy_text = ""
            if "accuracy" in grp.columns:
                accuracy_vals = sorted(set(grp["accuracy"].dropna().astype(str)))
                accuracy_text = ", ".join(accuracy_vals)

            rows.append({
                "Mode": mode_name,
                "Check Class": check_class,
                "Count": len(grp),
                "Reference Boundaries": allb,
                "Sensitivity": sensitivity_text,
                "Accuracy": accuracy_text
            })

        related_modes = (
            pd.DataFrame(rows)
            .sort_values(["Count", "Mode"], ascending=[False, True])
            .reset_index(drop=True)
        )

        st.dataframe(related_modes, use_container_width=True, height=260)
    else:
        st.info("No related modes found for this defect / reason.")
else:
    st.info("Choose a defect / reason above to see related modes.")

st.markdown("---")

# ============================================================
# STEP 2
# ============================================================
section_title("Step 2 — Review what this mode can also detect")

mode_options_from_reason = []
if not related_modes.empty and "Mode" in related_modes.columns:
    mode_options_from_reason = related_modes["Mode"].dropna().astype(str).unique().tolist()

selected_related_mode = st.selectbox(
    "Select a mode from the results",
    ["All"] + sorted(mode_options_from_reason),
    key="mode_related_mode_selector"
)

if selected_related_mode != "All":
    selected_mode_rows = filtered_mode[
        filtered_mode["mode"].astype(str) == selected_related_mode
    ].copy()

    other_reason_counts = pd.DataFrame(columns=["Recorded Reason", "Count"])

    if "reason" in selected_mode_rows.columns:
        split_mode_reasons = (
            selected_mode_rows["reason"]
            .dropna()
            .astype(str)
            .str.split(",")
            .explode()
            .astype(str)
            .str.strip()
        )
        split_mode_reasons = split_mode_reasons[split_mode_reasons != ""]

        if not split_mode_reasons.empty:
            other_reason_counts = split_mode_reasons.value_counts().reset_index()
            other_reason_counts.columns = ["Recorded Reason", "Count"]

    if not other_reason_counts.empty:
        card_cols = st.columns(3)
        for idx, row in other_reason_counts.iterrows():
            col = card_cols[idx % 3]
            with col:
                st.markdown(
                    f"""
                    <div class="mode-card">
                        <div class="mode-card-title">{row['Recorded Reason']}</div>
                        <div class="mode-card-meta">Count: {int(row['Count'])}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
    else:
        st.info("No other recorded reasons found for this mode.")
else:
    st.info("Select one mode above to see what else it is able to detect.")

st.markdown("---")

# ============================================================
# STEP 3
# ============================================================
section_title("Step 3 — Review unchecked modes for this grower")

next_modes_table = pd.DataFrame(
    columns=[
        "Check",
        "Mode",
        "Check Class",
        "Count",
        "Reference Boundaries",
        "Sensitivity",
        "Accuracy"
    ]
)

if selected_mode_variety != "All" and selected_mode_grower != "All":
    variety_mode_db = mode_df.copy()

    if "variety" in variety_mode_db.columns:
        variety_mode_db = variety_mode_db[
            variety_mode_db["variety"].astype(str) == selected_mode_variety
        ]

    if selected_version != "All" and "decfile_version" in variety_mode_db.columns:
        variety_mode_db = variety_mode_db[
            variety_mode_db["decfile_version"].astype(str) == selected_version
        ]

    grower_mode_db = variety_mode_db.copy()
    if "grower" in grower_mode_db.columns:
        grower_mode_db = grower_mode_db[
            grower_mode_db["grower"].astype(str) == selected_mode_grower
        ]

    checked_pairs = set()
    if not grower_mode_db.empty:
        for keys, grp in grower_mode_db.groupby(["mode", "check_class"], dropna=False):
            checked_pairs.add((str(keys[0]), str(keys[1])))

    rows = []
    if not variety_mode_db.empty:
        for keys, grp in variety_mode_db.groupby(["mode", "check_class"], dropna=False):
            mode_name = str(keys[0])
            check_class = str(keys[1])

            if (mode_name, check_class) in checked_pairs:
                continue

            _, allb = summarize_boundaries(grp["boundary_after"]) if "boundary_after" in grp.columns else ("", "")

            sensitivity_text = ""
            if "sensitivity" in grp.columns:
                sensitivity_vals = sorted(set(grp["sensitivity"].dropna().astype(str)))
                sensitivity_text = ", ".join(sensitivity_vals)

            accuracy_text = ""
            if "accuracy" in grp.columns:
                accuracy_vals = sorted(set(grp["accuracy"].dropna().astype(str)))
                accuracy_text = ", ".join(accuracy_vals)

            rows.append({
                "Check": False,
                "Mode": mode_name,
                "Check Class": check_class,
                "Count": len(grp),
                "Reference Boundaries": allb,
                "Sensitivity": sensitivity_text,
                "Accuracy": accuracy_text
            })

    if rows:
        next_modes_table = (
            pd.DataFrame(rows)
            .sort_values(["Count", "Mode", "Check Class"], ascending=[False, True, True])
            .reset_index(drop=True)
        )

if selected_mode_variety == "All" or selected_mode_grower == "All":
    st.info("Choose a specific variety and grower to see which modes are not yet checked for this grower.")
elif not next_modes_table.empty:
    st.data_editor(
        next_modes_table,
        use_container_width=True,
        height=300,
        hide_index=True,
        column_config={"Check": st.column_config.CheckboxColumn("Check")},
        disabled=["Mode", "Check Class", "Count", "Reference Boundaries", "Sensitivity", "Accuracy"]
    )
else:
    st.info("No additional unchecked modes found for this grower under the selected variety.")
