import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

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

      .insight-good {
        background: rgba(52, 211, 153, 0.08);
        border: 1px solid rgba(52, 211, 153, 0.35);
        border-radius: 8px;
        padding: 12px 14px;
        margin-bottom: 10px;
        color: #a7f3d0;
      }

      .insight-bad {
        background: rgba(251, 113, 133, 0.08);
        border: 1px solid rgba(251, 113, 133, 0.35);
        border-radius: 8px;
        padding: 12px 14px;
        margin-bottom: 10px;
        color: #fecdd3;
      }

      .insight-neutral {
        background: rgba(245, 166, 35, 0.08);
        border: 1px solid rgba(245, 166, 35, 0.35);
        border-radius: 8px;
        padding: 12px 14px;
        margin-bottom: 10px;
        color: #fde68a;
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


def apply_plot_theme(fig, height=360):
    fig.update_layout(**PLOT_LAYOUT, height=height)
    return fig


# ============================================================
# PREP
# ============================================================
runs = ensure_datetime(runs, "run_date")
apply_dashboard_style()

st.markdown(
    """
    <div class="page-header">
      <h1>🍏 Quality Analysis</h1>
      <span>Grade distribution · loss profile · defect and mode activity</span>
    </div>
    """,
    unsafe_allow_html=True,
)

quality_df = runs.copy()
quality_df = quality_df.dropna(subset=["run_date"]).copy()

# ============================================================
# FILTERS
# ============================================================
with st.sidebar:
    st.header("Quality Filters")

    quality_df["month_label"] = quality_df["run_date"].dt.to_period("M").astype(str)

    selected_quality_month = st.selectbox(
        "Month",
        ["All"] + sorted(quality_df["month_label"].dropna().astype(str).unique().tolist(), reverse=True),
        key="quality_month"
    )

    selected_variety = st.selectbox(
        "Variety",
        ["All"] + sorted(quality_df["variety"].dropna().astype(str).unique().tolist()) if "variety" in quality_df.columns else ["All"],
        key="quality_variety"
    )

    selected_grower = st.selectbox(
        "Grower",
        ["All"] + sorted(quality_df["grower"].dropna().astype(str).unique().tolist()) if "grower" in quality_df.columns else ["All"],
        key="quality_grower"
    )

filtered_df = quality_df.copy()

if selected_quality_month != "All":
    filtered_df = filtered_df[filtered_df["month_label"].astype(str) == selected_quality_month].copy()

if selected_variety != "All" and "variety" in filtered_df.columns:
    filtered_df = filtered_df[filtered_df["variety"].astype(str) == selected_variety].copy()

if selected_grower != "All" and "grower" in filtered_df.columns:
    filtered_df = filtered_df[filtered_df["grower"].astype(str) == selected_grower].copy()

# ============================================================
# RATE COLUMNS
# ============================================================
rate_cols = [
    c for c in [
        "premium_rate",
        "c1_color_rate",
        "c1_quality_rate",
        "c2_color_rate",
        "c2_quality_rate",
        "no_color_rate",
        "juice_rate",
    ] if c in filtered_df.columns
]

label_map = {
    "premium_rate": "Premium",
    "c1_color_rate": "C1 Color",
    "c1_quality_rate": "C1 Quality",
    "c2_color_rate": "C2 Color",
    "c2_quality_rate": "C2 Quality",
    "no_color_rate": "No Color",
    "juice_rate": "Juice",
}

for col in rate_cols:
    filtered_df[col] = pd.to_numeric(filtered_df[col], errors="coerce")

avg_rates = filtered_df[rate_cols].mean() if rate_cols else pd.Series(dtype="float64")

# ============================================================
# KPI ROW
# ============================================================
run_count = len(filtered_df)
grower_count = filtered_df["grower"].dropna().nunique() if "grower" in filtered_df.columns else None
variety_count = filtered_df["variety"].dropna().nunique() if "variety" in filtered_df.columns else None
batch_count = filtered_df["batch_id"].dropna().nunique() if "batch_id" in filtered_df.columns else None

k1, k2, k3, k4 = st.columns(4)

with k1:
    st.markdown(kpi_html("Runs", f"{run_count:,}"), unsafe_allow_html=True)
with k2:
    st.markdown(kpi_html("Growers", f"{grower_count:,}" if pd.notna(grower_count) else "N/A"), unsafe_allow_html=True)
with k3:
    st.markdown(kpi_html("Varieties", f"{variety_count:,}" if pd.notna(variety_count) else "N/A"), unsafe_allow_html=True)
with k4:
    st.markdown(kpi_html("Batches", f"{batch_count:,}" if pd.notna(batch_count) else "N/A"), unsafe_allow_html=True)

st.markdown("---")

# ============================================================
# AVERAGE QUALITY RATES
# ============================================================
if rate_cols:
    section_title("Average Quality Rates (%)")
    rate_cols_ui = st.columns(len(rate_cols))

    for i, col in enumerate(rate_cols):
        val = avg_rates[col]
        direction = "neu"
        if col == "premium_rate":
            direction = "up"
        elif col in ["juice_rate", "no_color_rate"]:
            direction = "down"

        rate_cols_ui[i].markdown(
            kpi_html(label_map.get(col, col), f"{val:.1f}%" if pd.notna(val) else "N/A", "", direction),
            unsafe_allow_html=True
        )

st.markdown("---")

# ============================================================
# TREND + PREVIEW
# ============================================================
cl1, cl2 = st.columns([1.5, 1.0])

with cl1:
    section_title("Grade Distribution Over Time")

    if rate_cols and not filtered_df.empty:
        trend_df = filtered_df.copy()
        trend_df["period"] = trend_df["run_date"].dt.to_period("M").astype(str)
        trend_grp = trend_df.groupby("period")[rate_cols].mean(numeric_only=True).reset_index()

        fig_trend = go.Figure()
        for col, color in zip(rate_cols, COLOR_SEQ):
            fig_trend.add_trace(
                go.Scatter(
                    x=trend_grp["period"],
                    y=trend_grp[col],
                    name=label_map.get(col, col),
                    mode="lines+markers",
                    line=dict(color=color, width=2),
                    hovertemplate=f"{label_map.get(col, col)}: %{{y:.1f}}%"
                )
            )

        apply_plot_theme(fig_trend, height=360)
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("No quality rate data available.")

with cl2:
    section_title("Run Details")

    preview_cols = [
        c for c in [
            "run_date", "run_id", "grower", "variety", "bins_run",
            "premium_rate", "juice_rate", "test_drop_count"
        ] if c in filtered_df.columns
    ]
    st.dataframe(filtered_df[preview_cols].head(20), use_container_width=True, height=380)

st.markdown("---")

# ============================================================
# LOSS ANALYSIS
# ============================================================
section_title("Loss Analysis")

il1, il2 = st.columns([1.15, 1.65])

with il1:
    premium_v = avg_rates.get("premium_rate", None)
    juice_v = avg_rates.get("juice_rate", None)
    no_color_v = avg_rates.get("no_color_rate", None)
    c1c = avg_rates.get("c1_color_rate", None)
    c1q = avg_rates.get("c1_quality_rate", None)

    total_loss = None
    if pd.notna(juice_v) or pd.notna(no_color_v):
        total_loss = (0 if pd.isna(juice_v) else juice_v) + (0 if pd.isna(no_color_v) else no_color_v)

    if pd.notna(premium_v):
        st.markdown(
            f'<div class="insight-good">✔ Premium average: <b>{premium_v:.1f}%</b></div>',
            unsafe_allow_html=True
        )

    if pd.notna(total_loss):
        st.markdown(
            f'<div class="insight-bad">⚠ Juice + No-Color loss: <b>{total_loss:.1f}%</b></div>',
            unsafe_allow_html=True
        )

    if pd.notna(c1c) and pd.notna(c1q):
        if c1c > c1q:
            st.markdown(
                f'<div class="insight-bad">⚠ Color loss ({c1c:.1f}%) exceeds quality loss ({c1q:.1f}%)</div>',
                unsafe_allow_html=True
            )
        elif c1q > c1c:
            st.markdown(
                f'<div class="insight-bad">⚠ Quality loss ({c1q:.1f}%) exceeds color loss ({c1c:.1f}%)</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f'<div class="insight-neutral">Color and quality loss are balanced ({c1c:.1f}%)</div>',
                unsafe_allow_html=True
            )

    if "test_drop_count" in filtered_df.columns:
        avg_td = pd.to_numeric(filtered_df["test_drop_count"], errors="coerce").mean()
        if pd.notna(avg_td):
            st.markdown(
                kpi_html("Avg Test Drops / Run", f"{avg_td:.1f}"),
                unsafe_allow_html=True
            )

with il2:
    if rate_cols:
        radar_vals = [avg_rates[c] for c in rate_cols if pd.notna(avg_rates[c])]
        radar_labels = [label_map.get(c, c) for c in rate_cols if pd.notna(avg_rates[c])]
        radar_source_cols = [c for c in rate_cols if pd.notna(avg_rates[c])]

        if radar_vals:
            bar_colors = []
            for c in radar_source_cols:
                if c == "premium_rate":
                    bar_colors.append(EMERALD)
                elif c in ["juice_rate", "no_color_rate"]:
                    bar_colors.append(ROSE)
                else:
                    bar_colors.append(AMBER)

            fig_rad = go.Figure(
                go.Bar(
                    x=radar_labels,
                    y=radar_vals,
                    marker_color=bar_colors,
                    hovertemplate="%{x}: %{y:.1f}%"
                )
            )
            apply_plot_theme(fig_rad, height=280)
            fig_rad.update_layout(showlegend=False, yaxis_title="Avg Rate %")
            st.plotly_chart(fig_rad, use_container_width=True)

st.markdown("---")

# ============================================================
# DEFECTS + MODES
# ============================================================
section_title("Defects & Mode Activity")

top_defects = pd.DataFrame(columns=["defect", "count"])
top_adjusted = pd.DataFrame(columns=["mode", "count"])
top_checked = pd.DataFrame(columns=["mode", "count"])

if batches is not None:
    batch_filtered = batches.copy()

    if selected_variety != "All" and "variety" in batch_filtered.columns:
        batch_filtered = batch_filtered[batch_filtered["variety"].astype(str) == selected_variety]

    if selected_grower != "All" and "grower" in batch_filtered.columns:
        batch_filtered = batch_filtered[batch_filtered["grower"].astype(str) == selected_grower]

    defect_cols = [c for c in ["defect_1", "defect_2", "defect_3"] if c in batch_filtered.columns]
    if defect_cols:
        dv = batch_filtered[defect_cols].melt(value_name="defect")["defect"].dropna().astype(str).str.strip()
        dv = dv[dv != ""]
        if not dv.empty:
            top_defects = dv.value_counts().reset_index()
            top_defects.columns = ["defect", "count"]

if changes is not None:
    ch = changes.copy()

    if selected_variety != "All" and "variety" in ch.columns:
        ch = ch[ch["variety"].astype(str) == selected_variety]

    run_ids = filtered_df["run_id"].dropna().astype(str).unique().tolist() if "run_id" in filtered_df.columns else []
    if "run_id" in ch.columns and run_ids:
        ch = ch[ch["run_id"].astype(str).isin(run_ids)]

    if "mode" in ch.columns and "action" in ch.columns:
        adjusted = ch[ch["action"].astype(str).str.lower().str.startswith("a")]
        checked = ch[ch["action"].astype(str).str.lower().str.startswith("c")]

        if not adjusted.empty:
            top_adjusted = adjusted["mode"].astype(str).value_counts().reset_index()
            top_adjusted.columns = ["mode", "count"]

        if not checked.empty:
            top_checked = checked["mode"].astype(str).value_counts().reset_index()
            top_checked.columns = ["mode", "count"]

dm1, dm2, dm3 = st.columns(3)

with dm1:
    section_title("Top Defects")
    if not top_defects.empty:
        fig_def = px.bar(
            top_defects.head(8),
            x="count",
            y="defect",
            orientation="h",
            color_discrete_sequence=[ROSE]
        )
        fig_def.update_traces(hovertemplate="%{y}: %{x}")
        apply_plot_theme(fig_def, height=280)
        st.plotly_chart(fig_def, use_container_width=True)
    else:
        st.info("No defect data.")

with dm2:
    section_title("Top Adjusted Modes")
    if not top_adjusted.empty:
        fig_adj = px.bar(
            top_adjusted.head(8),
            x="count",
            y="mode",
            orientation="h",
            color_discrete_sequence=[AMBER]
        )
        apply_plot_theme(fig_adj, height=280)
        st.plotly_chart(fig_adj, use_container_width=True)
    else:
        st.info("No adjustment data.")

with dm3:
    section_title("Top Checked Modes")
    if not top_checked.empty:
        fig_chk = px.bar(
            top_checked.head(8),
            x="count",
            y="mode",
            orientation="h",
            color_discrete_sequence=[BLUE]
        )
        apply_plot_theme(fig_chk, height=280)
        st.plotly_chart(fig_chk, use_container_width=True)
    else:
        st.info("No check data.")

# ============================================================
# PREMIUM RATE BY VARIETY
# ============================================================
if "premium_rate" in quality_df.columns and "variety" in quality_df.columns:
    st.markdown("---")
    section_title("Premium Rate by Variety (All Time)")

    premium_variety = (
        quality_df.groupby("variety", as_index=False)["premium_rate"]
        .mean(numeric_only=True)
        .dropna()
        .sort_values("premium_rate", ascending=False)
    )

    if not premium_variety.empty:
        fig_pv = px.bar(
            premium_variety,
            x="variety",
            y="premium_rate",
            color="premium_rate",
            color_continuous_scale=["#1e2435", EMERALD],
            labels={"variety": "Variety", "premium_rate": "Avg Premium %"},
        )
        fig_pv.update_coloraxes(showscale=False)
        fig_pv.update_traces(hovertemplate="%{x}: %{y:.1f}%")
        apply_plot_theme(fig_pv, height=280)
        st.plotly_chart(fig_pv, use_container_width=True)
