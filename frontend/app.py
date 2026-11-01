"""
AVSAR — Streamlit Frontend
Autonomous student government scheme navigator powered by AI.
"""

import os
import streamlit as st
import requests
import pandas as pd
import json
import uuid
from typing import Optional

from storage import (
    get_scheme_id,
    get_user_applications,
    is_scheme_applied,
    mark_as_applied,
    unmark_applied,
    toggle_applied,
)

# ─── Page Configuration ────────────────────────────────────────────────────────

st.set_page_config(
    page_title="AVSAR",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Constants ─────────────────────────────────────────────────────────────────

BACKEND_URL = os.environ.get("BACKEND_URL", "https://avsar-backend-yyeq.onrender.com")

INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
    "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim",
    "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand",
    "West Bengal",
    # Union Territories
    "Andaman and Nicobar Islands", "Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu", "Delhi",
    "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry",
]

# Rich, vibrant scheme category colors (curated to suit blue, zero harsh reds)
CATEGORY_COLORS = {
    "scholarship": "#2563EB",        # Royal Blue
    "education_loan": "#0284C7",     # Vivid Cyan / Sky
    "hostel": "#7C3AED",             # Vivid Purple
    "fee_reimbursement": "#D97706",   # Rich Amber
    "digital_access": "#0891B2",     # Deep Cyan
    "skill_development": "#059669",   # Emerald Green
    "research_fellowship": "#4F46E5",# Indigo
    "study_abroad": "#0369A1",       # Ocean Blue
    "girl_child": "#A21CAF",         # Magenta / Fuchsia
    "differently_abled": "#EA580C",   # Tangerine Orange
    "sports": "#16A34A",             # Bright Leaf Green
    "health_insurance": "#0D9488",   # Teal
    "book_grant": "#92400E",         # Warm Ochre
    "internship": "#3B82F6",         # Electric Blue
}

CATEGORY_LABELS = {
    "scholarship": "Scholarship",
    "education_loan": "Education Loan",
    "hostel": "Hostel Accommodation",
    "fee_reimbursement": "Fee Reimbursement",
    "digital_access": "Digital Access & Devices",
    "skill_development": "Skill Development",
    "research_fellowship": "Research Fellowship",
    "study_abroad": "Study Abroad",
    "girl_child": "Girl Child Education",
    "differently_abled": "Differently Abled Support",
    "sports": "Sports Scholarship",
    "health_insurance": "Student Health Insurance",
    "book_grant": "Book & Equipment Grant",
    "internship": "Internship & Apprenticeship",
}

# ─── Custom CSS ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    /* ── Global Styles (Toned-down glare-free light slate canvas) ── */
    :root {
        --primary: #2563EB;
        --primary-hover: #1D4ED8;
        --secondary: #0F172A;
        --surface: #F8FAFC;
        --bg-page: #EEF2F6;
        --border-color: #CBD5E1;
        --border-color-dark: #334155;
        --text-main: #0F172A;
        --text-muted: #475569;
        --success: #059669;
        --warning: #D97706;
    }

    /* Soft toned-down light canvas (not harsh blinding pure white) */
    .stApp,
    [data-testid="stAppViewContainer"],
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        color: #0F172A !important;
        background-color: #EEF2F6 !important;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* ── Sidebar General Styling ── */
    section[data-testid="stSidebar"] {
        background-color: #0B132B !important;
        border-right: 1.5px solid #1E293B !important;
    }

    /* Make sidebar comfortable, roomy and bigger when open */
    section[data-testid="stSidebar"]:not([data-collapsed="true"]) {
        min-width: 360px !important;
    }

    section[data-testid="stSidebar"][data-collapsed="true"] {
        min-width: 0 !important;
        max-width: 0 !important;
    }

    [data-testid="stSidebarUserContent"] {
        padding: 0 1.25rem 2rem 1.25rem !important;
    }

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] h4,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label {
        color: #F8FAFC !important;
    }

    /* ── Sidebar Collapse and Expand Buttons ── */
    [data-testid="stSidebarHeader"] {
        background-color: #0B132B !important;
        padding: 14px 16px 8px 16px !important;
    }

    /* Collapse button (top right of sidebar header) */
    [data-testid="stSidebarCollapseButton"],
    [data-testid="stSidebarCollapseButton"] button {
        background-color: #162447 !important;
        color: #38BDF8 !important;
        border: 1.5px solid #1F4068 !important;
        border-radius: 8px !important;
        width: 36px !important;
        height: 36px !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        cursor: pointer !important;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.25) !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    [data-testid="stSidebarCollapseButton"] button svg,
    [data-testid="stSidebarCollapseButton"] svg {
        fill: #38BDF8 !important;
        color: #38BDF8 !important;
        stroke: #38BDF8 !important;
        width: 20px !important;
        height: 20px !important;
    }

    [data-testid="stSidebarCollapseButton"] button:hover,
    [data-testid="stSidebarCollapseButton"]:hover {
        background-color: #1D4ED8 !important;
        border-color: #60A5FA !important;
        color: #FFFFFF !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.45) !important;
        transform: scale(1.05) !important;
    }

    [data-testid="stSidebarCollapseButton"] button:hover svg,
    [data-testid="stSidebarCollapseButton"]:hover svg {
        fill: #FFFFFF !important;
        color: #FFFFFF !important;
        stroke: #FFFFFF !important;
    }

    /* Expand button (floats at top-left when sidebar is collapsed/hidden) */
    [data-testid="stExpandSidebarButton"],
    button[data-testid="stExpandSidebarButton"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="stSidebarCollapsedControl"] button,
    [data-testid="collapsedControl"],
    [data-testid="collapsedControl"] button {
        display: inline-flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        position: fixed !important;
        top: 14px !important;
        left: 14px !important;
        background-color: #0B132B !important;
        color: #38BDF8 !important;
        border: 1.5px solid #1F4068 !important;
        border-radius: 8px !important;
        width: 40px !important;
        height: 40px !important;
        align-items: center !important;
        justify-content: center !important;
        cursor: pointer !important;
        z-index: 999999 !important;
        box-shadow: 0 4px 14px rgba(11, 19, 43, 0.35) !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    [data-testid="stExpandSidebarButton"] svg,
    button[data-testid="stExpandSidebarButton"] svg,
    [data-testid="stSidebarCollapsedControl"] svg,
    [data-testid="collapsedControl"] svg {
        fill: #38BDF8 !important;
        color: #38BDF8 !important;
        stroke: #38BDF8 !important;
        width: 22px !important;
        height: 22px !important;
    }

    [data-testid="stExpandSidebarButton"]:hover,
    button[data-testid="stExpandSidebarButton"]:hover,
    [data-testid="stSidebarCollapsedControl"]:hover,
    [data-testid="stSidebarCollapsedControl"] button:hover,
    [data-testid="collapsedControl"]:hover,
    [data-testid="collapsedControl"] button:hover {
        background-color: #1D4ED8 !important;
        border-color: #60A5FA !important;
        color: #FFFFFF !important;
        box-shadow: 0 6px 18px rgba(37, 99, 235, 0.5) !important;
        transform: scale(1.08) !important;
    }

    [data-testid="stExpandSidebarButton"]:hover svg,
    button[data-testid="stExpandSidebarButton"]:hover svg,
    [data-testid="stSidebarCollapsedControl"]:hover svg,
    [data-testid="collapsedControl"]:hover svg {
        fill: #FFFFFF !important;
        color: #FFFFFF !important;
        stroke: #FFFFFF !important;
    }

    /* ── Main Canvas Smooth Centralisation & Symmetrical Layout ── */
    .stMain {
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        width: 100% !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    .stMain > div:first-child {
        width: 100% !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
    }

    .block-container,
    [data-testid="stMainBlockContainer"] {
        max-width: 1180px !important;
        width: 100% !important;
        margin-left: auto !important;
        margin-right: auto !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        padding-top: 2.5rem !important;
        padding-bottom: 4rem !important;
        box-sizing: border-box !important;
        transition: max-width 0.3s cubic-bezier(0.4, 0, 0.2, 1),
                    padding 0.3s cubic-bezier(0.4, 0, 0.2, 1),
                    margin 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    /* ── Sidebar Navigation Buttons (Executive Button Cards) ── */
    [data-testid="stSidebar"] .stButton {
        margin-bottom: 4px !important;
    }

    [data-testid="stSidebar"] .stButton > button {
        width: 100% !important;
        text-align: left !important;
        justify-content: flex-start !important;
        padding: 12px 16px !important;
        font-size: 0.95rem !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        letter-spacing: 0.02em !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    /* Inactive Navigation Buttons in Sidebar */
    [data-testid="stSidebar"] .stButton > button[kind="secondary"],
    [data-testid="stSidebar"] .stButton > button:not([kind="primary"]) {
        background-color: #162447 !important;
        color: #E2E8F0 !important;
        border: 1.5px solid #1F4068 !important;
        border-left: 4.5px solid #334155 !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2) !important;
    }

    [data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover,
    [data-testid="stSidebar"] .stButton > button:not([kind="primary"]):hover {
        background-color: #1F3460 !important;
        border-color: #38BDF8 !important;
        border-left-color: #38BDF8 !important;
        color: #FFFFFF !important;
        transform: translateX(4px) !important;
        box-shadow: 0 3px 10px rgba(56, 189, 248, 0.25) !important;
    }

    /* Active Navigation Button in Sidebar */
    [data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #1D4ED8 0%, #2563EB 100%) !important;
        color: #FFFFFF !important;
        border: 1.5px solid #60A5FA !important;
        border-left: 5px solid #38BDF8 !important;
        box-shadow: 0 3px 12px rgba(37, 99, 235, 0.45) !important;
        transform: translateX(4px) !important;
    }

    /* Sidebar Dropdowns and Inputs */
    [data-testid="stSidebar"] [data-baseweb="select"] {
        background-color: #162447 !important;
        border: 1px solid #1F4068 !important;
        border-radius: 6px !important;
        color: #F8FAFC !important;
    }

    [data-testid="stSidebar"] [data-baseweb="tag"] {
        background-color: #1E3A8A !important;
        color: #BFDBFE !important;
        border-radius: 4px !important;
        border: 1px solid #3B82F6 !important;
    }

    [data-testid="stSidebar"] .stSlider > div {
        color: #F8FAFC !important;
    }

    /* ── Main Canvas Button Overrides (Blue palette replacing red) ── */
    .stMain .stButton > button,
    .stMain button[kind="primary"],
    .stMain button[kind="secondary"] {
        border-radius: 8px !important;
        font-weight: 600 !important;
        letter-spacing: 0.01em !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    /* Primary Buttons in Main: Vivid Royal Blue Gradient */
    .stMain .stButton > button[kind="primary"],
    .stMain button[kind="primary"] {
        background: linear-gradient(135deg, #1D4ED8 0%, #2563EB 100%) !important;
        color: #FFFFFF !important;
        border: 1px solid #1D4ED8 !important;
        box-shadow: 0 2px 6px rgba(37, 99, 235, 0.22) !important;
    }
    .stMain .stButton > button[kind="primary"]:hover,
    .stMain button[kind="primary"]:hover {
        background: linear-gradient(135deg, #1E40AF 0%, #1D4ED8 100%) !important;
        border-color: #1E40AF !important;
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35) !important;
        transform: translateY(-1px) !important;
    }

    /* Secondary Buttons in Main: Soft Pearl Surface with Royal Blue Accents */
    .stMain .stButton > button[kind="secondary"],
    .stMain .stButton > button:not([kind="primary"]),
    .stMain button[kind="secondary"] {
        background-color: #F8FAFC !important;
        color: #1D4ED8 !important;
        border: 1.5px solid #BFDBFE !important;
        box-shadow: 0 1px 3px rgba(37, 99, 235, 0.06) !important;
    }
    .stMain .stButton > button[kind="secondary"]:hover,
    .stMain .stButton > button:not([kind="primary"]):hover,
    .stMain button[kind="secondary"]:hover {
        background-color: #EFF6FF !important;
        border-color: #3B82F6 !important;
        color: #1E40AF !important;
        box-shadow: 0 3px 10px rgba(59, 130, 246, 0.16) !important;
        transform: translateY(-1px) !important;
    }

    /* Link Buttons: Vibrant Ocean Blue */
    .stLinkButton > a,
    [data-testid="stLinkButton"] > a {
        background: linear-gradient(135deg, #0284C7 0%, #0369A1 100%) !important;
        color: #FFFFFF !important;
        border: 1px solid #0284C7 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        box-shadow: 0 2px 6px rgba(2, 132, 199, 0.25) !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        text-decoration: none !important;
    }
    .stLinkButton > a:hover,
    [data-testid="stLinkButton"] > a:hover {
        background: linear-gradient(135deg, #0369A1 0%, #075985 100%) !important;
        border-color: #075985 !important;
        box-shadow: 0 4px 14px rgba(2, 132, 199, 0.38) !important;
        color: #FFFFFF !important;
        transform: translateY(-1px) !important;
    }

    /* Download Buttons: Fresh Mint / Emerald */
    .stDownloadButton > button {
        background-color: #EAF8EE !important;
        color: #047857 !important;
        border: 1.5px solid #A7F3D0 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }
    .stDownloadButton > button:hover {
        background-color: #DCFCE7 !important;
        border-color: #059669 !important;
        color: #065F46 !important;
        box-shadow: 0 3px 10px rgba(5, 150, 105, 0.18) !important;
        transform: translateY(-1px) !important;
    }

    /* ── Bullet Points & List Items (Sapphire / Royal Blue) ── */
    ul li::marker {
        color: #2563EB !important;
        font-size: 1.15em !important;
    }
    ol li::marker {
        color: #2563EB !important;
        font-weight: 700 !important;
    }
    li {
        margin-bottom: 5px;
        color: #334155;
    }

    /* Checkbox & Radio Accents (Replaces Streamlit red with vibrant blue) */
    input[type="checkbox"],
    input[type="radio"] {
        accent-color: #2563EB !important;
    }
    [data-baseweb="checkbox"] [checked] {
        background-color: #2563EB !important;
        border-color: #2563EB !important;
    }

    /* Progress Bar: Blue to Cyan Gradient */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #2563EB 0%, #06B6D4 100%) !important;
        border-radius: 6px !important;
    }
    .stProgress > div > div {
        background-color: #CBD5E1 !important;
        border-radius: 6px !important;
    }

    /* ── Hero Container (Vibrant Navy / Deep Sapphire) ── */
    .hero-container {
        background: linear-gradient(135deg, #0B192C 0%, #1E3A8A 55%, #0F2A4A 100%);
        border: 1px solid rgba(59, 130, 246, 0.3);
        border-top: 4px solid #38BDF8;
        border-radius: 12px;
        padding: 50px 36px;
        text-align: center;
        color: #FFFFFF;
        margin-bottom: 28px;
        box-shadow: 0 6px 24px rgba(15, 23, 42, 0.12);
    }
    .hero-badge {
        display: inline-block;
        padding: 5px 14px;
        background: rgba(56, 189, 248, 0.15);
        border: 1px solid rgba(56, 189, 248, 0.4);
        border-radius: 20px;
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #38BDF8;
        margin-bottom: 16px;
    }
    .hero-container h1 {
        font-size: 2.45rem;
        font-weight: 800;
        margin-bottom: 14px;
        letter-spacing: -0.02em;
        color: #FFFFFF;
        text-shadow: 0 2px 4px rgba(0,0,0,0.25);
    }
    .hero-container p {
        font-size: 1.12rem;
        color: #CBD5E1;
        max-width: 680px;
        margin: 0 auto;
        line-height: 1.6;
    }

    /* ── Colorful Stat Cards (Soft tinted surfaces, no harsh white) ── */
    .stat-card {
        border-radius: 10px;
        padding: 24px 20px;
        text-align: center;
        border: 1.5px solid #CBD5E1;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .stat-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0,0,0,0.08);
    }
    .stat-card-blue {
        border-top: 4px solid #2563EB;
        background: #EBF3FC;
        border-color: #BFDBFE;
    }
    .stat-card-purple {
        border-top: 4px solid #7C3AED;
        background: #F5EEFD;
        border-color: #DDD6FE;
    }
    .stat-card-teal {
        border-top: 4px solid #0D9488;
        background: #EAF7F5;
        border-color: #99F6E4;
    }
    .stat-num-blue   { color: #1D4ED8; font-size: 2.3rem; font-weight: 800; }
    .stat-num-purple { color: #6D28D9; font-size: 2.3rem; font-weight: 800; }
    .stat-num-teal   { color: #0F766E; font-size: 2.3rem; font-weight: 800; }
    .stat-label {
        font-size: 0.8rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #334155;
        margin-top: 6px;
    }

    /* ── Step Cards 01-04 (Soft pearl surface, dark clear typography) ── */
    .step-card {
        background: #F8FAFC;
        border: 1.5px solid #CBD5E1;
        border-radius: 10px;
        padding: 24px 18px;
        height: 100%;
        box-shadow: 0 2px 6px rgba(0,0,0,0.03);
        transition: transform 0.2s;
    }
    .step-card:hover {
        transform: translateY(-2px);
        border-color: #94A3B8;
    }
    .step-card-1 { border-top: 3.5px solid #2563EB; }
    .step-card-2 { border-top: 3.5px solid #6366F1; }
    .step-card-3 { border-top: 3.5px solid #0D9488; }
    .step-card-4 { border-top: 3.5px solid #D97706; }

    .step-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        border-radius: 8px;
        color: #FFFFFF;
        font-weight: 800;
        font-size: 0.88rem;
        margin-bottom: 14px;
    }
    .badge-blue   { background: linear-gradient(135deg, #1D4ED8 0%, #2563EB 100%); }
    .badge-indigo { background: linear-gradient(135deg, #4F46E5 0%, #6366F1 100%); }
    .badge-teal   { background: linear-gradient(135deg, #0F766E 0%, #0D9488 100%); }
    .badge-amber  { background: linear-gradient(135deg, #B45309 0%, #D97706 100%); }

    .step-title {
        font-weight: 700;
        font-size: 1.05rem;
        color: #0F172A;
        margin-bottom: 6px;
    }
    .step-desc {
        font-size: 0.88rem;
        color: #334155;
        line-height: 1.55;
    }

    /* ── Metric Summary Cards in Discovery Results ── */
    .metric-card {
        border-radius: 8px;
        padding: 16px 18px;
        border: 1.5px solid #CBD5E1;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        margin-bottom: 8px;
    }
    .metric-blue   { border-top: 3.5px solid #2563EB; background: #EBF3FC; border-color: #BFDBFE; }
    .metric-purple { border-top: 3.5px solid #7C3AED; background: #F5EEFD; border-color: #DDD6FE; }
    .metric-green  { border-top: 3.5px solid #059669; background: #EAF8EE; border-color: #A7F3D0; }
    .metric-teal   { border-top: 3.5px solid #0284C7; background: #EBF8FD; border-color: #BAE6FD; }
    .metric-label  { font-size: 0.78rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #475569; }
    .metric-val    { font-size: 1.7rem; font-weight: 800; color: #0F172A; margin-top: 4px; }

    /* ── Scheme Card (One single, compact outlined box) ── */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: #F8FAFC !important;
        border-radius: 10px !important;
        padding: 20px 22px !important;
        margin-bottom: 18px !important;
        border: 1.5px solid #CBD5E1 !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.03) !important;
        transition: all 0.2s ease-in-out !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: #93C5FD !important;
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.08) !important;
    }

    /* Keep progress bar and checklist inside card compact */
    [data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stProgress"] {
        margin: 6px 0 8px 0 !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"] details[data-testid="stExpander"] {
        background-color: #FFFFFF !important;
        border: 1.2px solid #E2E8F0 !important;
        border-radius: 8px !important;
        margin: 8px 0 !important;
    }
    .scheme-title {
        font-size: 1.22rem;
        font-weight: 800;
        color: #0F172A !important;
        margin-bottom: 6px;
        letter-spacing: -0.01em;
    }
    .scheme-desc {
        color: #334155;
        font-size: 0.92rem;
        line-height: 1.55;
        margin-top: 10px;
    }

    /* ── Badges & Chips ── */
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.03em;
        color: #FFFFFF;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    .benefit-chip {
        background: #DCFCE7;
        color: #065F46;
        border: 1.5px solid #86EFAC;
        border-radius: 6px;
        padding: 4px 12px;
        font-weight: 700;
        font-size: 0.86rem;
        display: inline-block;
        margin-left: 8px;
    }

    /* ── Match Reason Bullets ── */
    .match-reason {
        color: #1E40AF;
        font-size: 0.86rem;
        font-weight: 600;
        margin: 4px 0;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .match-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background-color: #2563EB;
        display: inline-block;
        box-shadow: 0 0 0 2.5px #BFDBFE;
    }

    /* ── Step Indicator (Toned-down form stepper) ── */
    .step-indicator {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 28px;
        background: #F8FAFC;
        padding: 16px 20px;
        border-radius: 10px;
        border: 1.5px solid #CBD5E1;
        box-shadow: 0 1px 4px rgba(0,0,0,0.03);
    }
    .step-dot {
        width: 30px;
        height: 30px;
        border-radius: 6px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 0.85rem;
        background: #E2E8F0;
        color: #475569;
        border: 1px solid #CBD5E1;
    }
    .step-dot.active {
        background: linear-gradient(135deg, #1D4ED8 0%, #2563EB 100%);
        color: #FFFFFF;
        border-color: #2563EB;
        box-shadow: 0 2px 6px rgba(37, 99, 235, 0.35);
    }
    .step-dot.done {
        background: #059669;
        color: #FFFFFF;
        border-color: #059669;
    }

    /* ── Section Header (Dark Navy, 100% visible) ── */
    .section-header {
        font-size: 1.45rem;
        font-weight: 800;
        color: #0F172A !important;
        border-left: 4.5px solid #2563EB;
        padding-left: 12px;
        border-bottom: 1.5px solid #CBD5E1;
        padding-bottom: 8px;
        margin-bottom: 24px;
        letter-spacing: -0.01em;
    }

    /* ── Callout Box ── */
    .info-box {
        background: #EBF3FC;
        border: 1.5px solid #BFDBFE;
        border-left: 4.5px solid #2563EB;
        border-radius: 8px;
        padding: 16px 18px;
        margin: 14px 0;
        font-size: 0.9rem;
        color: #1E3A8A;
        line-height: 1.55;
        font-weight: 500;
    }

    /* ── Application Guide Container ── */
    .guide-container {
        background: #F1F5F9;
        border: 1.5px solid #CBD5E1;
        border-left: 5px solid #2563EB;
        border-radius: 10px;
        padding: 24px;
        margin-top: 14px;
        margin-bottom: 20px;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.05);
    }
    .guide-header {
        font-size: 1.2rem;
        font-weight: 800;
        color: #0F172A;
        margin-bottom: 6px;
    }
    .guide-sub {
        font-size: 0.88rem;
        color: #475569;
        margin-bottom: 18px;
    }

    /* ── Tech Tags ── */
    .tech-tag {
        display: inline-block;
        background: #E0E7FF;
        color: #3730A3;
        border: 1px solid #C7D2FE;
        border-radius: 6px;
        padding: 5px 12px;
        margin: 3px;
        font-size: 0.84rem;
        font-weight: 600;
    }

    /* ── Hindi Voice Audio Widget ── */
    .hindi-voice-panel {
        background: #F8FAFC;
        border: 1.5px solid #CBD5E1;
        border-left: 5px solid #0284C7;
        border-radius: 10px;
        padding: 18px 20px;
        margin-top: 14px;
        margin-bottom: 8px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
    }
    .hindi-voice-header {
        font-size: 0.84rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #0369A1;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .hindi-voice-text {
        font-size: 0.96rem;
        color: #0F172A !important;
        line-height: 1.8;
        font-weight: 500;
        font-family: "Noto Sans Devanagari", "Mangal", -apple-system, sans-serif;
        background: #FFFFFF;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 12px;
        border: 1.5px solid #CBD5E1;
        box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.02);
        white-space: pre-wrap;
    }
</style>
""", unsafe_allow_html=True)

# ─── Session State Init ────────────────────────────────────────────────────────

if "page" not in st.session_state:
    st.session_state.page = "Home"
if "form_step" not in st.session_state:
    st.session_state.form_step = 1
if "form_data" not in st.session_state:
    st.session_state.form_data = {}
if "results" not in st.session_state:
    st.session_state.results = None
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "open_guides" not in st.session_state:
    st.session_state.open_guides = set()
if "guide_cache" not in st.session_state:
    st.session_state.guide_cache = {}
if "hindi_audio_cache" not in st.session_state:
    st.session_state.hindi_audio_cache = {}
if "hindi_audio_open" not in st.session_state:
    st.session_state.hindi_audio_open = set()
if "applications" not in st.session_state:
    st.session_state.applications = []

# Ensure user_id exists in session & URL query params for isolation and persistence
if "user_id" not in st.session_state:
    q_uid = st.query_params.get("uid")
    if q_uid:
        st.session_state.user_id = q_uid
    else:
        new_uid = f"user_{uuid.uuid4().hex[:8]}"
        st.session_state.user_id = new_uid
        st.query_params["uid"] = new_uid

# ─── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style='padding: 4px 0 16px 0; border-bottom: 1px solid #1E293B; margin-bottom: 20px;'>
        <div style='font-size: 1.35rem; font-weight: 800; color: #FFFFFF; letter-spacing: 0.05em;'>
            AVSAR
        </div>
        <div style='font-size: 0.76rem; color: #94A3B8; margin-top: 5px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em;'>
            National Student Scheme Navigator
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Sleek full-width navigation button cards (No native radio circles)
    nav_items = [
        ("Home", "Home"),
        ("Discover Schemes", "Discover"),
        ("My Applications", "Applications"),
        ("About", "About"),
    ]
    for label, key in nav_items:
        is_active = (st.session_state.page == key)
        b_type = "primary" if is_active else "secondary"
        if st.button(label, key=f"nav_btn_{key}", use_container_width=True, type=b_type):
            if st.session_state.page != key:
                st.session_state.page = key
                st.rerun()

    # If results are active on Discover page, render the dropdown filter in the sidebar
    if st.session_state.page == "Discover" and st.session_state.results is not None:
        schemes_raw = st.session_state.results.get("eligible_schemes", [])
        all_cats_found = sorted(list({s.get("category", "") for s in schemes_raw if s.get("category")}))

        st.markdown("<hr style='border-color: #1E293B; margin: 24px 0 16px 0;'/>", unsafe_allow_html=True)
        st.markdown("""
        <div style='font-size: 0.8rem; font-weight: 700; color: #38BDF8; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 10px;'>
            Filter Schemes
        </div>
        """, unsafe_allow_html=True)

        if "selected_categories" not in st.session_state or not set(st.session_state.selected_categories).issubset(set(all_cats_found)):
            st.session_state.selected_categories = all_cats_found

        category_labels_dict = {cat: CATEGORY_LABELS.get(cat, cat.replace("_", " ").title()) for cat in all_cats_found}

        sidebar_selected_cats = st.multiselect(
            "Filter by Category",
            options=all_cats_found,
            default=st.session_state.selected_categories,
            format_func=lambda c: category_labels_dict.get(c, c),
            placeholder="Select categories...",
            help="Filter visible schemes by category",
        )
        st.session_state.selected_categories = sidebar_selected_cats

        st.session_state.min_score_filter = st.slider(
            "Minimum Match Score (%)",
            min_value=0,
            max_value=100,
            value=st.session_state.get("min_score_filter", 0),
            step=5,
            help="Show schemes matching above this percentage",
        )

    st.markdown("<hr style='border-color: #1E293B; margin: 24px 0 16px 0;'/>", unsafe_allow_html=True)
    st.markdown("""
    <div style='font-size: 0.76rem; color: #94A3B8; line-height: 1.5;'>
        Official directories indexed:<br/>
        <span style='color: #60A5FA; font-weight: 600;'>myscheme.gov.in · scholarships.gov.in · vidyalakshmi.co.in</span>
        <div style='margin-top: 12px; font-size: 0.72rem; color: #64748B;'>
            Government of India National Standards Compliant
        </div>
    </div>
    """, unsafe_allow_html=True)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def backend_post(endpoint: str, payload: dict) -> Optional[dict]:
    """POST to backend; returns parsed JSON or None on error."""
    try:
        resp = requests.post(
            f"{BACKEND_URL}{endpoint}",
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        st.error(
            "**Backend service unavailable.**\n\n"
            "Ensure the FastAPI server is running:\n```bash\ncd backend\nuvicorn main:app --reload --port 8000\n```"
        )
        return None
    except requests.exceptions.Timeout:
        st.error("Request timed out. The server is processing the request — please retry shortly.")
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"Backend error: {e.response.status_code} — {e.response.text[:300]}")
        return None
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        return None


def score_color(score: float) -> str:
    """Colors tuned for soft slate canvas (Emerald -> Royal Blue -> Slate Steel)."""
    if score >= 0.75:
        return "#059669"  # Vibrant Emerald
    elif score >= 0.5:
        return "#2563EB"  # Royal Blue
    return "#475569"      # Refined Dark Slate Steel (ultra-visible on light slate, zero harsh reds)


def results_to_df(schemes: list) -> pd.DataFrame:
    rows = []
    for s in schemes:
        rows.append({
            "Scheme Name": s.get("name", ""),
            "Category": CATEGORY_LABELS.get(s.get("category", ""), s.get("category", "")),
            "Eligibility Score (%)": round(s.get("eligibility_score", 0) * 100, 1),
            "Benefit": s.get("benefit_amount", "—"),
            "Portal": s.get("application_portal", ""),
            "URL": s.get("portal_url", ""),
            "Deadline": s.get("deadline", "—"),
        })
    return pd.DataFrame(rows)


# ─── Page: HOME ───────────────────────────────────────────────────────────────

def page_home():
    st.markdown("""
    <div class='hero-container'>
        <div class='hero-badge'>Government Scheme & Welfare Directory</div>
        <h1>Find Government Scholarships and Schemes</h1>
        <p>
            AVSAR systematically matches your academic profile against 500+ central and state
            government welfare programs, calculates eligibility thresholds, and provides guided application assistance.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div class='stat-card stat-card-blue'>
            <div class='stat-num-blue'>500+</div>
            <div class='stat-label'>Government Schemes Indexed</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class='stat-card stat-card-purple'>
            <div class='stat-num-purple'>14</div>
            <div class='stat-label'>Welfare Categories</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class='stat-card stat-card-teal'>
            <div class='stat-num-teal'>100%</div>
            <div class='stat-label'>Verified Government Portals</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        if st.button("Get Started — Find Matching Schemes", use_container_width=True, type="primary"):
            st.session_state.page = "Discover"
            st.session_state.form_step = 1
            st.rerun()

    st.markdown("<br/>", unsafe_allow_html=True)

    st.markdown("<div class='section-header'>System Process</div>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    steps = [
        ("01", "badge-blue", "step-card-1", "Profile Assessment", "Enter your academic record, caste category, domicile state, and annual family income."),
        ("02", "badge-indigo", "step-card-2", "Algorithmic Matching", "The system verifies criteria against official central and state guidelines."),
        ("03", "badge-teal", "step-card-3", "Ranked Results", "Examine prioritized schemes with calculated benefit amounts, deadlines, and documentation."),
        ("04", "badge-amber", "step-card-4", "Application Guidance", "Access step-by-step submission checklists and authenticated portal links."),
    ]
    for col, (num, badge_cls, card_cls, title, desc) in zip([c1, c2, c3, c4], steps):
        with col:
            st.markdown(f"""
            <div class='step-card {card_cls}'>
                <div class='step-badge {badge_cls}'>{num}</div>
                <div class='step-title'>{title}</div>
                <div class='step-desc'>{desc}</div>
            </div>""", unsafe_allow_html=True)


# ─── Page: DISCOVER ───────────────────────────────────────────────────────────

def render_step_indicator(current: int):
    steps = ["Basic Details", "Academic Record", "Verification & Additional"]
    html = "<div class='step-indicator'>"
    for i, label in enumerate(steps, 1):
        cls = "done" if i < current else ("active" if i == current else "")
        num_display = str(i)
        html += f"""
        <div style='display:flex; align-items:center; gap:8px;'>
            <div class='step-dot {cls}'>{num_display}</div>
            <span style='font-size:0.86rem; color:{"#1D4ED8" if i==current else ("#059669" if i<current else "#475569")};
                         font-weight:{"700" if i==current else "600"};'>{label}</span>
        </div>
        """
        if i < 3:
            line_color = "#2563EB" if i < current else "#CBD5E1"
            html += f"<div style='flex:1; height:2px; background:{line_color}; margin:0 8px;'></div>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def page_discover():
    st.markdown("<div class='section-header'>Discover Government Schemes</div>", unsafe_allow_html=True)

    if st.session_state.results is None:
        _show_discovery_form()
    else:
        _show_results()


def _show_discovery_form():
    render_step_indicator(st.session_state.form_step)

    fd = st.session_state.form_data

    # ── Step 1: Basic Info ────────────────────────────────────────────────────
    if st.session_state.form_step == 1:
        st.markdown("#### Step 1: Personal & Domicile Information")
        with st.container():
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Full Name *", value=fd.get("name", ""), placeholder="e.g. Priya Sharma")
                age = st.number_input("Age *", min_value=14, max_value=35, value=fd.get("age", 18))
                gender = st.selectbox(
                    "Gender *",
                    ["Male", "Female", "Other"],
                    index=["Male", "Female", "Other"].index(fd.get("gender", "Female")),
                )
            with col2:
                state = st.selectbox(
                    "State / Union Territory *",
                    INDIAN_STATES,
                    index=INDIAN_STATES.index(fd.get("state", "Maharashtra")) if fd.get("state") in INDIAN_STATES else 13,
                )
                district = st.text_input("District (optional)", value=fd.get("district", ""), placeholder="e.g. Pune")

        st.markdown("<br/>", unsafe_allow_html=True)
        if st.button("Proceed to Academic Details", type="primary"):
            if not name.strip():
                st.error("Please enter your full name.")
            else:
                fd.update({"name": name, "age": age, "gender": gender.lower(), "state": state, "district": district})
                st.session_state.form_step = 2
                st.rerun()

    # ── Step 2: Academic Info ─────────────────────────────────────────────────
    elif st.session_state.form_step == 2:
        st.markdown("#### Step 2: Academic & Institutional Details")
        col1, col2 = st.columns(2)
        with col1:
            category_opts = ["General", "SC", "ST", "OBC", "EWS", "Minority"]
            category = st.selectbox(
                "Social Category *",
                category_opts,
                index=category_opts.index(fd.get("category", "General")),
            )
            income = st.number_input(
                "Annual Family Income (INR) *",
                min_value=0,
                max_value=2_000_000,
                value=fd.get("annual_family_income", 200_000),
                step=10_000,
            )
            income_slider = st.slider(
                "Income Adjustment Slider (INR)",
                0, 1_500_000, income, step=5_000,
                help="Adjust annual family income to match official income certificate",
            )
            income = max(income, income_slider)

            edu_opts = ["Class 8", "Class 10", "Class 12", "Diploma", "Undergraduate", "Postgraduate", "PhD", "Vocational"]
            education_level = st.selectbox(
                "Current Education Level *",
                edu_opts,
                index=edu_opts.index(fd.get("education_level_label", "Undergraduate")),
            )

        with col2:
            course = st.text_input("Course or Program Name *", value=fd.get("course", ""), placeholder="e.g. B.Tech Computer Science")
            stream_opts = ["Science", "Arts", "Commerce", "Engineering", "Medical", "Law", "Vocational", "Other"]
            stream = st.selectbox(
                "Academic Stream *",
                stream_opts,
                index=stream_opts.index(fd.get("stream", "Engineering")),
            )
            inst_opts = ["Government", "Private", "Aided"]
            institution_type = st.selectbox(
                "Institution Type *",
                inst_opts,
                index=inst_opts.index(fd.get("institution_type_label", "Government")),
            )
            percentage = st.slider(
                "Previous Academic Percentage / Normalized CGPA *",
                0.0, 100.0, float(fd.get("percentage_marks", 75.0)), step=0.5,
            )

        st.markdown("<br/>", unsafe_allow_html=True)
        bcol1, bcol2 = st.columns([1, 1])
        with bcol1:
            if st.button("Previous Step"):
                st.session_state.form_step = 1
                st.rerun()
        with bcol2:
            if st.button("Proceed to Additional Details", type="primary"):
                if not course.strip():
                    st.error("Please enter your current course or program.")
                else:
                    edu_map = {
                        "Class 8": "class_8", "Class 10": "class_10", "Class 12": "class_12",
                        "Diploma": "diploma", "Undergraduate": "undergraduate",
                        "Postgraduate": "postgraduate", "PhD": "phd", "Vocational": "vocational",
                    }
                    inst_map = {"Government": "government", "Private": "private", "Aided": "aided"}
                    fd.update({
                        "category": category.lower() if category != "General" else "general",
                        "annual_family_income": income,
                        "education_level": edu_map[education_level],
                        "education_level_label": education_level,
                        "course": course,
                        "stream": stream,
                        "institution_type": inst_map[institution_type],
                        "institution_type_label": institution_type,
                        "percentage_marks": percentage,
                    })
                    st.session_state.form_step = 3
                    st.rerun()

    # ── Step 3: Additional Info ───────────────────────────────────────────────
    elif st.session_state.form_step == 3:
        st.markdown("#### Step 3: Verification & Additional Criteria")
        col1, col2 = st.columns(2)
        with col1:
            has_disability = st.checkbox("Person with Benchmark Disability (PwD)", value=fd.get("has_disability", False))
            disability_type = ""
            if has_disability:
                disability_type = st.text_input(
                    "Disability Classification",
                    value=fd.get("disability_type", ""),
                    placeholder="e.g. Visual Impairment, Locomotor Disability",
                )
            interests = st.multiselect(
                "Specialized Interests (if applicable)",
                ["Sports", "Research", "Arts", "Coding", "Agriculture", "None"],
                default=fd.get("interests", []),
            )

        with col2:
            aadhar = st.checkbox("Aadhaar Card Available for e-KYC", value=fd.get("aadhar_available", True))
            bank = st.checkbox("Active Student Bank Account (Aadhaar Seeded)", value=fd.get("bank_account_available", True))
            income_cert = st.checkbox("Valid Income Certificate Issued by Competent Authority", value=fd.get("income_certificate_available", True))

            st.markdown("""
            <div class='info-box'>
            Documentation Note: Direct Benefit Transfer (DBT) mandates an Aadhaar-seeded bank account. If any document is pending issuance, the system will still evaluate conditional eligibility.
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br/>", unsafe_allow_html=True)
        bcol1, bcol2 = st.columns([1, 1])
        with bcol1:
            if st.button("Previous Step"):
                st.session_state.form_step = 2
                st.rerun()
        with bcol2:
            if st.button("Find Matching Schemes", type="primary"):
                interests_clean = [i.lower() for i in interests if i != "None"]
                fd.update({
                    "has_disability": has_disability,
                    "disability_type": disability_type if has_disability else None,
                    "interests": interests_clean,
                    "aadhar_available": aadhar,
                    "bank_account_available": bank,
                    "income_certificate_available": income_cert,
                })
                _submit_and_fetch()


def _submit_and_fetch():
    fd = st.session_state.form_data

    profile = {
        "name": fd["name"],
        "age": fd["age"],
        "gender": fd["gender"].lower(),
        "state": fd["state"],
        "district": fd.get("district") or None,
        "category": fd["category"],
        "annual_family_income": fd["annual_family_income"],
        "education_level": fd["education_level"],
        "course": fd["course"],
        "stream": fd.get("stream"),
        "institution_type": fd["institution_type"],
        "percentage_marks": fd["percentage_marks"],
        "has_disability": fd.get("has_disability", False),
        "disability_type": fd.get("disability_type"),
        "interests": fd.get("interests", []),
        "aadhar_available": fd.get("aadhar_available", True),
        "bank_account_available": fd.get("bank_account_available", True),
        "income_certificate_available": fd.get("income_certificate_available", True),
    }

    payload = {"profile": profile, "auto_apply": False}

    with st.spinner("Evaluating profile against 500+ government welfare schemes..."):
        data = backend_post("/api/discover", payload)

    if data:
        st.session_state.results = data
        st.session_state.session_id = data.get("session_id")
        st.session_state.open_guides = set()
        st.session_state.guide_cache = {}
        st.rerun()


def _show_results():
    data = st.session_state.results
    schemes: list = data.get("eligible_schemes", [])

    # ── Summary Metrics Cards (Soft tinted surfaces, dark navy numbers) ────────
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div class='metric-card metric-blue'>
            <div class='metric-label'>Matching Schemes</div>
            <div class='metric-val'>{data.get("total_found", len(schemes))}</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class='metric-card metric-purple'>
            <div class='metric-label'>Categories Covered</div>
            <div class='metric-val'>{len(data.get("categories_covered", []))}</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class='metric-card metric-teal'>
            <div class='metric-label'>Processing Time</div>
            <div class='metric-val'>{data.get("processing_time_seconds", 0):.2f}s</div>
        </div>""", unsafe_allow_html=True)

    # ── Top Recommendations ───────────────────────────────────────────────────
    top = data.get("top_recommendations", [])
    if top:
        st.markdown(f"""
        <div class='info-box'>
        <b>Primary Recommendations:</b> {' · '.join(top[:3])}
        </div>""", unsafe_allow_html=True)

    # ── Recommended Next Steps ────────────────────────────────────────────────
    next_steps = data.get("next_steps", [])
    if next_steps:
        with st.expander("Recommended Next Steps"):
            for step in next_steps:
                st.markdown(f"- {step}")

    st.markdown("<hr style='border-color: #CBD5E1; margin: 20px 0;'/>", unsafe_allow_html=True)

    if not schemes:
        st.warning(
            "No matching schemes found for the specified criteria. Try adjusting the family income threshold "
            "or education level, or consult your respective state scholarship portal directly."
        )
        if st.button("Modify Search Criteria"):
            st.session_state.results = None
            st.session_state.form_step = 1
            st.rerun()
        return

    # Sort schemes by eligibility score descending
    schemes_sorted = sorted(schemes, key=lambda x: x.get("eligibility_score", 0), reverse=True)

    # ── Filter using Sidebar Dropdown State ────────────────────────────────────
    active_cats = st.session_state.get("selected_categories", [])
    min_score = st.session_state.get("min_score_filter", 0)

    filtered = [
        s for s in schemes_sorted
        if (not active_cats or s.get("category", "") in active_cats)
        and (round(s.get("eligibility_score", 0) * 100) >= min_score)
    ]

    # ── Action Bar: Count + Export ─────────────────────────────────────────────
    df = results_to_df(filtered)
    csv = df.to_csv(index=False).encode("utf-8")
    colA, colB = st.columns([4, 1])
    with colA:
        st.markdown(f"<span style='font-size:1.05rem; font-weight:700; color:#0F172A;'>Showing {len(filtered)} of {len(schemes)} eligible schemes</span>", unsafe_allow_html=True)
    with colB:
        st.download_button(
            label="Export Results (CSV)",
            data=csv,
            file_name="schemepath_results.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.markdown("<br/>", unsafe_allow_html=True)

    if not filtered:
        st.info("No schemes match the active sidebar filters. Select additional categories or lower the match score threshold.")

    # ── Scheme Cards ──────────────────────────────────────────────────────────
    for scheme in filtered:
        _render_scheme_card(scheme)

    st.markdown("<hr style='border-color: #CBD5E1; margin: 24px 0;'/>", unsafe_allow_html=True)
    if st.button("Start New Search"):
        st.session_state.results = None
        st.session_state.form_data = {}
        st.session_state.form_step = 1
        st.session_state.open_guides = set()
        st.session_state.guide_cache = {}
        st.session_state.hindi_audio_cache = {}
        st.session_state.hindi_audio_open = set()
        st.rerun()


def _render_scheme_card(scheme: dict):
    scheme_id = get_scheme_id(scheme)
    user_id = st.session_state.get("user_id", "default_user")
    is_applied = is_scheme_applied(user_id, scheme_id)

    score = scheme.get("eligibility_score", 0.0)
    score_pct = int(score * 100)
    cat = scheme.get("category", "scholarship")
    badge_color = CATEGORY_COLORS.get(cat, "#2563EB")
    cat_label = CATEGORY_LABELS.get(cat, cat.replace("_", " ").title())
    sc = score_color(score)

    with st.container(border=True):
        st.markdown(f"""
        <div style='display:flex; justify-content:space-between; align-items:flex-start;'>
            <div style='flex:1; padding-right:16px;'>
                <div class='scheme-title'>
                    {scheme.get('name', 'Government Scheme')}
                </div>
                <div>
                    <span class='badge' style='background:{badge_color};'>{cat_label}</span>
                    {"<span class='benefit-chip'>Benefit: " + scheme.get('benefit_amount','') + "</span>" if scheme.get('benefit_amount') else ""}
                </div>
            </div>
            <div style='text-align:right; min-width:130px;'>
                <div style='font-size:0.75rem; font-weight:700; text-transform:uppercase; color:#475569;'>Eligibility Match</div>
                <div style='font-size:1.65rem; font-weight:800; color:{sc};'>{score_pct}%</div>
            </div>
        </div>
        <div class='scheme-desc'>{scheme.get('description','')[:320]}…</div>
        """, unsafe_allow_html=True)

        st.progress(score)

        # Match Reasons with Blue Bullets
        reasons = scheme.get("match_reasons", [])
        if reasons:
            reasons_html = "".join([f"<div class='match-reason'><span class='match-dot'></span> {r}</div>" for r in reasons[:4]])
            st.markdown(f"<div style='margin-top:6px; margin-bottom:10px;'>{reasons_html}</div>", unsafe_allow_html=True)

        # Required Documents Expander
        docs = scheme.get("documents_required", [])
        if docs:
            with st.expander("Required Documents Checklist"):
                for doc in docs:
                    st.markdown(f"- {doc}")

        # Action Buttons: Apply on Portal | Mark as Applied | Application Guide | Listen in Hindi
        portal_url = scheme.get("portal_url", "")
        is_guide_open = scheme_id in st.session_state.open_guides
        is_audio_open = scheme_id in st.session_state.hindi_audio_open

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if portal_url:
                st.link_button("Apply on Portal ↗", portal_url, use_container_width=True)
            else:
                st.button("Apply on Portal ↗", disabled=True, use_container_width=True, key=f"apply_{scheme_id}")

        with col2:
            mark_btn_label = "✓ Marked Applied" if is_applied else "Mark as Applied"
            mark_btn_type = "primary" if is_applied else "secondary"
            if st.button(
                mark_btn_label,
                key=f"toggle_applied_{scheme_id}",
                type=mark_btn_type,
                use_container_width=True,
                help="Click to unmark" if is_applied else "Mark as applied to track in My Applications",
            ):
                toggle_applied(user_id, scheme)
                st.rerun()

        with col3:
            guide_button_text = "Close Guide" if is_guide_open else "Application Guide"
            if st.button(
                guide_button_text,
                key=f"guide_toggle_{scheme_id}",
                use_container_width=True,
            ):
                if is_guide_open:
                    st.session_state.open_guides.remove(scheme_id)
                else:
                    if scheme_id not in st.session_state.guide_cache:
                        _fetch_guide_for_scheme(scheme)
                    if scheme_id in st.session_state.guide_cache:
                        st.session_state.open_guides.add(scheme_id)
                st.rerun()

        with col4:
            audio_btn_label = "Hide Hindi" if is_audio_open else "Listen in Hindi"
            if st.button(
                audio_btn_label,
                key=f"hindi_toggle_{scheme_id}",
                use_container_width=True,
            ):
                if is_audio_open:
                    st.session_state.hindi_audio_open.discard(scheme_id)
                else:
                    # Invalidate old summary if outside the target 1-minute window (<300 or >680 chars)
                    cached_data = st.session_state.hindi_audio_cache.get(scheme_id)
                    if cached_data:
                        c_len = len(cached_data.get("text", ""))
                        if c_len < 300 or c_len > 680:
                            st.session_state.hindi_audio_cache.pop(scheme_id, None)

                    if scheme_id not in st.session_state.hindi_audio_cache:
                        _fetch_hindi_audio(scheme)
                    if scheme_id in st.session_state.hindi_audio_cache:
                        st.session_state.hindi_audio_open.add(scheme_id)
                st.rerun()

        # Render Hindi audio panel if open
        if is_audio_open and scheme_id in st.session_state.hindi_audio_cache:
            _render_hindi_audio_panel(scheme_id, st.session_state.hindi_audio_cache[scheme_id])

        # If guide is open for this card, render the dropdown section right below
        if is_guide_open and scheme_id in st.session_state.guide_cache:
            _render_guide_dropdown(scheme, st.session_state.guide_cache[scheme_id])


def _fetch_guide_for_scheme(scheme: dict):
    if not st.session_state.session_id:
        st.error("No active session found. Please run a scheme search first.")
        return

    payload = {
        "session_id": st.session_state.session_id,
        "scheme_id": scheme.get("scheme_id"),
        "profile": st.session_state.form_data,
    }
    with st.spinner(f"Compiling application guide for {scheme.get('name', 'scheme')}..."):
        result = backend_post("/api/guide", payload)

    if result and result.get("success"):
        st.session_state.guide_cache[scheme.get("scheme_id")] = result
    else:
        st.error("Unable to generate application guide. Please try again.")


def _fetch_hindi_audio(scheme: dict):
    """Fetch Hindi TTS summary from backend and store in session state cache."""
    if not st.session_state.session_id:
        st.error("No active session. Please run a scheme search first.")
        return

    payload = {
        "session_id": st.session_state.session_id,
        "scheme_id": scheme.get("scheme_id"),
    }
    with st.spinner(f"Preparing Hindi audio summary for {scheme.get('name', 'scheme')}..."):
        result = backend_post("/api/hindi-summary", payload)

    if result and result.get("success"):
        st.session_state.hindi_audio_cache[scheme.get("scheme_id")] = result
    else:
        st.error("Unable to generate Hindi audio summary. Please check your API key and try again.")


def _render_hindi_audio_panel(scheme_id: str, result: dict):
    """Render the Hindi audio panel with transcript and audio player."""
    import base64

    hindi_text = result.get("text", "")
    audio_b64  = result.get("audio_b64", "")

    text_html = f"<div class='hindi-voice-text'>{hindi_text}</div>" if hindi_text else ""
    panel_html = f"""
    <div class='hindi-voice-panel'>
        <div class='hindi-voice-header'>HINDI VOICE SUMMARY</div>
        {text_html}
    </div>
    """
    st.markdown(panel_html, unsafe_allow_html=True)

    if audio_b64:
        audio_bytes = base64.b64decode(audio_b64)
        st.audio(audio_bytes, format="audio/mp3")



def _render_guide_dropdown(scheme: dict, result: dict):
    scheme_id = scheme.get("scheme_id", "")
    guide = result.get("guide", {})
    scheme_name = result.get("scheme_name", scheme.get("name"))
    portal_url = result.get("portal_url", "")

    st.markdown(f"""
    <div class='guide-container'>
        <div class='guide-header'>Personalized Application Guide: {scheme_name}</div>
        <div class='guide-sub'>Follow these verified guidelines to submit your application on the official portal.</div>
    """, unsafe_allow_html=True)

    # Pre-filled values
    st.markdown("##### Pre-filled Profile Values")
    st.caption("Use these values precisely when entering information on the portal form:")
    pre = guide.get("pre_filled_values", {})
    if pre:
        cols = st.columns(2)
        for i, (field, value) in enumerate(pre.items()):
            cols[i % 2].markdown(f"**{field}:** `{value}`")

    st.markdown("<br/>", unsafe_allow_html=True)

    # Step-by-step
    st.markdown("##### Step-by-Step Instructions")
    steps = guide.get("steps", [])
    for idx, step in enumerate(steps, 1):
        st.markdown(f"**{idx}.** {step}")

    st.markdown("<br/>", unsafe_allow_html=True)

    # Documents checklist
    st.markdown("##### Required Verification Documents")
    for doc_item in guide.get("documents_checklist", []):
        note = f" — *{doc_item.get('note')}*" if doc_item.get("note") else ""
        st.markdown(f"- **{doc_item.get('doc')}**{note}")

    # Pro tips
    tips = guide.get("pro_tips", [])
    if tips:
        st.markdown("<br/>", unsafe_allow_html=True)
        st.markdown("##### Key Notes & Recommendations")
        for tip in tips:
            st.markdown(f"- {tip}")

    # Deadline + Time
    st.markdown("<br/>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**Application Deadline:** {guide.get('deadline_note', 'Refer to official portal notification')}")
    with col2:
        st.info(f"**Estimated Completion Time:** {guide.get('estimated_time', '30–45 minutes')}")

    # Portal Link and Close Guide Button
    c_btn1, c_btn2 = st.columns([3, 1])
    with c_btn1:
        if portal_url:
            st.link_button("Open Official Portal", portal_url, use_container_width=True)
    with c_btn2:
        if st.button("Close Guide", key=f"close_bottom_{scheme_id}", use_container_width=True):
            st.session_state.open_guides.remove(scheme_id)
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ─── Page: APPLICATIONS ───────────────────────────────────────────────────────

def page_applications():
    st.markdown("<div class='section-header'>My Applications</div>", unsafe_allow_html=True)

    # ── 1. Compact Application Overview (Summary Cards) ─────────────────────────
    user_id = st.session_state.get("user_id", "default_user")
    applied_dict = get_user_applications(user_id)
    apps = list(applied_dict.values())

    total_count = len(apps)
    submitted_count = len(apps)
    under_review_count = 0
    approved_count = 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class='metric-card metric-blue'>
            <div class='metric-label'>Total Applications</div>
            <div class='metric-val'>{total_count}</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class='metric-card metric-teal'>
            <div class='metric-label'>Marked Applied</div>
            <div class='metric-val'>{submitted_count}</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class='metric-card metric-purple'>
            <div class='metric-label'>Under Review</div>
            <div class='metric-val'>{under_review_count}</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class='metric-card metric-green'>
            <div class='metric-label'>Approved</div>
            <div class='metric-val'>{approved_count}</div>
        </div>""", unsafe_allow_html=True)

    # ── 2. Applications List or Polished Empty State ─────────────────────────────
    if apps:
        st.markdown(f"#### Your Marked Applications ({len(apps)})")
        st.markdown("""
        <div class='info-box'>
        <b>Personal Application Tracker:</b> These schemes were marked as applied by you. This records your application intent and tracking details locally; official processing status should be verified through the respective government portals below.
        </div>
        """, unsafe_allow_html=True)

        for app_record in apps:
            sid = app_record.get("scheme_id", "")
            cat = app_record.get("category", "scholarship")
            badge_color = CATEGORY_COLORS.get(cat, "#2563EB")
            cat_label = CATEGORY_LABELS.get(cat, cat.replace("_", " ").title())
            portal_url = app_record.get("portal_url", "")
            marked_time = app_record.get("marked_at", "")

            with st.container(border=True):
                st.markdown(f"""
                <div style='display:flex; justify-content:space-between; align-items:flex-start;'>
                    <div style='flex:1; padding-right:16px;'>
                        <div class='scheme-title'>
                            {app_record.get('name', 'Government Scheme')}
                        </div>
                        <div>
                            <span class='badge' style='background:{badge_color};'>{cat_label}</span>
                            {"<span class='benefit-chip'>Benefit: " + app_record.get('benefit_amount','') + "</span>" if app_record.get('benefit_amount') else ""}
                        </div>
                    </div>
                    <div style='text-align:right;'>
                        <span class='badge' style='background:#059669;'>✓ Marked as Applied</span>
                        <div style='font-size:0.75rem; color:#64748B; margin-top:4px;'>{marked_time}</div>
                    </div>
                </div>
                <div class='scheme-desc'>{app_record.get('description','')[:300]}…</div>
                """, unsafe_allow_html=True)

                col_a, col_b = st.columns([2, 1])
                with col_a:
                    if portal_url:
                        st.link_button("Open Official Portal ↗", portal_url, use_container_width=True)
                    else:
                        st.button("Open Official Portal ↗", disabled=True, use_container_width=True, key=f"portal_link_{sid}")
                with col_b:
                    if st.button("Mark as Not Applied", key=f"unmark_{sid}", use_container_width=True, help="Remove from your applications"):
                        unmark_applied(user_id, sid)
                        st.rerun()
    else:
        with st.container(border=True):
            st.markdown("""
            <div style='padding: 4px 0;'>
                <div style='font-size: 1.15rem; font-weight: 800; color: #0F172A; margin-bottom: 6px;'>
                    No Applications Marked Yet
                </div>
                <div style='color: #475569; font-size: 0.92rem; line-height: 1.6; margin-bottom: 16px;'>
                    When you apply for a scheme or internship, click <b>'Mark as Applied'</b> on any scheme card to save it here for tracking.<br/>
                    You can also verify your active application status directly through official government portals.
                </div>
            </div>
            """, unsafe_allow_html=True)

            col_btn, _ = st.columns([1, 2])
            with col_btn:
                if st.button("Discover Schemes →", type="primary", use_container_width=True, key="btn_discover_from_apps"):
                    st.session_state.page = "Discover"
                    st.rerun()

            st.caption(
                "Note: AVSAR does not claim that an application was officially submitted or verified. This feature only records schemes you have marked as applied."
            )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # ── 3. Official Tracking Dashboards ──────────────────────────────────────────
    st.markdown("#### Official Tracking Dashboards")
    st.markdown(
        "<div style='color: #475569; font-size: 0.88rem; margin-bottom: 14px;'>"
        "Use these primary national portals to verify the official processing status of your submitted applications."
        "</div>",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("""
            <div style='display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;'>
                <div style='font-size: 1.12rem; font-weight: 800; color: #0F172A;'>MyScheme Portal</div>
                <span class='badge' style='background: #0284C7;'>National Aggregator</span>
            </div>
            <div style='color: #475569; font-size: 0.88rem; line-height: 1.5; margin-bottom: 12px;'>
                Central citizen directory providing application status for central ministries and state welfare schemes.
            </div>
            <div style='background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px 14px; margin-bottom: 16px;'>
                <div style='font-size: 0.78rem; font-weight: 700; text-transform: uppercase; color: #64748B; margin-bottom: 8px;'>Verification Steps</div>
                <div style='color: #1E293B; font-size: 0.86rem; line-height: 1.6;'>
                    <b>1.</b> Access official portal at <a href='https://www.myscheme.gov.in' target='_blank' style='color:#2563EB; font-weight:600;'>myscheme.gov.in</a><br/>
                    <b>2.</b> Authenticate using Mobile OTP or DigiLocker<br/>
                    <b>3.</b> Navigate to <b>'Track Applications'</b> on your citizen dashboard<br/>
                    <b>4.</b> Review application reference timeline and stage updates
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.link_button("Open MyScheme Portal ↗", "https://www.myscheme.gov.in", use_container_width=True)

    with col2:
        with st.container(border=True):
            st.markdown("""
            <div style='display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;'>
                <div style='font-size: 1.12rem; font-weight: 800; color: #0F172A;'>National Scholarship Portal</div>
                <span class='badge' style='background: #2563EB;'>NSP Central</span>
            </div>
            <div style='color: #475569; font-size: 0.88rem; line-height: 1.5; margin-bottom: 12px;'>
                Single-window digital platform for Central, UGC/AICTE, and State Government scholarship programs.
            </div>
            <div style='background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px 14px; margin-bottom: 16px;'>
                <div style='font-size: 0.78rem; font-weight: 700; text-transform: uppercase; color: #64748B; margin-bottom: 8px;'>Verification Steps</div>
                <div style='color: #1E293B; font-size: 0.86rem; line-height: 1.6;'>
                    <b>1.</b> Access official portal at <a href='https://scholarships.gov.in' target='_blank' style='color:#2563EB; font-weight:600;'>scholarships.gov.in</a><br/>
                    <b>2.</b> Select <b>'Applicant Corner'</b> and choose your application year<br/>
                    <b>3.</b> Sign in with your Application ID and Password<br/>
                    <b>4.</b> Check status under <b>'Check Your Status'</b> (Institute / State verification)
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.link_button("Open NSP Portal ↗", "https://scholarships.gov.in", use_container_width=True)


# ─── Page: ABOUT ──────────────────────────────────────────────────────────────

def page_about():
    st.markdown("<div class='section-header'>About AVSAR</div>", unsafe_allow_html=True)

    st.markdown("""
    **AVSAR** is an automated student welfare scheme discovery and guidance platform
    designed for the Indian education system. It eliminates information asymmetries by matching eligible
    students with government scholarships, educational loans, and welfare benefits across federal and state levels.
    """)

    st.markdown("### Mission")
    st.markdown("""
    > Enable every eligible student in India to discover, verify, and complete application workflows
    > for every government welfare program to which they are legally entitled.
    """)

    st.markdown("### System Architecture")
    tech = {
        "AI & Intelligence": ["Google Gemini Pro", "LangGraph Agent Workflow", "ChromaDB Vector Store"],
        "Backend Architecture": ["FastAPI", "LangChain Core", "Pydantic v2 Validation"],
        "User Interface": ["Streamlit Enterprise UI", "Responsive CSS Design System"],
        "Automation Infrastructure": ["Playwright Browser Automation", "Headless Portal Driver"],
        "Data Integration": ["National Scholarship Portal", "myscheme.gov.in Aggregator", "Vidya Lakshmi Portal"],
    }
    for category, items in tech.items():
        st.markdown(f"**{category}**")
        tags_html = "".join([f"<span class='tech-tag'>{item}</span>" for item in items])
        st.markdown(tags_html, unsafe_allow_html=True)
        st.markdown("")

    st.markdown("### Official Data Sources")
    sources = [
        ("myscheme.gov.in", "Central Ministry & State Welfare Directory", "https://www.myscheme.gov.in"),
        ("scholarships.gov.in", "National Scholarship Portal (NSP)", "https://scholarships.gov.in"),
        ("vidyalakshmi.co.in", "Vidya Lakshmi Educational Loan Portal", "https://www.vidyalakshmi.co.in"),
        ("ugc.ac.in", "University Grants Commission Research Fellowships", "https://www.ugc.ac.in"),
        ("aicte-india.org", "AICTE Technical Scholarships & Grants", "https://www.aicte-india.org"),
        ("State Portals", "Direct State Welfare Department Repositories", "#"),
    ]
    df_src = pd.DataFrame(sources, columns=["Source", "Description", "URL"])
    st.dataframe(df_src, use_container_width=True, hide_index=True)

    st.markdown("### Supported Scheme Categories")
    cats = list(CATEGORY_LABELS.values())
    cols = st.columns(4)
    for i, cat in enumerate(cats):
        with cols[i % 4]:
            st.markdown(f"- {cat}")

    st.markdown("<hr style='border-color: #CBD5E1; margin: 24px 0;'/>", unsafe_allow_html=True)
    st.markdown(
        "<div style='text-align:center; color:#64748B; font-size:0.85rem;'>"
        "AVSAR · Student Government Scheme Navigator · Open Source"
        "</div>",
        unsafe_allow_html=True,
    )


# ─── Router ───────────────────────────────────────────────────────────────────

page = st.session_state.page

if page == "Home":
    page_home()
elif page == "Discover":
    page_discover()
elif page == "Applications":
    page_applications()
elif page == "About":
    page_about()
