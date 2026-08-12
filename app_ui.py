import html

import streamlit as st


APP_NAME = "Kanji Studio"


def apply_app_style():
    """全ページ共通の製品向けレスポンシブスタイルを適用する。"""
    st.markdown(
        """
        <style>
        :root {
          --ks-ink: #172033;
          --ks-muted: #667085;
          --ks-line: #e4e7ec;
          --ks-surface: #ffffff;
          --ks-soft: #f7f8fa;
          --ks-brand: #3157d5;
          --ks-brand-soft: #eef2ff;
          --ks-success: #157f5b;
          --ks-warning: #b54708;
        }
        .stApp { background: #f6f7f9; color: var(--ks-ink); }
        [data-testid="stHeader"] { background: rgba(246,247,249,.88); backdrop-filter: blur(12px); }
        [data-testid="stSidebar"] { background: #111827; }
        [data-testid="stSidebar"] * { color: #f8fafc; }
        [data-testid="stSidebarNav"] a { border-radius: 10px; margin: 2px 8px; }
        [data-testid="stSidebarNav"] a:hover { background: rgba(255,255,255,.10); }
        .block-container { max-width: 1440px; padding-top: 2rem; padding-bottom: 4rem; }
        h1, h2, h3 { color: var(--ks-ink); letter-spacing: -.025em; }
        h1 { font-size: clamp(1.8rem, 3vw, 2.55rem); }
        h2 { margin-top: 1.5rem; }
        div[data-testid="stMetric"] {
          background: var(--ks-surface); border: 1px solid var(--ks-line);
          border-radius: 14px; padding: 16px 18px; box-shadow: 0 1px 2px rgba(16,24,40,.04);
        }
        div[data-testid="stMetricLabel"] { color: var(--ks-muted); }
        div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] {
          border: 1px solid var(--ks-line); border-radius: 14px; overflow: hidden;
          box-shadow: 0 1px 2px rgba(16,24,40,.04);
        }
        .stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] button {
          min-height: 42px; border-radius: 10px; font-weight: 650;
        }
        .stTextInput input, .stTextArea textarea, div[data-baseweb="select"] > div {
          border-radius: 10px;
        }
        div[data-testid="stAlert"] { border-radius: 12px; }
        div[data-testid="stExpander"] { background: white; border-radius: 12px; }
        .ks-eyebrow { color: var(--ks-brand); font-size: .78rem; font-weight: 750; letter-spacing: .12em; text-transform: uppercase; }
        .ks-lead { color: var(--ks-muted); font-size: 1.02rem; max-width: 760px; margin: -.25rem 0 1.25rem; }
        .ks-card {
          height: 100%; background: white; border: 1px solid var(--ks-line); border-radius: 16px;
          padding: 20px; box-shadow: 0 1px 2px rgba(16,24,40,.04);
        }
        .ks-card h3 { font-size: 1.05rem; margin: 0 0 6px; }
        .ks-card p { color: var(--ks-muted); margin: 0; font-size: .92rem; line-height: 1.6; }
        .ks-section-label { color: var(--ks-muted); font-size: .82rem; font-weight: 700; margin: 1.75rem 0 .65rem; }
        .ks-mobile-note { display: none; }
        @media (max-width: 768px) {
          .block-container { padding: 1rem 1rem 3rem; }
          [data-testid="stHorizontalBlock"] { flex-direction: column; gap: .6rem; }
          [data-testid="column"] { width: 100% !important; flex: 1 1 100% !important; }
          div[data-testid="stMetric"] { padding: 13px 15px; }
          .ks-mobile-note { display: block; background: var(--ks-brand-soft); color: #3448a8; border-radius: 10px; padding: 11px 13px; margin-bottom: 12px; font-size: .88rem; }
          .stButton > button, .stDownloadButton > button { width: 100%; }
          h1 { margin-bottom: .25rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title, description, eyebrow=APP_NAME):
    st.markdown(f'<div class="ks-eyebrow">{html.escape(eyebrow)}</div>', unsafe_allow_html=True)
    st.title(title)
    st.markdown(f'<div class="ks-lead">{html.escape(description)}</div>', unsafe_allow_html=True)


def feature_card(title, description):
    st.markdown(
        f'<div class="ks-card"><h3>{html.escape(title)}</h3><p>{html.escape(description)}</p></div>',
        unsafe_allow_html=True,
    )


def mobile_note(text):
    st.markdown(f'<div class="ks-mobile-note">{html.escape(text)}</div>', unsafe_allow_html=True)
