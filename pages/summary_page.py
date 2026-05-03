import streamlit as st
import pandas as pd
import plotly.express as px

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
    </style>
    """, unsafe_allow_html=True)


AMBER = "#f5a623"
EMERALD = "#34d399"
ROSE = "#fb7185"
BLUE = "#60a5fa"
PURPLE = "#a78bfa"
COLOR_SEQ = [AMBER, BLUE, EMERALD, PURPLE, ROSE, "#f9a8d4", "#fcd34d", "#6ee7b7"]

PLOT_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#181c27",
    font=dict(family="DM Mono, monospace", color="#94a3b8", size=11),
    title_font=dict(family="Sora, sans-serif", color="#e8eaf2", size=13),
    xaxis=dict(gridcolor="#252a3a", linecolor="#252a3a", tickfont=dict(size=10)),
    yaxis=dict(gridcolor="#252a3a", linecolor="#252a3a", tickfont=dict(size=10)),
    margin=dict(l=20, r=20, t=44, b=20),
    hovermode="x unified",
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
)


def apply_plot_theme(fig, height=380):
    fig.update_layout(**PLOT_LAYOUT, height=height)
    return fig


def section_title(title: str):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)


def format_delta(current, previous, mode="number"):
    if pd.isna(current) or pd.isna(previous):
        return "N/A"

    if mode == "percent":
        if previous == 0:
            return "N/A"
        return f"{((current - previous) / previous) * 100:+.1f}% vs prev"

    if mode == "float":
        return f"{current - previous:+.1f} vs prev"

    return f"{int(current - previous):+,.0f} vs prev"


def kpi_html(label, value, delta="", direction="neu"):
    delta_html = f'<div class="kpi-delta {direction}">{delta}</div>' if delta else ""
    return f"""
    <div class="kpi-card">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{value}</div>
      {delta_html}
    </div>
    """


# ============================================================
# PREP
# ============================================================
runs = ensure_datetime(runs, "run_date")
downtime = ensure_datetime(downtime, "run_date")

apply_dashboard_style()

latest_date = pd.NaT
if runs is not None and "run_date" in runs.columns:
    latest_date = runs["run_date"].max()

date_str = latest_date.strftime("%d %b %Y") if pd.notna(latest_date) else "N/A"

st.markdown(
    f"""
    <div class="page-header">
      <h1>🍎 Presizing Operations</h1>
      <span>Updated {date_str} · {len(runs):,} runs recorded</span>
    </div>
    """,
    unsafe_allow_html=True,
)

summary_df = runs.copy()
summary_df = summary_df.dropna(subset=["run_date"]).copy()

# ============================================================
# SIDEBAR FILTERS
# ============================================================
with st.sidebar:
    st.header("Summary Filters")

    period_choice = st.radio(
        "Period Type",
        ["Yearly", "Monthly", "Weekly"]
    )

    selected_year = None
    selected_month = None
    selected_week = None
    prev_year = None
    prev_month = None
    prev_week = None

    if period_choice == "Yearly":
        summary_df["year"] = summary_df["run_date"].dt.year.astype(int)
        available_years = sorted(summary_df["year"].dropna().unique().tolist(), reverse=True)
        selected_year = st.selectbox("Select Year", available_years)

    elif period_choice == "Monthly":
        summary_df["year"] = summary_df["run_date"].dt.year.astype(int)
        summary_df["month_num"] = summary_df["run_date"].dt.month
        summary_df["month_name"] = summary_df["run_date"].dt.strftime("%b")
        summary_df["month_label"] = summary_df["run_date"].dt.to_period("M").astype(str)

        available_years = sorted(summary_df["year"].dropna().unique().tolist(), reverse=True)
        selected_year = st.selectbox("Select Year", available_years)

        year_df_sidebar = summary_df[summary_df["year"] == selected_year].copy()
        available_months = (
            year_df_sidebar["month_label"]
            .dropna()
            .drop_duplicates()
            .sort_values()
            .tolist()
        )
        selected_month = st.selectbox("Select Month", ["All"] + available_months)

    else:
        summary_df["month_label"] = summary_df["run_date"].dt.to_period("M").astype(str)
        summary_df["week_start"] = summary_df["run_date"] - pd.to_timedelta(
            summary_df["run_date"].dt.weekday, unit="D"
        )
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
            month_df_sidebar = summary_df.copy()
        else:
            month_df_sidebar = summary_df[summary_df["month_label"] == selected_month].copy()

        available_weeks = (
            month_df_sidebar[["week_label", "week_start"]]
            .drop_duplicates()
            .sort_values("week_start")["week_label"]
            .tolist()
        )
        selected_week = st.selectbox("Select Week", ["All"] + available_weeks)

# ============================================================
# MAIN FILTERED DATA
# ============================================================
if period_choice == "Yearly":
    chart_df = (
        summary_df.groupby("year", as_index=False)["bins_run"]
        .sum()
        .sort_values("year")
    )
    summary_filtered = summary_df[summary_df["year"] == selected_year].copy()
    selected_period_label = str(selected_year)

    prev_year = selected_year - 1
    previous_filtered = summary_df[summary_df["year"] == prev_year].copy()

elif period_choice == "Monthly":
    year_df = summary_df[summary_df["year"] == selected_year].copy()

    chart_df = (
        summary_df.groupby(["year", "month_num", "month_name"], as_index=False)["bins_run"]
        .sum()
        .sort_values(["month_num", "year"], ascending=[True, False])
    )

    if selected_month == "All":
        summary_filtered = year_df.copy()
        selected_period_label = f"{selected_year} (All)"
        previous_filtered = pd.DataFrame()
        prev_month = None
    else:
        summary_filtered = year_df[year_df["month_label"] == selected_month].copy()
        selected_period_label = selected_month

        available_months = (
            year_df["month_label"]
            .dropna()
            .drop_duplicates()
            .sort_values()
            .tolist()
        )
        current_idx = available_months.index(selected_month)
        prev_month = available_months[current_idx - 1] if current_idx > 0 else None
        previous_filtered = year_df[year_df["month_label"] == prev_month].copy() if prev_month else pd.DataFrame()

else:
    if selected_month == "All":
        month_df = summary_df.copy()
    else:
        month_df = summary_df[summary_df["month_label"] == selected_month].copy()

    chart_df = (
        month_df.groupby(["week_label", "week_start"], as_index=False)["bins_run"]
        .sum()
        .sort_values("week_start")
    )

    if selected_week == "All":
        summary_filtered = month_df.copy()
        selected_period_label = "All" if selected_month == "All" else f"{selected_month} (All)"
        previous_filtered = pd.DataFrame()
        prev_week = None
    else:
        summary_filtered = month_df[month_df["week_label"] == selected_week].copy()
        selected_period_label = selected_week

        available_weeks = (
            month_df[["week_label", "week_start"]]
            .drop_duplicates()
            .sort_values("week_start")["week_label"]
            .tolist()
        )
        current_idx = available_weeks.index(selected_week)
        prev_week = available_weeks[current_idx - 1] if current_idx > 0 else None
        previous_filtered = month_df[month_df["week_label"] == prev_week].copy() if prev_week else pd.DataFrame()

# ============================================================
# DOWNTIME FILTERED
# ============================================================
current_downtime = None
prev_downtime = None
downtime_filtered = pd.DataFrame()

if downtime is not None and "run_date" in downtime.columns:
    downtime_df_for_kpi = downtime.copy().dropna(subset=["run_date"]).copy()

    if "duration_hours" not in downtime_df_for_kpi.columns and "duration_minutes" in downtime_df_for_kpi.columns:
        downtime_df_for_kpi["duration_hours"] = pd.to_numeric(
            downtime_df_for_kpi["duration_minutes"], errors="coerce"
        ) / 60

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
            current_dt_filtered = downtime_df_for_kpi[
                downtime_df_for_kpi["month_label"] == selected_month
            ].copy()
            prev_dt_filtered = downtime_df_for_kpi[
                downtime_df_for_kpi["month_label"] == prev_month
            ].copy() if prev_month else pd.DataFrame()

    else:
        downtime_df_for_kpi["week_label"] = "W/C " + (
            downtime_df_for_kpi["run_date"] - pd.to_timedelta(downtime_df_for_kpi["run_date"].dt.weekday, unit="D")
        ).dt.strftime("%Y-%m-%d")

        if selected_week == "All":
            current_dt_filtered = downtime_df_for_kpi.copy()
            prev_dt_filtered = pd.DataFrame()
        else:
            current_dt_filtered = downtime_df_for_kpi[
                downtime_df_for_kpi["week_label"] == selected_week
            ].copy()
            prev_dt_filtered = downtime_df_for_kpi[
                downtime_df_for_kpi["week_label"] == prev_week
            ].copy() if prev_week else pd.DataFrame()

    downtime_filtered = current_dt_filtered.copy()
    current_downtime = (
        current_dt_filtered["duration_hours"].sum()
        if "duration_hours" in current_dt_filtered.columns else None
    )
    prev_downtime = (
        prev_dt_filtered["duration_hours"].sum()
        if "duration_hours" in prev_dt_filtered.columns and not prev_dt_filtered.empty else None
    )

# ============================================================
# KPI VALUES
# ============================================================
current_total_bins = (
    summary_filtered["bins_run"].sum()
    if "bins_run" in summary_filtered.columns else None
)
prev_total_bins = (
    previous_filtered["bins_run"].sum()
    if "bins_run" in previous_filtered.columns and not previous_filtered.empty else None
)

current_bins_per_hour = None
prev_bins_per_hour = None

if "total_bins_with_retip" in summary_filtered.columns and "run_hours" in summary_filtered.columns:
    current_total_hours = summary_filtered["run_hours"].sum()
    current_total_bins_for_speed = summary_filtered["total_bins_with_retip"].sum()
    if pd.notna(current_total_hours) and current_total_hours > 0:
        current_bins_per_hour = current_total_bins_for_speed / current_total_hours

if (
    not previous_filtered.empty
    and "total_bins_with_retip" in previous_filtered.columns
    and "run_hours" in previous_filtered.columns
):
    prev_total_hours = previous_filtered["run_hours"].sum()
    prev_total_bins_for_speed = previous_filtered["total_bins_with_retip"].sum()
    if pd.notna(prev_total_hours) and prev_total_hours > 0:
        prev_bins_per_hour = prev_total_bins_for_speed / prev_total_hours

current_retip = (
    summary_filtered["retip"].sum()
    if "retip" in summary_filtered.columns else None
)
prev_retip = (
    previous_filtered["retip"].sum()
    if "retip" in previous_filtered.columns and not previous_filtered.empty else None
)

retip_rate = None
if pd.notna(current_retip) and pd.notna(current_total_bins) and (current_total_bins + current_retip) > 0:
    retip_rate = (current_retip / (current_total_bins + current_retip)) * 100

total_hours = summary_filtered["run_hours"].sum() if "run_hours" in summary_filtered.columns else None
downtime_pct = None
if pd.notna(current_downtime) and pd.notna(total_hours) and (total_hours + current_downtime) > 0:
    downtime_pct = (current_downtime / (total_hours + current_downtime)) * 100

# ============================================================
# KPI ROW
# ============================================================
k1, k2, k3, k4, k5 = st.columns(5)

with k1:
    st.markdown(
        kpi_html(
            "Total Bins Run",
            f"{current_total_bins:,.0f}" if pd.notna(current_total_bins) else "N/A",
            format_delta(current_total_bins, prev_total_bins, "percent"),
            "up" if pd.notna(current_total_bins) and pd.notna(prev_total_bins) and current_total_bins >= prev_total_bins else "down",
        ),
        unsafe_allow_html=True,
    )

with k2:
    st.markdown(
        kpi_html(
            "Bins / Hour",
            f"{current_bins_per_hour:.1f}" if pd.notna(current_bins_per_hour) else "N/A",
            format_delta(current_bins_per_hour, prev_bins_per_hour, "float"),
            "up" if pd.notna(current_bins_per_hour) and pd.notna(prev_bins_per_hour) and current_bins_per_hour >= prev_bins_per_hour else "down",
        ),
        unsafe_allow_html=True,
    )

with k3:
    st.markdown(
        kpi_html(
            "Total Retip",
            f"{int(current_retip):,}" if pd.notna(current_retip) else "N/A",
            format_delta(current_retip, prev_retip),
            "down" if pd.notna(current_retip) and pd.notna(prev_retip) and current_retip > prev_retip else "up",
        ),
        unsafe_allow_html=True,
    )

with k4:
    st.markdown(
        kpi_html(
            "Downtime",
            f"{current_downtime:.2f} hrs" if pd.notna(current_downtime) else "N/A",
            format_delta(current_downtime, prev_downtime, "float"),
            "down" if pd.notna(current_downtime) and pd.notna(prev_downtime) and current_downtime > prev_downtime else "up",
        ),
        unsafe_allow_html=True,
    )

with k5:
    st.markdown(
        kpi_html(
            "Retip Rate",
            f"{retip_rate:.1f}%" if pd.notna(retip_rate) else "N/A",
            "bins sent back for re-grading",
            "neu",
        ),
        unsafe_allow_html=True,
    )

st.markdown("---")

# ============================================================
# MAIN CHARTS
# ============================================================
bins_by_variety = (
    summary_filtered.groupby("variety", as_index=False)["bins_run"]
    .sum()
    .sort_values("bins_run", ascending=False)
)

main_left, main_right = st.columns([2.2, 1.4])

with main_left:
    section_title("Throughput Trend")

    if period_choice == "Yearly":
        fig = px.bar(chart_df, x="year", y="bins_run", color_discrete_sequence=[AMBER])
        fig.update_xaxes(type="category")
    elif period_choice == "Monthly":
        fig = px.line(
            chart_df,
            x="month_name",
            y="bins_run",
            color="year",
            markers=True,
            color_discrete_sequence=COLOR_SEQ,
            category_orders={"month_name": ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]},
        )
    else:
        fig = px.bar(chart_df, x="week_label", y="bins_run", color_discrete_sequence=[AMBER])

    fig.update_traces(hovertemplate="%{y:,.0f} bins")
    apply_plot_theme(fig, height=380)
    st.plotly_chart(fig, use_container_width=True)

with main_right:
    section_title(f"Variety Split — {selected_period_label}")

    if not bins_by_variety.empty:
        fig_pie = px.pie(
            bins_by_variety,
            names="variety",
            values="bins_run",
            hole=0.55,
            color_discrete_sequence=COLOR_SEQ,
        )
        fig_pie.update_traces(
            textposition="outside",
            textfont_size=10,
            hovertemplate="%{label}<br>%{value:,.0f} bins (%{percent})"
        )
        apply_plot_theme(fig_pie, height=340)
        fig_pie.update_layout(showlegend=True, legend=dict(orientation="v", x=1, y=0.5))
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No variety data for this selection.")

# ============================================================
# TOP CONTRIBUTORS
# ============================================================
st.markdown("---")
section_title("Top Contributors")

grower_bins = (
    summary_filtered.groupby("grower", as_index=False)["bins_run"]
    .sum()
    .sort_values("bins_run", ascending=False)
)

top_variety = bins_by_variety.iloc[0]["variety"] if not bins_by_variety.empty else "N/A"
top_grower = grower_bins.iloc[0]["grower"] if not grower_bins.empty else "N/A"

retip_focus_grower = "N/A"
if "retip" in summary_filtered.columns:
    retip_by_grower = (
        summary_filtered.groupby("grower", as_index=False)["retip"]
        .sum()
        .sort_values("retip", ascending=False)
    )
    if not retip_by_grower.empty:
        retip_focus_grower = retip_by_grower.iloc[0]["grower"]

top_downtime_area = "N/A"
if not downtime_filtered.empty and "downtime_area" in downtime_filtered.columns:
    area_counts = downtime_filtered["downtime_area"].dropna().astype(str).value_counts()
    if not area_counts.empty:
        top_downtime_area = area_counts.index[0]

t1, t2, t3, t4 = st.columns(4)

with t1:
    st.markdown(kpi_html("Top Variety", str(top_variety)), unsafe_allow_html=True)
with t2:
    st.markdown(kpi_html("Top Grower", str(top_grower)), unsafe_allow_html=True)
with t3:
    st.markdown(kpi_html("Most Retipped Grower", str(retip_focus_grower)), unsafe_allow_html=True)
with t4:
    st.markdown(kpi_html("Top Downtime Area", str(top_downtime_area)), unsafe_allow_html=True)

# ============================================================
# THROUGHPUT EFFICIENCY BY GROWER
# ============================================================
if "bins_per_hour_row" in summary_filtered.columns:
    st.markdown("---")
    section_title("Throughput Efficiency by Grower")

    bph_grower = (
        summary_filtered.groupby("grower", as_index=False)
        .apply(lambda g: pd.Series({
            "bins_per_hour": g["total_bins_with_retip"].sum() / g["run_hours"].sum()
            if g["run_hours"].sum() > 0 else None,
            "total_bins": g["bins_run"].sum()
        }))
        .dropna(subset=["bins_per_hour"])
        .sort_values("bins_per_hour", ascending=True)
    )

    if not bph_grower.empty:
        overall_bph = current_bins_per_hour
        fig_bph = px.bar(
            bph_grower,
            x="bins_per_hour",
            y="grower",
            orientation="h",
            color="bins_per_hour",
            color_continuous_scale=["#1e2435", AMBER],
            labels={"bins_per_hour": "Bins/hr", "grower": "Grower"},
        )
        if pd.notna(overall_bph):
            fig_bph.add_vline(
                x=overall_bph,
                line_dash="dot",
                line_color=ROSE,
                annotation_text=f"Avg {overall_bph:.1f}",
                annotation_font_color=ROSE,
            )
        fig_bph.update_coloraxes(showscale=False)
        fig_bph.update_traces(hovertemplate="%{x:.1f} bins/hr")
        apply_plot_theme(fig_bph, height=max(280, len(bph_grower) * 32))
        st.plotly_chart(fig_bph, use_container_width=True)

# ============================================================
# VARIETY DEEP-DIVE
# ============================================================
st.markdown("---")
section_title("Variety Deep-Dive")

available_varieties = sorted(summary_filtered["variety"].dropna().astype(str).unique().tolist())
selected_summary_variety = st.selectbox(
    "Select Variety",
    available_varieties if available_varieties else ["N/A"],
    key="summary_variety"
)

variety_filtered = summary_filtered[
    summary_filtered["variety"].astype(str) == selected_summary_variety
].copy()

variety_bins_per_hour = None
if "total_bins_with_retip" in variety_filtered.columns and "run_hours" in variety_filtered.columns:
    v_hours = variety_filtered["run_hours"].sum()
    v_bins = variety_filtered["total_bins_with_retip"].sum()
    if pd.notna(v_hours) and v_hours > 0:
        variety_bins_per_hour = v_bins / v_hours

total_retip_variety = variety_filtered["retip"].sum() if "retip" in variety_filtered.columns else None
total_bins_variety = variety_filtered["bins_run"].sum() if "bins_run" in variety_filtered.columns else None
run_days_variety = variety_filtered["run_date"].nunique() if "run_date" in variety_filtered.columns else None

vk1, vk2, vk3, vk4 = st.columns(4)
with vk1:
    st.markdown(kpi_html("Bins Run", f"{int(total_bins_variety):,}" if pd.notna(total_bins_variety) else "N/A"), unsafe_allow_html=True)
with vk2:
    st.markdown(kpi_html("Bins / Hour", f"{variety_bins_per_hour:.1f}" if pd.notna(variety_bins_per_hour) else "N/A"), unsafe_allow_html=True)
with vk3:
    st.markdown(kpi_html("Retip", f"{int(total_retip_variety):,}" if pd.notna(total_retip_variety) else "N/A"), unsafe_allow_html=True)
with vk4:
    st.markdown(kpi_html("Active Run Days", str(run_days_variety) if pd.notna(run_days_variety) else "N/A"), unsafe_allow_html=True)

bins_by_grower_variety = (
    variety_filtered.groupby("grower", as_index=False)
    .agg(
        total_bins=("bins_run", "sum"),
        period_start=("run_date", "min"),
        period_end=("run_date", "max"),
    )
    .sort_values("total_bins", ascending=True)
)

vl, vr = st.columns([1.6, 1.4])

with vl:
    if not bins_by_grower_variety.empty:
        fig_vg = px.bar(
            bins_by_grower_variety,
            x="total_bins",
            y="grower",
            orientation="h",
            color_discrete_sequence=[BLUE],
            labels={"total_bins": "Total Bins", "grower": "Grower"},
        )
        fig_vg.update_traces(hovertemplate="%{x:,.0f} bins")
        apply_plot_theme(fig_vg, height=max(240, len(bins_by_grower_variety) * 36))
        st.plotly_chart(fig_vg, use_container_width=True)

with vr:
    if not bins_by_grower_variety.empty:
        disp = bins_by_grower_variety.rename(columns={"grower": "Grower", "total_bins": "Bins"})[
            ["Grower", "Bins"]
        ].sort_values("Bins", ascending=False)
        disp["Bins"] = disp["Bins"].map(lambda x: f"{int(x):,}")
        st.dataframe(disp, use_container_width=True, height=280)

# ============================================================
# DOWNTIME ANALYSIS
# ============================================================
st.markdown("---")
section_title("Downtime Analysis")

dl, dm, dr = st.columns([1, 1.5, 1.5])

with dl:
    total_dt = downtime_filtered["duration_hours"].sum() if "duration_hours" in downtime_filtered.columns else None
    st.markdown(
        kpi_html("Total Downtime (hrs)", f"{total_dt:.2f}" if pd.notna(total_dt) else "N/A"),
        unsafe_allow_html=True,
    )

    if pd.notna(downtime_pct):
        st.markdown(
            kpi_html("Downtime %", f"{downtime_pct:.1f}%", "of total scheduled hours", "neu"),
            unsafe_allow_html=True,
        )

with dm:
    if not downtime_filtered.empty and "downtime_area" in downtime_filtered.columns:
        area_hrs = (
            downtime_filtered.groupby("downtime_area", as_index=False)["duration_hours"]
            .sum()
            .sort_values("duration_hours", ascending=False)
        )
        if not area_hrs.empty:
            fig_dt = px.bar(
                area_hrs,
                x="downtime_area",
                y="duration_hours",
                color_discrete_sequence=[ROSE],
                labels={"downtime_area": "Area", "duration_hours": "Hours"},
            )
            fig_dt.update_traces(hovertemplate="%{y:.2f} hrs")
            apply_plot_theme(fig_dt, height=260)
            st.plotly_chart(fig_dt, use_container_width=True)

with dr:
    if not downtime_filtered.empty:
        dt_tbl = downtime_filtered.copy()
        cols_show = [c for c in ["duration_hours", "downtime_area", "downtime_reason"] if c in dt_tbl.columns]
        dt_tbl = dt_tbl[cols_show].rename(columns={
            "duration_hours": "Hours",
            "downtime_area": "Area",
            "downtime_reason": "Reason",
        }).sort_values("Hours", ascending=False)
        dt_tbl["Hours"] = dt_tbl["Hours"].map(lambda x: f"{x:.2f}")
        st.dataframe(dt_tbl, use_container_width=True, height=280)
    else:
        st.info("No downtime recorded for this period.")
