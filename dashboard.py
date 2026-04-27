import os
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Presizing Dashboard", layout="wide")
st.title("Presizing Dashboard")

# -----------------------------
# Helpers
# -----------------------------
@st.cache_data
def load_csv(filename):
    if os.path.exists(filename):
        return pd.read_csv(filename)
    return None

def summarize_boundaries(series):
    vals = series.dropna().astype(str).str.strip()
    vals = vals[vals != ""]
    if vals.empty:
        return "", ""

    counts = vals.value_counts()
    top_3 = ", ".join(counts.head(3).index.tolist())

    def sort_key(x):
        try:
            return float(x)
        except Exception:
            return float("inf")

    all_sorted = ", ".join(sorted(vals.unique().tolist(), key=sort_key))
    return top_3, all_sorted

# -----------------------------
# Load data
# -----------------------------
runs = load_csv("runs_raw.csv")
batches = load_csv("batches_raw.csv")
changes = load_csv("changes_raw.csv")
downtime = load_csv("downtime_raw.csv")

if runs is None:
    st.error("runs_raw.csv not found.")
    st.stop()

# -----------------------------
# Clean runs_raw
# -----------------------------
runs["run_date_raw"] = runs["run_date"].astype(str).str.strip()

date_try_1 = pd.to_datetime(runs["run_date_raw"], dayfirst=True, errors="coerce")
date_try_2 = pd.to_datetime(runs["run_date_raw"], yearfirst=True, errors="coerce")
runs["run_date"] = date_try_1.fillna(date_try_2)

runs = runs.dropna(subset=["run_date"]).copy()

for col in ["receival_date_min", "receival_date_max"]:
    if col in runs.columns:
        runs[col] = pd.to_datetime(runs[col].astype(str).str.strip(), dayfirst=True, errors="coerce")

numeric_cols_runs = [
    "batch_id",
    "bins_run",
    "retip",
    "premium_rate",
    "c1_color_rate",
    "c1_quality_rate",
    "c2_color_rate",
    "c2_quality_rate",
    "no_color_rate",
    "juice_rate",
    "test_drop_count",
    "test_drop_kg",
    "Speed_12",
    "Speed_34",
    "Speed_56",
    "full_speed"
]

for col in numeric_cols_runs:
    if col in runs.columns:
        runs[col] = pd.to_numeric(runs[col], errors="coerce")

speed_cols = [c for c in ["Speed_12", "Speed_34", "Speed_56", "full_speed"] if c in runs.columns]

# -----------------------------
# Clean batches_raw
# -----------------------------
if batches is not None:
    for col in ["receival_date_min", "receival_date_max"]:
        if col in batches.columns:
            batches[col] = pd.to_datetime(batches[col].astype(str).str.strip(), dayfirst=True, errors="coerce")

    for col in ["batch_id", "premium", "premium%"]:
        if col in batches.columns:
            batches[col] = pd.to_numeric(batches[col], errors="coerce")

# -----------------------------
# Clean changes_raw
# -----------------------------
if changes is not None:
    changes = changes.drop(columns=[c for c in changes.columns if c.startswith("Unnamed")], errors="ignore")

    if "change_time" in changes.columns:
        changes["change_time"] = pd.to_datetime(changes["change_time"], errors="coerce")

    for col in ["boundary_before", "boundary_after"]:
        if col in changes.columns:
            changes[col] = pd.to_numeric(changes[col], errors="coerce")

# -----------------------------
# Clean downtime_raw
# -----------------------------
if downtime is not None:
    if "run_date" in downtime.columns:
        downtime["run_date_raw"] = downtime["run_date"].astype(str).str.strip()
        dt_try_1 = pd.to_datetime(downtime["run_date_raw"], dayfirst=True, errors="coerce")
        dt_try_2 = pd.to_datetime(downtime["run_date_raw"], yearfirst=True, errors="coerce")
        downtime["run_date"] = dt_try_1.fillna(dt_try_2)

    if "duration_minutes" in downtime.columns:
        downtime["duration_minutes"] = pd.to_numeric(downtime["duration_minutes"], errors="coerce")

# -----------------------------
# Tabs
# -----------------------------
tab_summary, tab_quality, tab_mode = st.tabs(["Summary", "Quality", "Mode"])

# =========================================================
# SUMMARY TAB
# =========================================================
with tab_summary:
    st.header("Summary")

    period_choice = st.radio(
        "Period Type",
        ["Yearly", "Monthly", "Weekly"],
        horizontal=True
    )

    summary_df = runs.copy()
    summary_df = summary_df.dropna(subset=["run_date"]).copy()

    # =========================
    # YEARLY VIEW
    # =========================
    if period_choice == "Yearly":
        summary_df["year"] = summary_df["run_date"].dt.year.astype(int)

        available_years = sorted(summary_df["year"].dropna().unique().tolist(), reverse=True)
        selected_year = st.selectbox("Select Year", available_years)

        chart_df = (
            summary_df.groupby("year", as_index=False)["bins_run"]
            .sum()
            .sort_values("year")
        )

        summary_filtered = summary_df[summary_df["year"] == selected_year].copy()
        selected_period_label = str(selected_year)

        left1, left2, right = st.columns([2.2, 1.7, 1])

        with left1:
            st.subheader("Total Bin Run Chart")
            fig = px.bar(
                chart_df,
                x="year",
                y="bins_run",
                labels={"year": "Year", "bins_run": "Total Bins"},
                title="Total Bin Run Chart"
            )
            fig.update_xaxes(type="category")
            st.plotly_chart(fig, use_container_width=True)

    # =========================
    # MONTHLY VIEW
    # =========================
    elif period_choice == "Monthly":
        summary_df["year"] = summary_df["run_date"].dt.year.astype(int)
        summary_df["month_num"] = summary_df["run_date"].dt.month
        summary_df["month_name"] = summary_df["run_date"].dt.strftime("%b")
        summary_df["month_label"] = summary_df["run_date"].dt.to_period("M").astype(str)

        available_years = sorted(summary_df["year"].dropna().unique().tolist(), reverse=True)
        selected_year = st.selectbox("Select Year", available_years)

        year_df = summary_df[summary_df["year"] == selected_year].copy()

        available_months = (
            year_df["month_label"]
            .dropna()
            .drop_duplicates()
            .sort_values()
            .tolist()
        )
        selected_month = st.selectbox("Select Month", available_months)

        compare_df = (
            summary_df.groupby(["year", "month_num", "month_name"], as_index=False)["bins_run"]
            .sum()
            .sort_values(["month_num", "year"])
        )

        summary_filtered = year_df[year_df["month_label"] == selected_month].copy()
        selected_period_label = selected_month

        left1, left2, right = st.columns([2.2, 1.7, 1])

        with left1:
            st.subheader("Total Bin Run Chart")

            fig = px.line(
                compare_df,
                x="month_name",
                y="bins_run",
                color="year",
                markers=True,
                category_orders={
                    "month_name": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                },
                labels={"month_name": "Month", "bins_run": "Total Bins", "year": "Year"},
                title="Monthly Comparison by Year"
            )

            for trace in fig.data:
                if str(trace.name) == str(selected_year):
                    trace.line.width = 4
                else:
                    trace.line.width = 2

            st.plotly_chart(fig, use_container_width=True)
    # =========================
    # WEEKLY VIEW
    # =========================
    elif period_choice == "Weekly":
        summary_df["month_label"] = summary_df["run_date"].dt.to_period("M").astype(str)
        summary_df["week_start"] = summary_df["run_date"] - pd.to_timedelta(summary_df["run_date"].dt.weekday, unit="D")
        summary_df["week_label"] = "W/C " + summary_df["week_start"].dt.strftime("%Y-%m-%d")

        available_months = (
            summary_df["month_label"]
            .dropna()
            .drop_duplicates()
            .sort_values()
            .tolist()
        )
        selected_month = st.selectbox("Select Month", available_months)

        month_df = summary_df[summary_df["month_label"] == selected_month].copy()

        available_weeks = (
            month_df[["week_label", "week_start"]]
            .drop_duplicates()
            .sort_values("week_start")["week_label"]
            .tolist()
        )
        selected_week = st.selectbox("Select Week", available_weeks)

        chart_df = (
            month_df.groupby(["week_label", "week_start"], as_index=False)["bins_run"]
            .sum()
            .sort_values("week_start")
        )

        summary_filtered = month_df[month_df["week_label"] == selected_week].copy()
        selected_period_label = selected_week

        left1, left2, right = st.columns([2.2, 1.7, 1])

        with left1:
            st.subheader("Total Bin Run Chart")
            fig = px.bar(
                chart_df,
                x="week_label",
                y="bins_run",
                labels={"week_label": "Week", "bins_run": "Total Bins"},
                title="Total Bin Run Chart"
            )
            st.plotly_chart(fig, use_container_width=True)

    # =========================
    # SHARED SUMMARY BLOCK
    # =========================
    bins_by_variety = (
        summary_filtered.groupby("variety", as_index=False)["bins_run"]
        .sum()
        .sort_values("bins_run", ascending=False)
    )

    avg_speed = None
    if speed_cols:
        avg_speed = summary_filtered[speed_cols].stack().mean()

    total_retip = summary_filtered["retip"].sum() if "retip" in summary_filtered.columns else None

    with left2:
        st.subheader(f"Total Bin Variety ({selected_period_label})")
        st.dataframe(
            bins_by_variety.rename(columns={"bins_run": "total_bins"}),
            use_container_width=True,
            height=260
        )

    with right:
        st.subheader("Average Speed")
        st.metric("Bins / Hour", f"{avg_speed:.1f}" if pd.notna(avg_speed) else "N/A")

        st.subheader("Total Retip")
        st.metric("Retip", f"{int(total_retip)}" if pd.notna(total_retip) else "N/A")

    # =========================
    # VARIETY SUMMARY BLOCK
    # =========================
    st.divider()
    st.subheader("Variety Summary Within Selected Period")

    available_varieties = sorted(summary_filtered["variety"].dropna().astype(str).unique().tolist())
    selected_summary_variety = st.selectbox(
        "Select Variety",
        available_varieties if available_varieties else ["No Variety Available"],
        key="summary_variety"
    )

    variety_filtered = summary_filtered.copy()
    if available_varieties:
        variety_filtered = variety_filtered[
            variety_filtered["variety"].astype(str) == selected_summary_variety
        ]

    total_bin_variety = variety_filtered["bins_run"].sum() if "bins_run" in variety_filtered.columns else None

    bins_by_grower_variety = (
        variety_filtered.groupby("grower", as_index=False)["bins_run"]
        .sum()
        .sort_values("bins_run", ascending=False)
    )

    avg_speed_variety = None
    if speed_cols:
        avg_speed_variety = variety_filtered[speed_cols].stack().mean()

    total_retip_variety = variety_filtered["retip"].sum() if "retip" in variety_filtered.columns else None

    if period_choice == "Yearly":
        variety_chart_base = summary_df.copy()
        variety_chart_df = (
            variety_chart_base[variety_chart_base["variety"].astype(str) == selected_summary_variety]
            .groupby("year", as_index=False)["bins_run"]
            .sum()
            .sort_values("year")
        )
        x_col = "year"
        chart_kind = "bar"

    elif period_choice == "Monthly":
        variety_chart_base = summary_df[summary_df["year"] == selected_year].copy()
        variety_chart_df = (
            variety_chart_base[variety_chart_base["variety"].astype(str) == selected_summary_variety]
            .groupby("month_label", as_index=False)["bins_run"]
            .sum()
            .sort_values("month_label")
        )
        x_col = "month_label"
        chart_kind = "line"

    else:
        variety_chart_base = summary_df[summary_df["month_label"] == selected_month].copy()
        variety_chart_df = (
            variety_chart_base[variety_chart_base["variety"].astype(str) == selected_summary_variety]
            .groupby(["week_label", "week_start"], as_index=False)["bins_run"]
            .sum()
            .sort_values("week_start")
        )
        x_col = "week_label"
        chart_kind = "bar"

    vleft1, vleft2, vright = st.columns([2.2, 1.7, 1])

    with vleft1:
        st.subheader("Total Bin Run")
        if chart_kind == "bar":
            fig_v = px.bar(
                variety_chart_df,
                x=x_col,
                y="bins_run",
                labels={x_col: x_col.replace("_", " ").title(), "bins_run": "Total Bins"},
                title="Variety Total Bin Run"
            )
        else:
            fig_v = px.line(
                variety_chart_df,
                x=x_col,
                y="bins_run",
                markers=True,
                labels={x_col: x_col.replace("_", " ").title(), "bins_run": "Total Bins"},
                title="Variety Total Bin Run"
            )
        st.plotly_chart(fig_v, use_container_width=True)

    with vleft2:
        st.subheader("Total Bin by Grower")
        st.dataframe(
            bins_by_grower_variety.rename(columns={"bins_run": "total_bins"}),
            use_container_width=True,
            height=260
        )

    with vright:
        st.subheader("Average Speed")
        st.metric("Bins / Hour", f"{avg_speed_variety:.1f}" if pd.notna(avg_speed_variety) else "N/A")

        st.subheader("Retip")
        st.metric("Retip", f"{int(total_retip_variety)}" if pd.notna(total_retip_variety) else "N/A")

    # =========================
    # DOWNTIME MINI SECTION
    # =========================
    st.divider()
    st.subheader("Downtime Summary")

    if downtime is not None and "run_date" in downtime.columns:
        downtime_df = downtime.copy()
        downtime_df = downtime_df.dropna(subset=["run_date"]).copy()

        if period_choice == "Yearly":
            downtime_df["year"] = downtime_df["run_date"].dt.year.astype(int)
            downtime_filtered = downtime_df[downtime_df["year"] == selected_year].copy()

        elif period_choice == "Monthly":
            downtime_df["year"] = downtime_df["run_date"].dt.year.astype(int)
            downtime_df["month_label"] = downtime_df["run_date"].dt.to_period("M").astype(str)
            downtime_filtered = downtime_df[downtime_df["month_label"] == selected_month].copy()

        else:
            downtime_df["month_label"] = downtime_df["run_date"].dt.to_period("M").astype(str)
            downtime_df["week_start"] = downtime_df["run_date"] - pd.to_timedelta(downtime_df["run_date"].dt.weekday, unit="D")
            downtime_df["week_label"] = "W/C " + downtime_df["week_start"].dt.strftime("%Y-%m-%d")
            downtime_filtered = downtime_df[downtime_df["week_label"] == selected_week].copy()

        total_downtime = downtime_filtered["duration_minutes"].sum() if "duration_minutes" in downtime_filtered.columns else None

        top_area = "N/A"
        if "downtime_area" in downtime_filtered.columns:
            area_counts = downtime_filtered["downtime_area"].dropna().astype(str).value_counts()
            if not area_counts.empty:
                top_area = area_counts.index[0]

        top_reason = "N/A"
        if "downtime_reason" in downtime_filtered.columns:
            reason_counts = downtime_filtered["downtime_reason"].dropna().astype(str).value_counts()
            if not reason_counts.empty:
                top_reason = reason_counts.index[0]

        dt1, dt2, dt3 = st.columns(3)

        with dt1:
            st.metric("Total Downtime (mins)", f"{int(total_downtime)}" if pd.notna(total_downtime) else "N/A")

        with dt2:
            st.metric("Top Downtime Area", top_area)

        with dt3:
            st.metric("Top Downtime Reason", top_reason)
    else:
        st.info("No downtime data available.")

# =========================================================
# QUALITY TAB
# =========================================================
with tab_quality:
    st.header("Quality")

    # Build month list from runs
    quality_runs = runs.copy()
    quality_runs["month_label"] = quality_runs["run_date"].dt.to_period("M").astype(str)

    # -----------------------------
    # Filters + Preview
    # -----------------------------
    q1, q2 = st.columns([1, 2])

    with q1:
        selected_variety = st.selectbox(
            "Variety",
            ["All"] + sorted(quality_runs["variety"].dropna().astype(str).unique().tolist()),
            key="quality_variety"
        )

        selected_grower = st.selectbox(
            "Grower",
            ["All"] + sorted(quality_runs["grower"].dropna().astype(str).unique().tolist()),
            key="quality_grower"
        )

        selected_quality_month = st.selectbox(
            "Month",
            ["All"] + sorted(quality_runs["month_label"].dropna().astype(str).unique().tolist(), reverse=True),
            key="quality_month"
        )

    quality_filtered = quality_runs.copy()

    if selected_variety != "All":
        quality_filtered = quality_filtered[
            quality_filtered["variety"].astype(str) == selected_variety
        ]

    if selected_grower != "All":
        quality_filtered = quality_filtered[
            quality_filtered["grower"].astype(str) == selected_grower
        ]

    if selected_quality_month != "All":
        quality_filtered = quality_filtered[
            quality_filtered["month_label"].astype(str) == selected_quality_month
        ]

    with q2:
        st.subheader("Filtered Data Preview")
        preview_cols = [
            c for c in [
                "run_date", "run_id", "grower", "variety", "batch_id",
                "bins_run", "premium_rate", "juice_rate", "test_drop_count", "notes_run"
            ] if c in quality_filtered.columns
        ]
        st.dataframe(
            quality_filtered[preview_cols].head(20),
            use_container_width=True,
            height=240
        )

    # -----------------------------
    # Quality Metrics + Chart
    # -----------------------------
    st.subheader("Quality Overview")

    quality_cols = [
        "premium_rate",
        "c1_color_rate",
        "c1_quality_rate",
        "c2_color_rate",
        "c2_quality_rate",
        "no_color_rate",
        "juice_rate",
        "test_drop_count"
    ]
    quality_cols = [c for c in quality_cols if c in quality_filtered.columns]

    label_map = {
        "premium_rate": "Premium",
        "c1_color_rate": "C1 Color",
        "c1_quality_rate": "C1 Quality",
        "c2_color_rate": "C2 Color",
        "c2_quality_rate": "C2 Quality",
        "no_color_rate": "No Color",
        "juice_rate": "Juice",
        "test_drop_count": "Test Drops"
    }

    quality_summary = pd.DataFrame(columns=["metric", "average_value", "metric_label"])

    if quality_cols:
        quality_summary = (
            quality_filtered[quality_cols]
            .mean()
            .dropna()
            .reset_index()
        )
        quality_summary.columns = ["metric", "average_value"]
        quality_summary["metric_label"] = quality_summary["metric"].map(label_map)

    c1, c2 = st.columns([1.2, 1.8])

    with c1:
        if not quality_summary.empty:
            st.dataframe(
                quality_summary[["metric_label", "average_value"]].rename(
                    columns={"metric_label": "metric"}
                ),
                use_container_width=True,
                height=260
            )
        else:
            st.info("No quality values available for this filter selection.")

    with c2:
        rate_metrics = [
            "premium_rate",
            "c1_color_rate",
            "c1_quality_rate",
            "c2_color_rate",
            "c2_quality_rate",
            "no_color_rate",
            "juice_rate"
        ]

        if not quality_summary.empty:
            rate_chart_df = quality_summary[
                quality_summary["metric"].isin(rate_metrics)
            ].copy()

            if not rate_chart_df.empty:
                fig_q = px.bar(
                    rate_chart_df,
                    x="metric_label",
                    y="average_value",
                    labels={"metric_label": "Metric", "average_value": "Average Rate"},
                    title="Quality Rate Overview"
                )
                st.plotly_chart(fig_q, use_container_width=True)

                metric_lookup = dict(zip(quality_summary["metric"], quality_summary["average_value"]))
                juice_val = metric_lookup.get("juice_rate", None)
                color_loss = metric_lookup.get("c1_color_rate", None)
                quality_loss = metric_lookup.get("c1_quality_rate", None)

                insight_parts = []

                if pd.notna(juice_val):
                    insight_parts.append(f"Juice avg: {juice_val:.2f}")

                if pd.notna(color_loss) and pd.notna(quality_loss):
                    if color_loss > quality_loss:
                        insight_parts.append("Color loss is higher than quality loss")
                    elif quality_loss > color_loss:
                        insight_parts.append("Quality loss is higher than color loss")
                    else:
                        insight_parts.append("Color and quality loss are similar")

                if insight_parts:
                    st.info(" | ".join(insight_parts))
        else:
            st.info("No chart data available.")

    # -----------------------------
    # Defects + Modes
    # -----------------------------
    st.subheader("Defects and Modes")

    top_defects = pd.DataFrame(columns=["defect", "count"])
    top_adjusted = pd.DataFrame(columns=["mode", "count"])
    top_checked = pd.DataFrame(columns=["mode", "count"])

    if batches is not None:
        batch_filtered = batches.copy()

        if "receival_date_min" in batch_filtered.columns:
            batch_filtered["month_label"] = batch_filtered["receival_date_min"].dt.to_period("M").astype(str)

        if selected_variety != "All" and "variety" in batch_filtered.columns:
            batch_filtered = batch_filtered[
                batch_filtered["variety"].astype(str) == selected_variety
            ]

        if selected_grower != "All" and "grower" in batch_filtered.columns:
            batch_filtered = batch_filtered[
                batch_filtered["grower"].astype(str) == selected_grower
            ]

        if selected_quality_month != "All" and "month_label" in batch_filtered.columns:
            batch_filtered = batch_filtered[
                batch_filtered["month_label"].astype(str) == selected_quality_month
            ]

        defect_cols = [c for c in ["defect_1", "defect_2", "defect_3"] if c in batch_filtered.columns]
        if defect_cols:
            defect_values = (
                batch_filtered[defect_cols]
                .melt(value_name="defect")["defect"]
                .dropna()
                .astype(str)
                .str.strip()
            )
            defect_values = defect_values[defect_values != ""]
            if not defect_values.empty:
                top_defects = defect_values.value_counts().reset_index()
                top_defects.columns = ["defect", "count"]

    if changes is not None:
        changes_filtered = changes.copy()

        if selected_variety != "All" and "variety" in changes_filtered.columns:
            changes_filtered = changes_filtered[
                changes_filtered["variety"].astype(str) == selected_variety
            ]

        # link month and grower using run_ids from already filtered runs
        run_ids = quality_filtered["run_id"].dropna().astype(str).unique().tolist()
        if "run_id" in changes_filtered.columns:
            changes_filtered = changes_filtered[
                changes_filtered["run_id"].astype(str).isin(run_ids)
            ]

        if "mode" in changes_filtered.columns and "action" in changes_filtered.columns:
            adjusted = changes_filtered[
                changes_filtered["action"].astype(str).str.lower().str.startswith("a")
            ]
            checked = changes_filtered[
                changes_filtered["action"].astype(str).str.lower().str.startswith("c")
            ]

            if not adjusted.empty:
                top_adjusted = adjusted["mode"].astype(str).value_counts().reset_index()
                top_adjusted.columns = ["mode", "count"]

            if not checked.empty:
                top_checked = checked["mode"].astype(str).value_counts().reset_index()
                top_checked.columns = ["mode", "count"]

    d1, d2, d3 = st.columns(3)

    with d1:
        st.subheader("Top 3 Defects")
        if not top_defects.empty:
            st.dataframe(top_defects.head(3), use_container_width=True, height=220)
        else:
            st.info("No defect data available.")

    with d2:
        st.subheader("Top 5 Adjusted Modes")
        if not top_adjusted.empty:
            st.dataframe(top_adjusted.head(5), use_container_width=True, height=220)
        else:
            st.info("No adjusted mode data available.")

    with d3:
        st.subheader("Top 5 Checked Modes")
        if not top_checked.empty:
            st.dataframe(top_checked.head(5), use_container_width=True, height=220)
        else:
            st.info("No checked mode data available.")

# =========================================================
# MODE TAB
# =========================================================
with tab_mode:
    st.header("Mode")

    if changes is None:
        st.info("changes_raw.csv not found.")
    else:
        mode_df = changes.copy()

        # Link changes -> runs
        if "run_id" in mode_df.columns and "run_id" in runs.columns:
            mode_df = mode_df.merge(
                runs[["run_id", "batch_id", "grower", "variety", "run_date"]],
                on="run_id",
                how="left",
                suffixes=("", "_run")
            )

        # Link runs -> batches
        if batches is not None and "batch_id" in mode_df.columns and "batch_id" in batches.columns:
            batch_link_cols = [
                c for c in ["batch_id", "decfile_version", "defect_1", "defect_2", "defect_3"]
                if c in batches.columns
            ]
            mode_df = mode_df.merge(
                batches[batch_link_cols],
                on="batch_id",
                how="left"
            )

        # -----------------------------
        # Filters
        # -----------------------------
        f1, f2, f3 = st.columns(3)

        with f1:
            available_varieties = ["All"]
            if "variety" in mode_df.columns:
                available_varieties += sorted(
                    mode_df["variety"].dropna().astype(str).unique().tolist()
                )

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

        with f2:
            available_growers = ["All"]
            if "grower" in filtered_mode.columns:
                available_growers += sorted(
                    filtered_mode["grower"].dropna().astype(str).unique().tolist()
                )

            selected_mode_grower = st.selectbox(
                "Grower",
                available_growers,
                key="mode_grower_selector"
            )

        if selected_mode_grower != "All" and "grower" in filtered_mode.columns:
            filtered_mode = filtered_mode[
                filtered_mode["grower"].astype(str) == selected_mode_grower
            ]

        with f3:
            available_versions = ["All"]
            if "decfile_version" in filtered_mode.columns:
                version_values = filtered_mode["decfile_version"].dropna().astype(str).unique().tolist()
                available_versions += sorted(version_values)

            selected_version = st.selectbox(
                "Version",
                available_versions,
                key="mode_version_selector"
            )

        if selected_version != "All" and "decfile_version" in filtered_mode.columns:
            filtered_mode = filtered_mode[
                filtered_mode["decfile_version"].astype(str) == selected_version
            ]

        # -----------------------------
        # Top defects table
        # -----------------------------
        st.subheader("Top Defects")

        top_defects_mode = pd.DataFrame(columns=["defect", "count"])

        defect_cols_mode = [c for c in ["defect_1", "defect_2", "defect_3"] if c in filtered_mode.columns]
        if defect_cols_mode:
            mode_defects = (
                filtered_mode[defect_cols_mode]
                .melt(value_name="defect")["defect"]
                .dropna()
                .astype(str)
                .str.strip()
            )
            mode_defects = mode_defects[mode_defects != ""]
            if not mode_defects.empty:
                top_defects_mode = mode_defects.value_counts().reset_index()
                top_defects_mode.columns = ["defect", "count"]

        if not top_defects_mode.empty:
            st.dataframe(top_defects_mode, use_container_width=True, height=240)
        else:
            st.info("No defect data available for the current filters.")

        # -----------------------------
        # Top adjusted mode table
        # -----------------------------
        st.subheader("Top Adjusted Modes")

        adjusted_mode_table = pd.DataFrame(columns=["mode", "check_class", "count", "all_boundaries"])

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

                    rows.append({
                        "mode": mode_name,
                        "check_class": check_class,
                        "count": len(grp),
                        "all_boundaries": allb
                    })

                adjusted_mode_table = (
                    pd.DataFrame(rows)
                    .sort_values(["count", "mode", "check_class"], ascending=[False, True, True])
                )

        if not adjusted_mode_table.empty:
            st.dataframe(adjusted_mode_table, use_container_width=True, height=320)
        else:
            st.info("No adjusted mode data available for the current filters.")

        # -----------------------------
        # Defect selector from reasons
        # -----------------------------
        st.subheader("Defect Selector from Recorded Reasons")

        reason_mode_df = filtered_mode.copy()

        available_reason_defects = []
        if "reason" in reason_mode_df.columns:
            split_reasons = (
                reason_mode_df["reason"]
                .fillna("")
                .astype(str)
                .str.split(",")
                .explode()
                .astype(str)
                .str.strip()
            )
            split_reasons = split_reasons[split_reasons != ""]
            available_reason_defects = sorted(split_reasons.dropna().unique().tolist())

        selected_reason_defect = st.selectbox(
            "Select defect from recorded reasons",
            ["All"] + available_reason_defects,
            key="mode_reason_defect_selector"
        )

        if selected_reason_defect != "All" and "reason" in reason_mode_df.columns and "mode" in reason_mode_df.columns:
            reason_mode_df["reason_split"] = (
                reason_mode_df["reason"]
                .fillna("")
                .astype(str)
                .str.split(",")
            )
            reason_mode_df = reason_mode_df.explode("reason_split")
            reason_mode_df["reason_split"] = reason_mode_df["reason_split"].astype(str).str.strip()

            matched_df = reason_mode_df[
                reason_mode_df["reason_split"].astype(str) == selected_reason_defect
            ].copy()

            if not matched_df.empty:
                related_modes = (
                    matched_df.groupby(["mode", "check_class"], as_index=False)
                    .agg(
                        count=("mode", "size"),
                        boundaries=("boundary_after", lambda x: ", ".join(sorted(set(x.dropna().astype(str)))))
                    )
                    .sort_values(["count", "mode"], ascending=[False, True])
                )

                st.write(f"Modes related to: {selected_reason_defect}")
                st.dataframe(related_modes, use_container_width=True, height=260)
            else:
                st.info("No matching modes found for this defect.")
        else:
            st.write("Choose a defect above to see related modes.")

        # -----------------------------
        # Mode filter to show reasons
        # -----------------------------
        st.subheader("Mode Reasons")

        available_modes_bottom = []
        if "mode" in filtered_mode.columns:
            available_modes_bottom = sorted(filtered_mode["mode"].dropna().astype(str).unique().tolist())

        selected_mode_bottom = st.selectbox(
            "Select mode",
            ["All"] + available_modes_bottom,
            key="mode_reason_selector"
        )

        if selected_mode_bottom != "All" and "mode" in filtered_mode.columns:
            mode_reason_filtered = filtered_mode[
                filtered_mode["mode"].astype(str) == selected_mode_bottom
            ].copy()

            if "reason" in mode_reason_filtered.columns:
                reason_table = (
                    mode_reason_filtered["reason"]
                    .dropna()
                    .astype(str)
                    .str.strip()
                    .value_counts()
                    .reset_index()
                )
                reason_table.columns = ["reason", "count"]

                if not reason_table.empty:
                    st.dataframe(reason_table, use_container_width=True, height=260)
                else:
                    st.info("No reasons recorded for this mode.")
            else:
                st.info("No reason column available.")
        else:
            st.write("Choose a mode above to see its recorded reasons.")