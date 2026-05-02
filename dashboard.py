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

time_cols = ["start_time", "end_time"]
for col in time_cols:
    if col in runs.columns:
        runs[col] = runs[col].astype(str).str.strip()

if all(col in runs.columns for col in ["run_date", "start_time", "end_time"]):
    runs["start_dt"] = pd.to_datetime(
        runs["run_date"].dt.strftime("%Y-%m-%d") + " " + runs["start_time"],
        errors="coerce"
    )
    runs["end_dt"] = pd.to_datetime(
        runs["run_date"].dt.strftime("%Y-%m-%d") + " " + runs["end_time"],
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

    # numeric only for real numeric columns
    for col in ["boundary_before", "boundary_after"]:
        if col in changes.columns:
            changes[col] = pd.to_numeric(changes[col], errors="coerce")

    # text columns
    for col in ["reason", "mode", "check_class", "action", "variety", "sensitivity", "accuracy"]:
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
if downtime is not None:
    if "run_date" in downtime.columns:
        downtime["run_date_raw"] = downtime["run_date"].astype(str).str.strip()
        dt_try_1 = pd.to_datetime(downtime["run_date_raw"], dayfirst=True, errors="coerce")
        dt_try_2 = pd.to_datetime(downtime["run_date_raw"], yearfirst=True, errors="coerce")
        downtime["run_date"] = dt_try_1.fillna(dt_try_2)

    if "duration_hours" in downtime.columns:
        downtime["duration_hours"] = pd.to_numeric(downtime["duration_hours"], errors="coerce")

    for col in ["downtime_area", "downtime_reason"]:
        if col in downtime.columns:
            downtime[col] = (
                downtime[col]
                .fillna("")
                .astype(str)
                .str.strip()
                .replace("", pd.NA)
            )

# -----------------------------
# Tabs
# -----------------------------
tab_summary, tab_quality, tab_mode = st.tabs(["Summary", "Quality", "Mode"])

# =========================================================
# SUMMARY TAB
# =========================================================
with tab_summary:
    st.header("Summary")

    latest_date = runs["run_date"].max()
    top_info_left, top_info_right = st.columns([2, 1])

    with top_info_left:
        st.caption(
            f"Last updated: {latest_date.strftime('%Y-%m-%d')}"
            if pd.notna(latest_date) else "Last updated: N/A"
        )

    with top_info_right:
        st.caption("Overview of production, performance, and downtime")

    period_choice = st.radio(
        "Period Type",
        ["Yearly", "Monthly", "Weekly"],
        horizontal=True
    )

    summary_df = runs.copy()
    summary_df = summary_df.dropna(subset=["run_date"]).copy()

    def format_delta(current, previous, mode="number"):
        if pd.isna(current) or pd.isna(previous):
            return "N/A"

        if mode == "percent":
            if previous == 0:
                return "N/A"
            delta_pct = ((current - previous) / previous) * 100
            return f"{delta_pct:+.1f}% vs prev"

        if mode == "float":
            return f"{current - previous:+.1f} vs prev"

        return f"{int(current - previous):+,.0f} vs prev"

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

        prev_year = selected_year - 1
        previous_filtered = summary_df[summary_df["year"] == prev_year].copy()

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
        selected_month = st.selectbox("Select Month", ["All"] + available_months)

        chart_df = (
            summary_df.groupby(["year", "month_num", "month_name"], as_index=False)["bins_run"]
            .sum()
            .sort_values(["month_num", "year"], ascending=[True, False])
        )

        if selected_month == "All":
            summary_filtered = year_df.copy()
            selected_period_label = f"{selected_year} (All Months)"
            prev_month = None
            previous_filtered = pd.DataFrame()
        else:
            summary_filtered = year_df[year_df["month_label"] == selected_month].copy()
            selected_period_label = selected_month

            month_order = available_months
            current_idx = month_order.index(selected_month)
            prev_month = month_order[current_idx - 1] if current_idx > 0 else None
            previous_filtered = year_df[year_df["month_label"] == prev_month].copy() if prev_month else pd.DataFrame()

    # =========================
    # WEEKLY VIEW
    # =========================
    else:
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
        selected_month = st.selectbox("Select Month", ["All"] + available_months)

        if selected_month == "All":
            month_df = summary_df.copy()
        else:
            month_df = summary_df[summary_df["month_label"] == selected_month].copy()

        available_weeks = (
            month_df[["week_label", "week_start"]]
            .drop_duplicates()
            .sort_values("week_start")["week_label"]
            .tolist()
        )
        selected_week = st.selectbox("Select Week", ["All"] + available_weeks)

        chart_df = (
            month_df.groupby(["week_label", "week_start"], as_index=False)["bins_run"]
            .sum()
            .sort_values("week_start")
        )

        if selected_week == "All":
            summary_filtered = month_df.copy()
            if selected_month == "All":
                selected_period_label = "All Weeks"
            else:
                selected_period_label = f"{selected_month} (All Weeks)"
            prev_week = None
            previous_filtered = pd.DataFrame()
        else:
            summary_filtered = month_df[month_df["week_label"] == selected_week].copy()
            selected_period_label = selected_week

            week_order = available_weeks
            current_idx = week_order.index(selected_week)
            prev_week = week_order[current_idx - 1] if current_idx > 0 else None
            previous_filtered = month_df[month_df["week_label"] == prev_week].copy() if prev_week else pd.DataFrame()

    # =========================
    # DOWNTIME FILTER FOR CURRENT PERIOD
    # =========================
    current_downtime = None
    prev_downtime = None
    downtime_filtered = pd.DataFrame()

    if downtime is not None and "run_date" in downtime.columns:
        downtime_df_for_kpi = downtime.copy().dropna(subset=["run_date"]).copy()

        if period_choice == "Yearly":
            downtime_df_for_kpi["year"] = downtime_df_for_kpi["run_date"].dt.year.astype(int)
            current_dt_filtered = downtime_df_for_kpi[downtime_df_for_kpi["year"] == selected_year].copy()
            prev_dt_filtered = downtime_df_for_kpi[downtime_df_for_kpi["year"] == prev_year].copy()

        elif period_choice == "Monthly":
            downtime_df_for_kpi["year"] = downtime_df_for_kpi["run_date"].dt.year.astype(int)
            downtime_df_for_kpi["month_label"] = downtime_df_for_kpi["run_date"].dt.to_period("M").astype(str)

            if selected_month == "All":
                current_dt_filtered = downtime_df_for_kpi[downtime_df_for_kpi["year"] == selected_year].copy()
                prev_dt_filtered = pd.DataFrame()
            else:
                current_dt_filtered = downtime_df_for_kpi[downtime_df_for_kpi["month_label"] == selected_month].copy()
                prev_dt_filtered = downtime_df_for_kpi[downtime_df_for_kpi["month_label"] == prev_month].copy() if prev_month else pd.DataFrame()

        else:
            downtime_df_for_kpi["month_label"] = downtime_df_for_kpi["run_date"].dt.to_period("M").astype(str)
            downtime_df_for_kpi["week_start"] = downtime_df_for_kpi["run_date"] - pd.to_timedelta(downtime_df_for_kpi["run_date"].dt.weekday, unit="D")
            downtime_df_for_kpi["week_label"] = "W/C " + downtime_df_for_kpi["week_start"].dt.strftime("%Y-%m-%d")

            if selected_month == "All":
                current_dt_filtered = downtime_df_for_kpi.copy()
                prev_dt_filtered = pd.DataFrame()
            elif selected_week == "All":
                current_dt_filtered = downtime_df_for_kpi[downtime_df_for_kpi["month_label"] == selected_month].copy()
                prev_dt_filtered = pd.DataFrame()
            else:
                current_dt_filtered = downtime_df_for_kpi[downtime_df_for_kpi["week_label"] == selected_week].copy()
                prev_dt_filtered = downtime_df_for_kpi[downtime_df_for_kpi["week_label"] == prev_week].copy() if prev_week else pd.DataFrame()

        downtime_filtered = current_dt_filtered.copy()
        current_downtime = current_dt_filtered["duration_hours"].sum() if "duration_hours" in current_dt_filtered.columns else None
        prev_downtime = prev_dt_filtered["duration_hours"].sum() if "duration_hours" in prev_dt_filtered.columns and not prev_dt_filtered.empty else None

    # =========================
    # KPI ROW
    # =========================
    current_total_bins = summary_filtered["bins_run"].sum() if "bins_run" in summary_filtered.columns else None
    prev_total_bins = previous_filtered["bins_run"].sum() if "bins_run" in previous_filtered.columns and not previous_filtered.empty else None

    current_bins_per_hour = None
    prev_bins_per_hour = None

    if "total_bins_with_retip" in summary_filtered.columns and "run_hours" in summary_filtered.columns:
        current_total_hours = summary_filtered["run_hours"].sum()
        current_total_bins_for_speed = summary_filtered["total_bins_with_retip"].sum()
        if pd.notna(current_total_hours) and current_total_hours > 0:
            current_bins_per_hour = current_total_bins_for_speed / current_total_hours

    if not previous_filtered.empty and "total_bins_with_retip" in previous_filtered.columns and "run_hours" in previous_filtered.columns:
        prev_total_hours = previous_filtered["run_hours"].sum()
        prev_total_bins_for_speed = previous_filtered["total_bins_with_retip"].sum()
        if pd.notna(prev_total_hours) and prev_total_hours > 0:
            prev_bins_per_hour = prev_total_bins_for_speed / prev_total_hours

    current_retip = summary_filtered["retip"].sum() if "retip" in summary_filtered.columns else None
    prev_retip = previous_filtered["retip"].sum() if "retip" in previous_filtered.columns and not previous_filtered.empty else None

    k1, k2, k3, k4 = st.columns(4)

    with k1:
        st.metric(
            "Total Bins",
            f"{int(current_total_bins):,}" if pd.notna(current_total_bins) else "N/A",
            delta=format_delta(current_total_bins, prev_total_bins, mode="percent"),
            delta_color="normal"
        )

    with k2:
        st.metric(
            "Bins / Hour",
            f"{current_bins_per_hour:.1f}" if pd.notna(current_bins_per_hour) else "N/A",
            delta=format_delta(current_bins_per_hour, prev_bins_per_hour, mode="float"),
            delta_color="normal"
        )

    with k3:
        st.metric(
            "Retip",
            f"{int(current_retip):,}" if pd.notna(current_retip) else "N/A",
            delta=format_delta(current_retip, prev_retip, mode="number"),
            delta_color="inverse"
        )

    with k4:
        st.metric(
            "Downtime",
            f"{current_downtime:.2f} hrs" if pd.notna(current_downtime) else "N/A",
            delta=format_delta(current_downtime, prev_downtime, mode="float"),
            delta_color="inverse"
        )

    # =========================
    # MAIN OVERVIEW ROW
    # =========================
    bins_by_variety = (
        summary_filtered.groupby("variety", as_index=False)["bins_run"]
        .sum()
        .sort_values("bins_run", ascending=False)
    )

    total_bins_period = bins_by_variety["bins_run"].sum() if not bins_by_variety.empty else 0
    bins_by_variety["share_pct"] = (
        (bins_by_variety["bins_run"] / total_bins_period) * 100
        if total_bins_period else 0
    )

    display_bins_by_variety = bins_by_variety.copy()
    display_bins_by_variety = display_bins_by_variety.rename(columns={
        "variety": "Variety",
        "bins_run": "Total Bins",
        "share_pct": "Share %"
    })
    if "Total Bins" in display_bins_by_variety.columns:
        display_bins_by_variety["Total Bins"] = display_bins_by_variety["Total Bins"].map(
            lambda x: f"{int(x):,}" if pd.notna(x) else ""
        )
    if "Share %" in display_bins_by_variety.columns:
        display_bins_by_variety["Share %"] = display_bins_by_variety["Share %"].map(
            lambda x: f"{x:.1f}%"
        )

    main_left, main_right = st.columns([2.2, 1.4])

    with main_left:
        st.subheader("Total Bins Trend")

        if period_choice == "Yearly":
            fig = px.bar(
                chart_df,
                x="year",
                y="bins_run",
                labels={"year": "Year", "bins_run": "Total Bins"},
                title="Total Bins by Year",
                color_discrete_sequence=["#3B82F6"]
            )
            fig.update_xaxes(type="category")

        elif period_choice == "Monthly":
            fig = px.line(
                chart_df,
                x="month_name",
                y="bins_run",
                color="year",
                markers=True,
                category_orders={
                    "month_name": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
                    "year": [str(y) for y in sorted(summary_df["year"].dropna().unique().tolist(), reverse=True)]
                },
                labels={"month_name": "Month", "bins_run": "Total Bins", "year": "Year"},
                title="Monthly Comparison by Year"
            )
            for trace in fig.data:
                if str(trace.name) == str(selected_year):
                    trace.line.width = 4
                else:
                    trace.line.width = 2

            fig.update_layout(
                legend_title_text="Year",
                legend=dict(
                    orientation="v",
                    yanchor="top",
                    y=1,
                    xanchor="left",
                    x=1.02
                )
            )

        else:
            fig = px.bar(
                chart_df,
                x="week_label",
                y="bins_run",
                labels={"week_label": "Week", "bins_run": "Total Bins"},
                title="Weekly Bins",
                color_discrete_sequence=["#3B82F6"]
            )

        fig.update_layout(
            hovermode="x unified",
            height=430,
            margin=dict(l=20, r=20, t=50, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)

    with main_right:
        st.subheader(f"Bins by Variety ({selected_period_label})")
        st.dataframe(
            display_bins_by_variety.head(10),
            use_container_width=True,
            height=430
        )

    # =========================
    # TOP CONTRIBUTORS
    # =========================
    grower_bins = (
        summary_filtered.groupby("grower", as_index=False)["bins_run"]
        .sum()
        .sort_values("bins_run", ascending=False)
    )

    top_variety = str(bins_by_variety.iloc[0]["variety"]) if not bins_by_variety.empty else "N/A"
    top_grower = str(grower_bins.iloc[0]["grower"]) if not grower_bins.empty else "N/A"

    retip_focus_grower = "N/A"
    if "retip" in summary_filtered.columns:
        retip_by_grower = (
            summary_filtered.groupby("grower", as_index=False)["retip"]
            .sum()
            .sort_values("retip", ascending=False)
        )
        if not retip_by_grower.empty:
            retip_focus_grower = str(retip_by_grower.iloc[0]["grower"])

    top_downtime_area = "N/A"
    if not downtime_filtered.empty and "downtime_area" in downtime_filtered.columns:
        area_counts = downtime_filtered["downtime_area"].dropna().astype(str).value_counts()
        if not area_counts.empty:
            top_downtime_area = area_counts.index[0]

    st.subheader("Top Contributors")
    t1, t2, t3, t4 = st.columns(4)

    with t1:
        st.metric("Top Variety", top_variety)

    with t2:
        st.metric("Top Grower", top_grower)

    with t3:
        st.metric("Retip Focus Grower", retip_focus_grower)

    with t4:
        st.metric("Top Downtime Area", top_downtime_area)

    # =========================
    # VARIETY SUMMARY
    # =========================
    st.divider()
    st.subheader("Variety Summary")

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

    bins_by_grower_variety = (
        variety_filtered.groupby("grower", as_index=False)
        .agg(
            total_bins=("bins_run", "sum"),
            period_start=("run_date", "min"),
            period_end=("run_date", "max")
        )
        .sort_values("total_bins", ascending=False)
    )

    if not bins_by_grower_variety.empty:
        bins_by_grower_variety["period"] = (
            bins_by_grower_variety["period_start"].dt.strftime("%Y-%m-%d")
            + " to "
            + bins_by_grower_variety["period_end"].dt.strftime("%Y-%m-%d")
        )
        bins_by_grower_variety = bins_by_grower_variety[["grower", "period", "total_bins"]]

    variety_bins_per_hour = None
    if "total_bins_with_retip" in variety_filtered.columns and "run_hours" in variety_filtered.columns:
        variety_total_hours = variety_filtered["run_hours"].sum()
        variety_total_bins_for_speed = variety_filtered["total_bins_with_retip"].sum()
        if pd.notna(variety_total_hours) and variety_total_hours > 0:
            variety_bins_per_hour = variety_total_bins_for_speed / variety_total_hours

    total_retip_variety = variety_filtered["retip"].sum() if "retip" in variety_filtered.columns else None

    if period_choice == "Yearly":
        variety_chart_base = summary_df.copy()
        variety_chart_df = (
            variety_chart_base[variety_chart_base["variety"].astype(str) == selected_summary_variety]
            .groupby("year", as_index=False)["bins_run"]
            .sum()
            .sort_values("year")
        )
        variety_chart_kind = "bar"

    elif period_choice == "Monthly":
        variety_chart_base = summary_df.copy()
        variety_chart_df = (
            variety_chart_base[variety_chart_base["variety"].astype(str) == selected_summary_variety]
            .groupby(["year", "month_num", "month_name"], as_index=False)["bins_run"]
            .sum()
            .sort_values(["month_num", "year"])
        )
        variety_chart_kind = "multi_line"

    else:
        if selected_month == "All":
            variety_chart_base = summary_df.copy()
        else:
            variety_chart_base = summary_df[summary_df["month_label"] == selected_month].copy()

        variety_chart_df = (
            variety_chart_base[variety_chart_base["variety"].astype(str) == selected_summary_variety]
            .groupby(["week_label", "week_start"], as_index=False)["bins_run"]
            .sum()
            .sort_values("week_start")
        )
        variety_chart_kind = "bar"

    vtop1, vtop2 = st.columns(2)
    with vtop1:
        st.metric("Variety Bins / Hour", f"{variety_bins_per_hour:.1f}" if pd.notna(variety_bins_per_hour) else "N/A")
    with vtop2:
        st.metric("Variety Retip", f"{int(total_retip_variety):,}" if pd.notna(total_retip_variety) else "N/A")

    vleft, vright = st.columns([2.2, 1.4])

    with vleft:
        st.subheader("Variety Bins Trend")

        if variety_chart_kind == "bar":
            x_col = "year" if period_choice == "Yearly" else "week_label"
            fig_v = px.bar(
                variety_chart_df,
                x=x_col,
                y="bins_run",
                labels={x_col: x_col.replace("_", " ").title(), "bins_run": "Total Bins"},
                title="Variety Total Bins",
                color_discrete_sequence=["#F59E0B"]
            )
        else:
            fig_v = px.line(
                variety_chart_df,
                x="month_name",
                y="bins_run",
                color="year",
                markers=True,
                category_orders={
                    "month_name": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
                    "year": [str(y) for y in sorted(summary_df["year"].dropna().unique().tolist(), reverse=True)]
                },
                labels={"month_name": "Month", "bins_run": "Total Bins", "year": "Year"},
                title="Variety Monthly Comparison by Year"
            )

            for trace in fig_v.data:
                if str(trace.name) == str(selected_year):
                    trace.line.width = 4
                else:
                    trace.line.width = 2

            fig_v.update_layout(
                legend_title_text="Year",
                legend=dict(
                    orientation="v",
                    yanchor="top",
                    y=1,
                    xanchor="left",
                    x=1.02
                )
            )

        fig_v.update_layout(
            hovermode="x unified",
            height=430,
            margin=dict(l=20, r=20, t=50, b=20)
        )

        st.plotly_chart(fig_v, use_container_width=True)

    with vright:
        st.subheader("Bins by Grower")

        display_grower_table = bins_by_grower_variety.rename(columns={
            "grower": "Grower",
            "period": "Period",
            "total_bins": "Total Bins"
        })

        if "Total Bins" in display_grower_table.columns:
            display_grower_table["Total Bins"] = display_grower_table["Total Bins"].map(
                lambda x: f"{int(x):,}" if pd.notna(x) else ""
            )

        st.dataframe(
            display_grower_table.head(10),
            use_container_width=True,
            height=430
        )

    # =========================
    # DOWNTIME SUMMARY
    # =========================
    st.divider()
    st.subheader("Downtime Summary")

    dt_left, dt_right = st.columns([1, 2.4])

    with dt_left:
        total_downtime = downtime_filtered["duration_hours"].sum() if "duration_hours" in downtime_filtered.columns else None
        st.metric("Total Downtime", f"{total_downtime:.2f} hrs" if pd.notna(total_downtime) else "N/A")

    with dt_right:
        downtime_table = pd.DataFrame(columns=["Downtime (hrs)", "Area", "Reason"])
        if not downtime_filtered.empty:
            downtime_table = downtime_filtered.copy()

            rename_map = {}
            if "duration_hours" in downtime_table.columns:
                rename_map["duration_hours"] = "Downtime (hrs)"
            if "downtime_area" in downtime_table.columns:
                rename_map["downtime_area"] = "Area"
            if "downtime_reason" in downtime_table.columns:
                rename_map["downtime_reason"] = "Reason"

            downtime_table = downtime_table.rename(columns=rename_map)

            keep_cols = [c for c in ["Downtime (hrs)", "Area", "Reason"] if c in downtime_table.columns]
            downtime_table = downtime_table[keep_cols]

            if "Downtime (hrs)" in downtime_table.columns:
                downtime_table["Downtime (hrs)"] = pd.to_numeric(downtime_table["Downtime (hrs)"], errors="coerce")
                downtime_table = downtime_table.sort_values("Downtime (hrs)", ascending=False)
                downtime_table["Downtime (hrs)"] = downtime_table["Downtime (hrs)"].map(
                    lambda x: f"{x:.2f}" if pd.notna(x) else ""
                )

        st.dataframe(downtime_table, use_container_width=True, height=260)

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
                c for c in ["batch_id", "grower", "variety", "decfile_version", "defect_1", "defect_2", "defect_3"]
                if c in batches.columns
            ]
            mode_df = mode_df.merge(
                batches[batch_link_cols],
                on="batch_id",
                how="left",
                suffixes=("", "_batch")
            )

        # Clean text fields
        for col in ["grower", "variety", "decfile_version", "mode", "check_class", "reason", "action", "sensitivity", "accuracy"]:
            if col in mode_df.columns:
                mode_df[col] = (
                    mode_df[col]
                    .fillna("")
                    .astype(str)
                    .str.strip()
                    .replace("", pd.NA)
                )

        # Keep only boundary columns numeric
        if "boundary_before" in mode_df.columns:
            mode_df["boundary_before"] = pd.to_numeric(mode_df["boundary_before"], errors="coerce")
        if "boundary_after" in mode_df.columns:
            mode_df["boundary_after"] = pd.to_numeric(mode_df["boundary_after"], errors="coerce")

        # Clean batches copy for top defects
        if batches is not None:
            batches_mode = batches.copy()
            for col in ["grower", "variety", "decfile_version", "defect_1", "defect_2", "defect_3"]:
                if col in batches_mode.columns:
                    batches_mode[col] = (
                        batches_mode[col]
                        .fillna("")
                        .astype(str)
                        .str.strip()
                        .replace("", pd.NA)
                    )
        else:
            batches_mode = None

        # -----------------------------
        # TOP ROW: Filters left / Top Defects right
        # -----------------------------
        top_left, top_right = st.columns([1.2, 1])

        with top_left:
            st.subheader("Filters")

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

        with top_right:
            st.subheader("Top Defects")

            top_defects_mode = pd.DataFrame(columns=["Defect", "Count"])

            if batches_mode is not None:
                filtered_batches_mode = batches_mode.copy()

                if selected_mode_variety != "All" and "variety" in filtered_batches_mode.columns:
                    filtered_batches_mode = filtered_batches_mode[
                        filtered_batches_mode["variety"].astype(str) == selected_mode_variety
                    ]

                if selected_mode_grower != "All" and "grower" in filtered_batches_mode.columns:
                    filtered_batches_mode = filtered_batches_mode[
                        filtered_batches_mode["grower"].astype(str) == selected_mode_grower
                    ]

                if selected_version != "All" and "decfile_version" in filtered_batches_mode.columns:
                    filtered_batches_mode = filtered_batches_mode[
                        filtered_batches_mode["decfile_version"].astype(str) == selected_version
                    ]

                defect_cols = [c for c in ["defect_1", "defect_2", "defect_3"] if c in filtered_batches_mode.columns]
                if defect_cols:
                    mode_defects = (
                        filtered_batches_mode[defect_cols]
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
                st.dataframe(top_defects_mode, use_container_width=True, height=260)
            else:
                st.info("No defect data available for the current filters.")

        # -----------------------------
        # Top Adjusted Modes
        # -----------------------------
        st.subheader("Top Adjusted Modes")

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
                height=320,
                hide_index=True,
                column_config={
                    "Check": st.column_config.CheckboxColumn("Check")
                },
                disabled=["Mode", "Check Class", "Count", "Reference Boundaries", "Sensitivity", "Accuracy"]
            )
        else:
            st.info("No adjusted mode data available for the current filters.")

        # -----------------------------
        # Step 1 - Select the defect to investigate
        # -----------------------------
        st.subheader("Step 1 — Select the defect to investigate")

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
                )

                st.dataframe(related_modes, use_container_width=True, height=260)
            else:
                st.info("No related modes found for this defect / reason.")
        else:
            st.write("Choose a defect / reason above to see related modes.")

        # -----------------------------
        # Step 2 - Review what this mode can also detect
        # -----------------------------
        st.subheader("Step 2 — Review what this mode can also detect")

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
                st.write("Other detectable defects / reasons for this mode")

                card_cols = st.columns(3)
                for idx, row in other_reason_counts.iterrows():
                    col = card_cols[idx % 3]
                    with col:
                        st.markdown(
                            f"""
                            <div style="
                                border:1px solid #e5e7eb;
                                border-radius:12px;
                                padding:14px;
                                margin-bottom:12px;
                                background-color:#fafafa;
                            ">
                                <div style="font-size:16px; font-weight:600; margin-bottom:6px;">
                                    {row['Recorded Reason']}
                                </div>
                                <div style="font-size:14px; color:#555;">
                                    Count: {int(row['Count'])}
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
            else:
                st.info("No other recorded reasons found for this mode.")
        else:
            st.write("Select one mode above to see what else it is able to see.")

        # -----------------------------
        # Step 3 - Review unchecked modes for this grower
        # -----------------------------
        st.subheader("Step 3 — Review unchecked modes for this grower")

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
            # full database for this variety, not limited by grower
            variety_mode_db = mode_df.copy()

            if "variety" in variety_mode_db.columns:
                variety_mode_db = variety_mode_db[
                    variety_mode_db["variety"].astype(str) == selected_mode_variety
                ]

            if selected_version != "All" and "decfile_version" in variety_mode_db.columns:
                variety_mode_db = variety_mode_db[
                    variety_mode_db["decfile_version"].astype(str) == selected_version
                ]

            # modes already present for this grower under same variety
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
            st.write("Choose a specific variety and grower to see which modes are not yet checked for this grower.")
        elif not next_modes_table.empty:
            st.data_editor(
                next_modes_table,
                use_container_width=True,
                height=280,
                hide_index=True,
                column_config={
                    "Check": st.column_config.CheckboxColumn("Check")
                },
                disabled=["Mode", "Check Class", "Count", "Reference Boundaries", "Sensitivity", "Accuracy"]
            )
        else:
            st.write("No additional unchecked modes found for this grower under the selected variety.")

