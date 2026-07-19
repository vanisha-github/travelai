import streamlit as st
import requests
import json
import os
import time
import urllib.parse
import re
import plotly.graph_objects as go
from datetime import datetime
import db

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="AI Travel Planner", page_icon="✈️", layout="wide", initial_sidebar_state="expanded")


# ─── BACKEND HELPERS ──────────────────────────────────────────────────────────

def plan_trip_api(trip_data: dict) -> dict:
    try:
        resp = requests.post(f"{BACKEND_URL}/plan-trip", json=trip_data, timeout=600)
        resp.raise_for_status()
        return resp.json()
    except requests.ConnectionError:
        return {"error": "Backend server is not running."}
    except requests.HTTPError as e:
        return {"error": f"Server error: {e.response.status_code}"}
    except requests.Timeout:
        return {"error": "Request timed out."}
    except Exception as e:
        return {"error": str(e)}


# ─── UTILITY HELPERS ──────────────────────────────────────────────────────────

def strip_html(t):
    """Remove ALL HTML/XML tags, fragments, and entities from text. Kills every possible remnant."""
    if not t: return ""
    t = str(t)
    t = re.sub(r"<[^>]*>", "", t)
    t = re.sub(r"</?[a-zA-Z][^>]*>", "", t)
    t = re.sub(r"</?[a-zA-Z]+", "", t)
    t = re.sub(r"<\s*/?\s*\w+\b", "", t)
    t = re.sub(r"<\s*>", "", t)
    t = re.sub(r"[<>]", "", t)
    t = re.sub(r"&[a-zA-Z]+;", " ", t)
    t = re.sub(r"&#?\w+;", " ", t)
    t = re.sub(r"</{1,3}", "", t)
    t = re.sub(r"/{2,}", "", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()

def sanitize_text(t):
    """Full sanitization: strip HTML + remove JSON/code fences + clean for display."""
    if not t: return ""
    t = strip_html(t)
    t = re.sub(r"```json.*?```", "", t, flags=re.DOTALL)
    t = re.sub(r"```\s*.*?```", "", t, flags=re.DOTALL)
    for _ in range(5):
        prev = t
        t = re.sub(r'\{[^{}]{0,500}\}', "", t)
        if t == prev:
            break
    t = re.sub(r'\[[\s\S]{0,300}\]', "", t)
    t = re.sub(r'"[a-zA-Z_]+"\s*:\s*(?:,|\}|null|""|0|\[\])', "", t)
    t = re.sub(r'\{\s*,', "{", t)
    t = re.sub(r',\s*\}', "}", t)
    t = re.sub(r'\{\s*\}', "", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = re.sub(r"[<>]", "", t)
    return t.strip()

def esc(t):
    if not t: return ""
    t = sanitize_text(t)
    return t.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

def safe_url(url):
    if not url: return ""
    url = str(url).strip()
    if not url: return ""
    if '<' in url or '>' in url or '"' in url or 'javascript:' in url.lower():
        print(f"Invalid URL discarded: {url[:120]}")
        return ""
    if not url.lower().startswith(('http://', 'https://')):
        print(f"Invalid URL discarded (not http): {url[:120]}")
        return ""
    return url

def maps_url(name, city=""):
    query = f"{name} {city}".strip() if city else name
    return f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote_plus(query)}"

def weather_icon(c):
    if not c: return "🌤️"
    c = c.lower()
    mapping = [
        ("clear sky", "☀️"), ("clear", "☀️"),
        ("few clouds", "🌤️"), ("partly cloudy", "⛅"), ("partly", "⛅"),
        ("scattered clouds", "⛅"), ("broken clouds", "🌥️"),
        ("overcast clouds", "☁️"), ("overcast", "☁️"),
        ("cloud", "☁️"), ("clouds", "☁️"),
        ("light rain", "🌦️"), ("moderate rain", "🌧️"), ("heavy rain", "🌧️"),
        ("rain", "🌧️"), ("drizzle", "🌦️"), ("shower", "🌦️"),
        ("thunderstorm", "⛈️"), ("thunder", "⛈️"), ("lightning", "⛈️"),
        ("snow", "❄️"), ("light snow", "🌨️"), ("heavy snow", "❄️"),
        ("sleet", "🌨️"), ("freezing rain", "🌨️"),
        ("mist", "🌫️"), ("fog", "🌫️"), ("haze", "🌫️"),
        ("smoke", "🌫️"), ("dust", "💨"), ("sand", "💨"),
        ("wind", "💨"), ("windy", "💨"), ("gale", "💨"),
        ("tornado", "🌪️"), ("hurricane", "🌀"),
        ("tropical storm", "🌀"),
    ]
    for key, icon in mapping:
        if key in c: return icon
    return "🌤️"

def dest_flag(d):
    flags={"france":"🇫🇷","paris":"🇫🇷","japan":"🇯🇵","tokyo":"🇯🇵","italy":"🇮🇹","rome":"🇮🇹",
        "venice":"🇮🇹","spain":"🇪🇸","barcelona":"🇪🇸","united states":"🇺🇸","new york":"🇺🇸","usa":"🇺🇸",
        "united kingdom":"🇬🇧","london":"🇬🇧","uk":"🇬🇧","germany":"🇩🇪","berlin":"🇩🇪","india":"🇮🇳",
        "delhi":"🇮🇳","mumbai":"🇮🇳","thailand":"🇹🇭","bangkok":"🇹🇭","greece":"🇬🇷","athens":"🇬🇷",
        "santorini":"🇬🇷","turkey":"🇹🇷","istanbul":"🇹🇷","dubai":"🇦🇪","uae":"🇦🇪","brazil":"🇧🇷",
        "australia":"🇦🇺","canada":"🇨🇦","switzerland":"🇨🇭","amsterdam":"🇳🇱","netherlands":"🇳🇱",
        "south korea":"🇰🇷","seoul":"🇰🇷","china":"🇨🇳","egypt":"🇪🇬","mexico":"🇲🇽","portugal":"🇵🇹",
        "morocco":"🇲🇦","vietnam":"🇻🇳","bali":"🇮🇩","singapore":"🇸🇬","cuba":"🇨🇺","peru":"🇵🇪",
        "colombia":"🇨🇴","argentina":"🇦🇷","chile":"🇨🇱","new zealand":"🇳🇿","ireland":"🇮🇪",
        "nepal":"🇳🇵","sri lanka":"🇱🇰","philippines":"🇵🇭"}
    dl = d.lower()
    for k, f in flags.items():
        if k in dl: return f
    return "🌍"

def clean_display(t):
    if not t: return ""
    t = sanitize_text(t)
    t = re.sub(r"\s+", " ", t).strip()
    if len(re.sub(r'[^a-zA-Z0-9\u00C0-\u024F]', '', t)) < 2:
        return ""
    return t


# ─── CSS ──────────────────────────────────────────────────────────────────────

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

:root{
--pri:#4F46E5;--pri2:#4338CA;--priL:#818CF8;--priXL:#EEF2FF;--priXX:#F5F7FF;
--bg:#F8FAFC;--card:#FFFFFF;--txt:#0F172A;--txt2:#334155;--txt3:#64748B;--txt4:#94A3B8;
--bdr:#E2E8F0;--bdr2:#CBD5E1;--grn:#059669;--grnL:#ECFDF5;--org:#D97706;--orgL:#FFFBEB;
--red:#DC2626;--redL:#FEF2F2;--blu:#0284C7;--bluL:#F0F9FF;--pnk:#DB2777;--pnkL:#FDF2F8;
--ind:#4F46E5;--indL:#EEF2FF;
}

*{font-family:'Inter',system-ui,-apple-system,sans-serif !important;}
.block-container{padding-top:1.5rem !important;padding-bottom:1rem !important;max-width:1100px !important;}
.stApp{background:var(--bg) !important;}
.stApp>header{background:transparent !important;}
section[data-testid="stSidebar"]{background:#fff !important;border-right:1px solid var(--bdr) !important;}
section[data-testid="stSidebar"]>div{padding-top:1rem !important;}

/* Tabs — clean, minimal */
.stTabs [data-baseweb="tab-list"]{
    gap:2px !important;
    background:var(--bg) !important;
    border:1px solid var(--bdr) !important;
    border-radius:10px !important;
    padding:4px !important;
    box-shadow:none !important;
    overflow-x:auto !important;
    overflow-y:hidden !important;
    scroll-behavior:smooth !important;
    scrollbar-width:none !important;
    -ms-overflow-style:none !important;
    position:relative !important;
}
.stTabs [data-baseweb="tab-list"]::-webkit-scrollbar{display:none !important;}
.stTabs [data-baseweb="tab"]{
    border-radius:8px !important;
    padding:0.5rem 1rem !important;
    font-weight:500 !important;
    font-size:0.8rem !important;
    color:var(--txt3) !important;
    border:1px solid transparent !important;
    background:transparent !important;
    white-space:nowrap !important;
    transition:all 0.2s ease !important;
    position:relative !important;
    min-width:fit-content !important;
}
.stTabs [data-baseweb="tab"]:hover{
    color:var(--txt) !important;
    background:rgba(79,70,229,0.04) !important;
}
.stTabs [aria-selected="true"]{
    background:var(--pri) !important;
    color:#fff !important;
    border-color:transparent !important;
    box-shadow:0 1px 3px rgba(79,70,229,0.2) !important;
    font-weight:600 !important;
}
.stTabs [data-baseweb="tab-highlight"]{display:none !important;}
.stTabs [data-baseweb="tab-border"]{display:none !important;}
.stTabs>div>div>div{
    background:var(--card) !important;
    border:1px solid var(--bdr) !important;
    border-top:none !important;
    border-radius:0 0 12px 12px !important;
    padding:1.8rem !important;
    box-shadow:none !important;
}

/* Buttons */
.stButton>button{border-radius:8px !important;font-weight:500 !important;border:none !important;transition:all 0.2s ease !important;}
.stButton>button[kind="primary"]{
    background:var(--pri) !important;color:#fff !important;
    box-shadow:0 1px 3px rgba(79,70,229,0.2) !important;
}
.stButton>button[kind="primary"]:hover{background:var(--pri2) !important;box-shadow:0 2px 6px rgba(79,70,229,0.3) !important;}
.stButton>button[kind="secondary"]{background:var(--card) !important;color:var(--txt2) !important;border:1px solid var(--bdr) !important;}
.stButton>button[kind="secondary"]:hover{background:var(--bg) !important;border-color:var(--bdr2) !important;}

/* Expanders */
[data-testid="stExpander"]{background:var(--card) !important;border:1px solid var(--bdr) !important;border-radius:10px !important;margin-bottom:0.6rem !important;box-shadow:none !important;transition:all 0.2s ease !important;}
[data-testid="stExpander"] summary{font-weight:600 !important;font-size:0.95rem !important;color:var(--txt) !important;}
[data-testid="stExpander"]:hover{border-color:var(--bdr2) !important;}

/* Progress & Inputs */
.stProgress>div>div>div{background:var(--pri) !important;border-radius:6px !important;}
.stTextInput>div>div>input,.stNumberInput>div>div>input{border-radius:8px !important;border:1px solid var(--bdr) !important;font-size:0.9rem !important;}
.stTextInput>div>div>input:focus,.stNumberInput>div>div>input:focus{border-color:var(--pri) !important;box-shadow:0 0 0 2px rgba(79,70,229,0.1) !important;}
.stMultiSelect>div>div{border-color:var(--bdr) !important;border-radius:8px !important;}
.stRadio>div{gap:0.3rem !important;}

/* Animations — subtle */
@keyframes fadeUp{from{opacity:0;transform:translateY(10px);}to{opacity:1;transform:translateY(0);}}
@keyframes fadeIn{from{opacity:0;}to{opacity:1;}}
@keyframes scaleIn{from{opacity:0;}to{opacity:1;}}
.anim-fade-up{animation:fadeUp 0.4s ease-out both;}
.anim-fade-in{animation:fadeIn 0.35s ease-out both;}
.anim-scale-in{animation:scaleIn 0.35s ease-out both;}
.anim-delay-1{animation-delay:0.05s;}.anim-delay-2{animation-delay:0.1s;}.anim-delay-3{animation-delay:0.15s;}
.anim-delay-4{animation-delay:0.2s;}.anim-delay-5{animation-delay:0.25s;}

/* Score ring */
.score-ring{position:relative;display:inline-flex;align-items:center;justify-content:center;}
.score-ring svg{transform:rotate(-90deg);}
.score-ring .score-val{position:absolute;font-size:1.8rem;font-weight:700;color:#fff;line-height:1;}
.score-ring .score-lbl{position:absolute;font-size:0.55rem;color:rgba(255,255,255,0.6);text-transform:uppercase;letter-spacing:1.5px;margin-top:2.4rem;}

/* Weather hero card — muted professional blue */
.wx-hero{background:linear-gradient(135deg,#0F172A 0%,#1E293B 50%,#0F172A 100%);
border-radius:14px;padding:1.8rem 2rem;color:#fff;position:relative;overflow:hidden;
box-shadow:0 1px 3px rgba(0,0,0,0.1);margin-bottom:1rem;}
.wx-hero::before{content:'';position:absolute;top:-40%;right:-15%;width:50%;height:180%;
background:radial-gradient(circle,rgba(14,165,233,0.08) 0%,transparent 70%);pointer-events:none;}

/* Weather detail cards */
.wx-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:0.6rem;}
.wx-card{background:rgba(255,255,255,0.06);
border:1px solid rgba(255,255,255,0.1);border-radius:10px;
padding:0.9rem 0.5rem;text-align:center;transition:all 0.2s ease;
animation:fadeUp 0.4s ease-out both;}
.wx-card:hover{background:rgba(255,255,255,0.1);}
.wx-card .wx-ic{font-size:1.3rem;line-height:1;margin-bottom:0.25rem;}
.wx-card .wx-val{font-size:0.95rem;font-weight:600;color:#fff;line-height:1.2;}
.wx-card .wx-lbl{font-size:0.6rem;color:rgba(255,255,255,0.5);text-transform:uppercase;letter-spacing:0.8px;margin-top:0.1rem;}

/* Weather extra data row */
.wx-extra{display:grid;grid-template-columns:repeat(3,1fr);gap:0.5rem;margin-top:0.5rem;}
.wx-extra-card{background:rgba(255,255,255,0.04);
border:1px solid rgba(255,255,255,0.08);border-radius:8px;
padding:0.5rem 0.4rem;text-align:center;font-size:0.72rem;color:rgba(255,255,255,0.6);
transition:all 0.2s;animation:fadeUp 0.4s ease-out both;}
.wx-extra-card:hover{background:rgba(255,255,255,0.08);}
.wx-extra-card span{font-weight:600;color:#fff;display:block;font-size:0.8rem;}

/* Weather tips */
.wx-tip{background:rgba(255,255,255,0.05);
border:1px solid rgba(255,255,255,0.08);border-radius:8px;
padding:0.5rem 0.7rem;margin-bottom:0.3rem;font-size:0.78rem;color:rgba(255,255,255,0.75);
display:flex;align-items:center;gap:0.5rem;animation:fadeUp 0.35s ease-out both;}
.wx-tip:hover{background:rgba(255,255,255,0.08);}

/* Tab scroll container */
.tab-scroll-wrap{position:relative;overflow:hidden;}
.tab-scroll-btn{position:absolute;top:50%;transform:translateY(-50%);z-index:10;
width:32px;height:32px;border-radius:8px;border:1px solid var(--bdr);cursor:pointer;
background:var(--card);color:var(--txt3);font-size:0.7rem;
box-shadow:0 1px 3px rgba(0,0,0,0.08);transition:all 0.2s ease;
display:flex;align-items:center;justify-content:center;}
.tab-scroll-btn:hover{background:var(--bg);color:var(--txt);border-color:var(--bdr2);}
.tab-scroll-btn:active{transform:translateY(-50%) scale(0.95);}
.tab-scroll-btn.left{left:6px;}
.tab-scroll-btn.right{right:6px;}
.tab-scroll-btn.hidden{display:none;opacity:0;pointer-events:none;}
.tab-fade-left,.tab-fade-right{position:absolute;top:0;bottom:0;width:40px;z-index:5;
pointer-events:none;transition:opacity 0.3s ease;}
.tab-fade-left{left:40px;background:linear-gradient(to right,var(--card),transparent);opacity:0;}
.tab-fade-right{right:0;background:linear-gradient(to left,var(--card),transparent);opacity:0;}
.tab-fade-left.show,.tab-fade-right.show{opacity:1;}

/* Score ring animation */
@keyframes scoreReveal{from{stroke-dashoffset:var(--circ);}to{stroke-dashoffset:var(--offset);}}
.score-ring circle.score-arc{animation:scoreReveal 1s ease-out forwards;}

/* Condition & feels-like badges */
.wx-badge{display:inline-flex;align-items:center;gap:0.2rem;background:rgba(255,255,255,0.1);
border:1px solid rgba(255,255,255,0.12);padding:0.2rem 0.6rem;
border-radius:6px;font-size:0.75rem;color:rgba(255,255,255,0.85);font-weight:500;}

/* Weather card stagger */
.wx-card:nth-child(1){animation-delay:0s;}
.wx-card:nth-child(2){animation-delay:0.05s;}
.wx-card:nth-child(3){animation-delay:0.1s;}
.wx-card:nth-child(4){animation-delay:0.15s;}
.wx-card:nth-child(5){animation-delay:0.2s;}
.wx-extra-card:nth-child(1){animation-delay:0.25s;}
.wx-extra-card:nth-child(2){animation-delay:0.3s;}
.wx-extra-card:nth-child(3){animation-delay:0.35s;}

.wx-icon-anim{display:inline-block;}

/* Score breakdown */
.score-breakdown{margin-top:0.5rem;}
.score-row{display:flex;align-items:center;gap:0.5rem;margin-bottom:0.35rem;}
.score-bar-track{flex:1;height:4px;background:rgba(255,255,255,0.12);border-radius:2px;overflow:hidden;}
.score-bar-fill{height:100%;border-radius:2px;transition:width 1s ease-out;}
.score-label{font-size:0.68rem;color:rgba(255,255,255,0.6);min-width:100px;}
.score-pts{font-size:0.68rem;color:rgba(255,255,255,0.8);font-weight:600;min-width:36px;text-align:right;}

/* ─── RESPONSIVE: Tablet ─────────────────────────────────────────────── */
@media(max-width:1024px){
    .block-container{max-width:100% !important;}
}

/* ─── RESPONSIVE: Mobile ─────────────────────────────────────────────── */
@media(max-width:768px){
    /* 1. Top padding — prevent Streamlit header overlap */
    .block-container{
        padding-top:4.5rem !important;
        padding-left:0.75rem !important;
        padding-right:0.75rem !important;
        padding-bottom:0.75rem !important;
        max-width:100% !important;
    }
    section[data-testid="stHeader"]{
        background:var(--bg) !important;
    }

    /* 2. Accordion/expander titles — prevent text spilling outside */
    [data-testid="stExpander"]{
        margin-left:0 !important;
        transform:none !important;
        overflow:visible !important;
    }
    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] summary > div,
    [data-testid="stExpander"] summary > div > span,
    [data-testid="stExpander"] summary > div > div,
    [data-testid="stExpander"] summary p{
        transform:none !important;
        margin-left:0 !important;
        padding-left:0 !important;
        overflow:visible !important;
        text-overflow:unset !important;
        white-space:normal !important;
        word-wrap:break-word !important;
        overflow-wrap:break-word !important;
        max-width:100% !important;
    }
    [data-testid="stExpander"] summary{
        padding:0.6rem 1rem !important;
        min-height:44px !important;
    }
    [data-testid="stExpander"] summary svg{
        flex-shrink:0 !important;
        margin-right:0.5rem !important;
    }

    /* 3. Sidebar — accessible via Streamlit hamburger on mobile */
    section[data-testid="stSidebar"]{
        display:block !important;
        z-index:999 !important;
    }
    section[data-testid="stSidebar"] > div{
        padding-top:1.5rem !important;
    }

    /* 4. Hero section — stack vertically */
    .hero-flex{
        flex-direction:column !important;
        align-items:stretch !important;
        gap:0.8rem !important;
    }
    .hero-info{
        min-width:0 !important;
    }
    .hero-info [style*="font-size:2.2rem"]{
        font-size:clamp(1.4rem,4vw,2rem) !important;
        letter-spacing:-0.3px !important;
    }
    .hero-score{
        align-self:center !important;
        width:100% !important;
        box-sizing:border-box !important;
        padding:1rem 1.2rem !important;
    }
    .score-ring-box{
        width:90px !important;
        height:90px !important;
    }
    .score-ring .score-val{font-size:1.4rem !important;}
    .score-ring .score-lbl{font-size:0.5rem !important;margin-top:1.8rem !important;}

    /* 5. Tabs — scrollable with touch-friendly 44px targets */
    .stTabs [data-baseweb="tab-list"]{
        padding:3px !important;
        gap:3px !important;
        -webkit-overflow-scrolling:touch !important;
    }
    .stTabs [data-baseweb="tab"]{
        padding:0.45rem 0.75rem !important;
        font-size:0.72rem !important;
        min-height:44px !important;
    }
    .stTabs>div>div>div{
        padding:1rem !important;
        border-radius:0 0 14px 14px !important;
    }

    /* 6. Cards — prevent horizontal overflow */
    [data-testid="stExpander"],
    [data-testid="stVerticalBlockBorderWrapper"]{
        max-width:100% !important;
        box-sizing:border-box !important;
        overflow:hidden !important;
    }

    /* 7. Hotel/Attraction/Food link buttons — stack vertically on mobile */
    .link-btns{
        display:flex !important;
        flex-direction:column !important;
        gap:0.3rem !important;
    }
    .link-btns a{
        display:block !important;
        text-align:center !important;
        margin:0 !important;
        padding:0.55rem 0.75rem !important;
    }

    /* 8. Day itinerary — fix text wrapping */
    [data-testid="stExpander"] summary span{
        word-wrap:break-word !important;
        overflow-wrap:break-word !important;
    }

    /* 10. Statistics / all Streamlit column blocks — 2 columns on mobile */
    [data-testid="stHorizontalBlock"]{
        grid-template-columns:repeat(2,1fr) !important;
        gap:0.5rem !important;
    }

    /* 11. Images — responsive */
    img{
        max-width:100% !important;
        height:auto !important;
        object-fit:cover !important;
    }

    /* 12. Typography — responsive */
    .hero-info [style*="font-size:2.2rem"]{
        font-size:clamp(1.4rem,4vw,2.2rem) !important;
    }

    /* 13. Touch targets — min-height 44px */
    .stButton>button{
        min-height:44px !important;
        font-size:0.9rem !important;
    }

    /* Weather section */
    .wx-hero{
        padding:1.2rem 1rem !important;
        border-radius:16px !important;
    }
    .wx-hero .wx-icon-anim{
        font-size:3rem !important;
    }
    .wx-hero [style*="font-size:3.5rem"]{
        font-size:clamp(1.8rem,7vw,2.5rem) !important;
    }
    .wx-grid{grid-template-columns:repeat(2,1fr) !important;}
    .wx-extra{grid-template-columns:repeat(2,1fr) !important;}
    .wx-card{padding:0.7rem 0.5rem !important;}
    .wx-card .wx-ic{font-size:1.3rem !important;}
    .wx-card .wx-val{font-size:0.95rem !important;}
    .wx-badge{font-size:0.7rem !important;padding:0.2rem 0.5rem !important;}

    /* Welcome hero */
    [style*="font-size:1.8rem"][style*="font-weight:700"]{
        font-size:clamp(1.3rem,4vw,1.8rem) !important;
    }

    /* Transport columns */
    [style*="text-align:center"][style*="background:#F1F5F9"]{
        padding:0.6rem !important;
    }

    /* Budget status card */
    [style*="font-size:2.2rem"][style*="font-weight:800"]{
        font-size:1.6rem !important;
    }
}

/* ─── RESPONSIVE: Small phones ───────────────────────────────────────── */
@media(max-width:480px){
    .block-container{
        padding-top:4.5rem !important;
        padding-left:0.5rem !important;
        padding-right:0.5rem !important;
    }

    /* Weather — single column */
    .wx-grid{grid-template-columns:1fr !important;}
    .wx-extra{grid-template-columns:1fr !important;}
    .wx-hero{padding:0.8rem 0.6rem !important;}
    .wx-hero .wx-icon-anim{font-size:2.2rem !important;}
    .wx-card{padding:0.5rem 0.3rem !important;}
    .wx-badge{font-size:0.65rem !important;}

    /* Score ring — smaller on tiny screens */
    .score-ring-box{width:72px !important;height:72px !important;}
    .score-ring .score-val{font-size:1.1rem !important;}
    .score-ring .score-lbl{display:none !important;}

    /* Tabs — tighter on small phones */
    .stTabs [data-baseweb="tab"]{
        padding:0.35rem 0.6rem !important;
        font-size:0.68rem !important;
        min-height:44px !important;
    }
    .stTabs>div>div>div{padding:0.7rem !important;}

    /* Buttons — full width on small phones */
    .stButton>button{
        width:100% !important;
        min-height:44px !important;
    }

    /* Score breakdown — tighter labels */
    .score-label{font-size:0.6rem !important;min-width:70px !important;}
    .score-pts{font-size:0.6rem !important;min-width:28px !important;}

    /* Hero score card */
    .hero-score{padding:0.8rem !important;}
}

/* Card hover — subtle professional */
.hl:hover{box-shadow:0 4px 12px rgba(0,0,0,0.06)!important;border-color:var(--bdr2)!important}
.hl-sm:hover{box-shadow:0 2px 8px rgba(0,0,0,0.05)!important;border-color:var(--bdr2)!important}
.hl-xs:hover{box-shadow:0 2px 6px rgba(0,0,0,0.04)!important}
.hl-pk:hover{border-color:#F9A8D4!important}
.hl-or:hover{border-color:#FCD34D!important}
.hl-subtle:hover{box-shadow:0 2px 8px rgba(0,0,0,0.04)!important}
.lk:hover{background:var(--bg)!important}
.lk-f:hover{opacity:0.85!important}
</style>""", unsafe_allow_html=True)

st.markdown("""<div id="mobile-menu-btn" title="Open sidebar menu"
onclick="(function(){var b=document.querySelector('[data-testid=stSidebarCollapseButton]');if(b){b.click();return;}var b2=document.querySelector('[data-testid=collapsedControl] button');if(b2){b2.click();return;}var s=document.querySelector('section[data-testid=stSidebar]');if(s){s.style.transform=s.style.transform==='translateX(0px)'?'translateX(-100%)':'translateX(0px)';}})()">
<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
</div>
<style>
@media(min-width:769px){#mobile-menu-btn{display:none !important;}}
@media(max-width:768px){
#mobile-menu-btn{
    display:flex !important;position:fixed !important;top:0.65rem !important;left:0.65rem !important;
    z-index:1002 !important;width:40px !important;height:40px !important;
    background:var(--card) !important;color:var(--txt2) !important;
    border:1px solid var(--bdr) !important;border-radius:10px !important;
    align-items:center !important;justify-content:center !important;
    cursor:pointer !important;box-shadow:0 1px 3px rgba(0,0,0,0.08) !important;
    transition:all 0.2s ease !important;
    -webkit-tap-highlight-color:transparent !important;
}
#mobile-menu-btn:active{background:var(--bg) !important;}
}
</style>""", unsafe_allow_html=True)


# ─── WELCOME SCREEN ───────────────────────────────────────────────────────────

def render_welcome():
    st.markdown("""<div class="anim-fade-up" style="background:#0F172A;
    border-radius:14px;padding:3rem 2.5rem;color:#fff;position:relative;overflow:hidden;margin-bottom:1.5rem;
    box-shadow:0 1px 3px rgba(0,0,0,0.1);">
    <div style="position:relative;z-index:1;text-align:center;">
    <div style="font-size:1.8rem;font-weight:700;letter-spacing:-0.5px;margin-bottom:0.4rem;">AI Travel Planner</div>
    <div style="font-size:0.95rem;color:#94A3B8;max-width:420px;margin:0 auto;">Plan data-driven trips with real weather, curated hotels, and smart budgets.</div>
    </div></div>""", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)

    cols = st.columns([1, 2, 1])
    with cols[1]:
        st.markdown("""<div class="anim-scale-in" style="background:#fff;border:1px solid #E2E8F0;border-radius:12px;
        padding:2rem 1.5rem;text-align:center;box-shadow:none;">
        <div style="font-size:0.95rem;font-weight:600;color:#0F172A;margin-bottom:0.25rem;">Enter Your Name</div>
        <div style="font-size:0.82rem;color:#64748B;margin-bottom:1rem;">To personalize your travel experience</div>
        </div>""", unsafe_allow_html=True)

        name = st.text_input("Your Name", placeholder="e.g. Alex", label_visibility="collapsed")
        st.markdown("<div style='margin-top:0.2rem;'></div>", unsafe_allow_html=True)

        if st.button("Start Planning", type="primary", width="stretch", key="start_btn"):
            if name and name.strip():
                st.session_state["user_name"] = name.strip()
                st.rerun()
            else:
                st.error("Please enter your name to continue.")

    st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)

    feat_cols = st.columns(3)
    feats = [
        ("Multi-Agent AI", "5 specialized agents plan your trip collaboratively"),
        ("Live Data", "Real weather, hotels, and attraction information"),
        ("PDF Export", "Download a formatted travel brochure instantly"),
    ]
    for i, (title, desc) in enumerate(feats):
        with feat_cols[i]:
            st.markdown(f"""<div class="anim-fade-up anim-delay-{i+1}" style="background:#fff;border:1px solid #E2E8F0;border-radius:10px;
            padding:1.2rem;text-align:center;box-shadow:none;">
            <div style="font-weight:600;color:#0F172A;font-size:0.9rem;margin-bottom:0.2rem;">{title}</div>
            <div style="font-size:0.78rem;color:#64748B;line-height:1.4;">{desc}</div>
            </div>""", unsafe_allow_html=True)


# ─── LANDING PAGE ─────────────────────────────────────────────────────────────

def render_landing():
    user_name = st.session_state.get("user_name", "Traveler")
    st.markdown(f"""<div class="anim-fade-up" style="background:#fff;
    border-radius:12px;padding:1.2rem 1.5rem;margin-bottom:1.5rem;border:1px solid #E2E8F0;">
    <div style="display:flex;align-items:center;gap:0.8rem;">
    <div style="width:36px;height:36px;border-radius:8px;background:#EEF2FF;
    display:inline-flex;align-items:center;justify-content:center;font-size:0.9rem;
    color:#4F46E5;font-weight:600;">{esc(user_name[0].upper())}</div>
    <div>
    <div style="font-size:1rem;font-weight:600;color:#0F172A;">Welcome, {esc(user_name)}</div>
    <div style="font-size:0.82rem;color:#64748B;margin-top:0.05rem;">Ready to plan your next trip?</div>
    </div></div></div>""", unsafe_allow_html=True)

    # Hero
    st.markdown("""<div class="anim-fade-up" style="background:#0F172A;
    border-radius:14px;padding:3rem 2.5rem;color:#fff;position:relative;overflow:hidden;margin-bottom:2rem;
    box-shadow:0 1px 3px rgba(0,0,0,0.1);">
    <div style="position:relative;z-index:1;text-align:center;">
    <div style="font-size:1.8rem;font-weight:700;letter-spacing:-0.5px;margin-bottom:0.4rem;">
    AI Travel Planner</div>
    <div style="font-size:0.95rem;color:#94A3B8;max-width:520px;margin:0 auto 0.3rem;">
    Your personal AI travel assistant. Plan trips with weather forecasts, hotel picks, attractions, and budget breakdowns.</div>
    <div style="font-size:0.82rem;color:#64748B;margin-bottom:1.5rem;">Fill in the sidebar and click <b style="color:#CBD5E1;">Generate Itinerary</b> to start.</div>
    <div style="display:flex;justify-content:center;gap:2.5rem;flex-wrap:wrap;">
    <div style="text-align:center;"><div style="font-size:1.5rem;font-weight:700;">5</div><div style="font-size:0.65rem;color:#64748B;text-transform:uppercase;letter-spacing:1px;">AI Agents</div></div>
    <div style="text-align:center;"><div style="font-size:1.5rem;font-weight:700;">12</div><div style="font-size:0.65rem;color:#64748B;text-transform:uppercase;letter-spacing:1px;">Trip Sections</div></div>
    <div style="text-align:center;"><div style="font-size:1.5rem;font-weight:700;">Live</div><div style="font-size:0.65rem;color:#64748B;text-transform:uppercase;letter-spacing:1px;">Weather Data</div></div>
    <div style="text-align:center;"><div style="font-size:1.5rem;font-weight:700;">PDF</div><div style="font-size:0.65rem;color:#64748B;text-transform:uppercase;letter-spacing:1px;">Export</div></div>
    </div>
    </div></div>""", unsafe_allow_html=True)

    # Features
    st.markdown('<div style="font-size:0.8rem;font-weight:600;color:#64748B;text-transform:uppercase;letter-spacing:1px;margin-bottom:0.6rem;text-align:center;">Capabilities</div>', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center;color:#94A3B8;font-size:0.85rem;margin-bottom:1rem;">Everything you need for trip planning</div>', unsafe_allow_html=True)

    features = [
        ("Itinerary","Multi-agent system generates personalized day-by-day plans","#4F46E5"),
        ("Weather","Real-time forecasts with packing advice and conditions","#0284C7"),
        ("Hotels","Curated picks with ratings, prices, and booking links","#4F46E5"),
        ("Attractions","Top sights with hours, fees, and Google Maps links","#DB2777"),
        ("Budget","Detailed cost breakdown with money-saving tips","#059669"),
        ("Packing","Smart checklist organized by category","#D97706"),
    ]

    cols = st.columns(3)
    for i, (title, desc, color) in enumerate(features):
        with cols[i % 3]:
            st.markdown(f"""<div class="anim-fade-up anim-delay-{i+1} hl" style="background:#fff;border:1px solid #E2E8F0;border-radius:10px;
            padding:1.3rem;box-shadow:none;transition:all 0.2s;cursor:default;height:100%;">
            <div style="width:6px;height:28px;border-radius:3px;background:{color};display:inline-block;margin-bottom:0.6rem;"></div>
            <div style="font-size:0.92rem;font-weight:600;color:#0F172A;margin-bottom:0.2rem;">{title}</div>
            <div style="font-size:0.78rem;color:#64748B;line-height:1.5;">{desc}</div>
            </div>""", unsafe_allow_html=True)

    # How It Works
    st.markdown("<div style='margin-top:2rem;'></div>", unsafe_allow_html=True)
    st.markdown('<div style="font-size:0.8rem;font-weight:600;color:#64748B;text-transform:uppercase;letter-spacing:1px;margin-bottom:0.6rem;text-align:center;">Process</div>', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center;color:#94A3B8;font-size:0.85rem;margin-bottom:1rem;">Three steps to your trip</div>', unsafe_allow_html=True)

    steps = [
        ("1","Configure","Enter your destination, budget, and interests in the sidebar."),
        ("2","Generate","5 AI agents research and plan your complete itinerary."),
        ("3","Export","Review, save, or download your trip as a PDF brochure."),
    ]
    scols = st.columns(3)
    for i, (num, title, desc) in enumerate(steps):
        with scols[i]:
            st.markdown(f"""<div class="anim-fade-up anim-delay-{i+1}" style="background:#fff;border:1px solid #E2E8F0;border-radius:10px;
            padding:1.4rem 1.2rem;text-align:center;box-shadow:none;">
            <div style="width:32px;height:32px;border-radius:8px;background:#EEF2FF;color:#4F46E5;
            display:inline-flex;align-items:center;justify-content:center;font-size:0.85rem;font-weight:700;margin-bottom:0.6rem;">{num}</div>
            <div style="font-size:0.95rem;font-weight:600;color:#0F172A;margin-bottom:0.2rem;">{title}</div>
            <div style="font-size:0.78rem;color:#64748B;line-height:1.5;">{desc}</div>
            </div>""", unsafe_allow_html=True)

    # Popular Destinations
    st.markdown("<div style='margin-top:2rem;'></div>", unsafe_allow_html=True)
    st.markdown('<div style="font-size:0.8rem;font-weight:600;color:#64748B;text-transform:uppercase;letter-spacing:1px;margin-bottom:0.6rem;text-align:center;">Trending</div>', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center;color:#94A3B8;font-size:0.85rem;margin-bottom:1rem;">Popular destinations to explore</div>', unsafe_allow_html=True)

    popular = [
        ("Paris","$800–3K","France"),
        ("Tokyo","$1.2K–4K","Japan"),
        ("Rome","$700–2.5K","Italy"),
        ("Bangkok","$400–1.5K","Thailand"),
        ("London","$1K–3.5K","UK"),
        ("Barcelona","$700–2.8K","Spain"),
    ]

    pcols = st.columns(6)
    for i, (name, price, country) in enumerate(popular):
        with pcols[i]:
            st.markdown(f"""<div class="anim-scale-in anim-delay-{i+1} hl-sm" style="background:#fff;border:1px solid #E2E8F0;border-radius:10px;
            padding:1rem 0.7rem;text-align:center;box-shadow:none;transition:all 0.2s;cursor:default;">
            <div style="font-weight:600;color:#0F172A;font-size:0.85rem;">{name}</div>
            <div style="font-size:0.68rem;color:#94A3B8;margin:0.15rem 0;">{country}</div>
            <div style="font-size:0.7rem;color:#4F46E5;font-weight:500;margin-top:0.15rem;">{price}</div>
            </div>""", unsafe_allow_html=True)

    # Testimonials
    st.markdown("<div style='margin-top:2rem;'></div>", unsafe_allow_html=True)
    st.markdown('<div style="font-size:0.8rem;font-weight:600;color:#64748B;text-transform:uppercase;letter-spacing:1px;margin-bottom:0.6rem;text-align:center;">Feedback</div>', unsafe_allow_html=True)

    testimonials = [
        ("\"Planned my entire Japan trip in 2 minutes. Hotel recommendations were spot-on.\"","— Sarah M."),
        ("\"The budget breakdown saved me hundreds. I knew exactly where every dollar went.\"","— James K."),
        ("\"The PDF export is gorgeous and so practical. Best travel tool I've used.\"","— Priya R."),
    ]
    tcols = st.columns(3)
    for i, (quote, author) in enumerate(testimonials):
        with tcols[i]:
            st.markdown(f"""<div class="anim-fade-up anim-delay-{i+1}" style="background:#fff;border:1px solid #E2E8F0;border-radius:10px;
            padding:1.2rem;box-shadow:none;">
            <div style="color:#334155;font-size:0.82rem;line-height:1.6;font-style:italic;margin-bottom:0.5rem;">{quote}</div>
            <div style="color:#4F46E5;font-weight:600;font-size:0.78rem;">{author}</div>
            </div>""", unsafe_allow_html=True)

    # Saved Trips
    saved = load_saved_trips()
    if saved:
        st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:0.8rem;font-weight:600;color:#64748B;text-transform:uppercase;letter-spacing:1px;margin-bottom:0.6rem;">Recent Trips ({len(saved)})</div>', unsafe_allow_html=True)
        scols = st.columns(min(len(saved), 4))
        for i, trip in enumerate(saved[:4]):
            with scols[i]:
                dest = trip.get("request",{}).get("destination","?")
                days = trip.get("request",{}).get("num_days","?")
                created = trip.get("created_at","")[:10]
                flag = dest_flag(dest)
                trip_id = trip.get("id","")
                st.markdown(f"""<div class="hl-subtle" style="background:#fff;border:1px solid #E2E8F0;border-radius:10px;
                padding:0.9rem;box-shadow:none;transition:all 0.2s;">
                <div style="font-weight:600;color:#0F172A;font-size:0.85rem;">{flag} {esc(dest)}</div>
                <div style="font-size:0.7rem;color:#94A3B8;margin-top:0.15rem;">{days} days · {created}</div>
                </div>""", unsafe_allow_html=True)
                bc1, bc2 = st.columns(2)
                with bc1:
                    if st.button("👁️ View", key=f"lv_{trip_id}", width="stretch"):
                        st.session_state.itinerary = trip.get("itinerary",{})
                        st.session_state.trip_request = trip.get("request",{})
                with bc2:
                    if st.button("🗑️ Delete", key=f"ld_{trip_id}", width="stretch"):
                        delete_saved_trip(trip_id)
                        st.rerun()


# ─── SIDEBAR ──────────────────────────────────────────────────────────────────

def render_sidebar():
    with st.sidebar:
        user_name = st.session_state.get("user_name", "")
        st.markdown("""<div style="text-align:center;padding:0.3rem 0 1.2rem 0;">
<div style="width:50px;height:50px;border-radius:14px;background:linear-gradient(135deg,#4F46E5,#4F46E5);
display:inline-flex;align-items:center;justify-content:center;font-size:1.4rem;box-shadow:0 4px 14px rgba(124,58,237,0.3);">✈️</div>
<div style="font-size:1.15rem;font-weight:800;color:#0F172A;margin-top:0.5rem;">AI Travel Planner</div>
</div>""", unsafe_allow_html=True)

        if user_name:
            st.markdown(f'<div style="text-align:center;background:linear-gradient(135deg,#F8FAFC,#F1F5F9);border:1.5px solid #E2E8F0;border-radius:12px;padding:0.6rem;margin-bottom:1rem;font-weight:600;color:#4F46E5;font-size:0.9rem;">👋 Welcome, {esc(user_name)}!</div>', unsafe_allow_html=True)

        st.markdown('<div style="background:#fff;border:1.5px solid #F1F5F9;border-radius:14px;padding:1.1rem;margin-bottom:0.7rem;">', unsafe_allow_html=True)
        st.markdown('<div style="font-weight:700;color:#0F172A;margin-bottom:0.5rem;">📍 Trip Details</div>', unsafe_allow_html=True)
        source_city = st.text_input("From", placeholder="e.g. New York")
        destination = st.text_input("To", placeholder="e.g. Paris, France")
        c1,c2 = st.columns(2)
        with c1: num_days = st.number_input("Days",1,30,5,1)
        with c2: num_travellers = st.number_input("Travelers",1,20,2,1)
        budget = st.number_input("Budget (USD)",100,100000,3000,100)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div style="background:#fff;border:1.5px solid #F1F5F9;border-radius:14px;padding:1.1rem;margin-bottom:0.7rem;">', unsafe_allow_html=True)
        st.markdown('<div style="font-weight:700;color:#0F172A;margin-bottom:0.5rem;">🎯 Interests</div>', unsafe_allow_html=True)
        interests = st.multiselect("Interests",["nature","adventure","food","history","shopping","beach"],default=["food","history"],label_visibility="collapsed")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div style="background:#fff;border:1.5px solid #F1F5F9;border-radius:14px;padding:1.1rem;margin-bottom:1rem;">', unsafe_allow_html=True)
        st.markdown('<div style="font-weight:700;color:#0F172A;margin-bottom:0.5rem;">🏨 Hotel Preference</div>', unsafe_allow_html=True)
        hotel_pref = st.radio("Tier",["budget","standard","luxury"],index=1,horizontal=True,label_visibility="collapsed")
        st.markdown('</div>', unsafe_allow_html=True)

        st.button("✨ Generate Itinerary",type="primary",width="stretch",key="gen_btn")
        plan_clicked = st.session_state.get("gen_btn", False)

        st.markdown("---")
        saved = load_saved_trips()
        if saved:
            with st.expander(f"📁 My Saved Trips ({len(saved)})", expanded=False):
                for trip in saved[:10]:
                    dest = trip.get("request",{}).get("destination","?")
                    days = trip.get("request",{}).get("num_days","?")
                    created = trip.get("created_at","")[:10]
                    trip_id = trip.get("id","")
                    st.markdown(f'<div style="font-size:0.82rem;font-weight:600;color:#0F172A;">📍 {esc(dest)} · {days}d · {created}</div>', unsafe_allow_html=True)
                    bc1,bc2,bc3 = st.columns(3)
                    with bc1:
                        if st.button("👁️",key=f"v_{trip_id}",help="View trip"):
                            st.session_state.itinerary = trip.get("itinerary",{})
                            st.session_state.trip_request = trip.get("request",{})
                    with bc2:
                        if st.button("📄",key=f"p_{trip_id}",help="Download PDF"):
                            pdf = export_pdf(trip.get("itinerary",{}), trip.get("request",{}))
                            if pdf:
                                with open(pdf,"rb") as f:
                                    st.download_button("⬇️",data=f.read(),file_name=f"{dest}_trip.pdf",mime="application/pdf",key=f"dl_{trip_id}")
                    with bc3:
                        if st.button("🗑️",key=f"d_{trip_id}",help="Delete"):
                            delete_saved_trip(trip_id)
                            st.rerun()
                    st.markdown('<div style="border-bottom:1px solid #F3F4F6;margin:0.4rem 0;"></div>', unsafe_allow_html=True)

        st.markdown("---")
        if st.button("🔄 Change User", width="stretch", type="secondary"):
            if "user_name" in st.session_state:
                del st.session_state["user_name"]
            for k in ["itinerary", "trip_request"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

    return source_city, destination, num_days, budget, num_travellers, interests, hotel_pref, plan_clicked


# ─── SCORE RING SVG ──────────────────────────────────────────────────────────

def score_ring_html(score, size=120, stroke=10):
    import math
    r = (size - stroke) / 2
    c = 2 * math.pi * r
    pct = min(score, 100) / 100
    offset = c * (1 - pct)
    if score >= 85: color = "#22C55E"
    elif score >= 70: color = "#A3E635"
    elif score >= 55: color = "#F59E0B"
    else: color = "#EF4444"
    return f"""<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" class="score-ring">
    <circle cx="{size//2}" cy="{size//2}" r="{r}" fill="none" stroke="rgba(255,255,255,0.15)" stroke-width="{stroke}"/>
    <circle class="score-arc" cx="{size//2}" cy="{size//2}" r="{r}" fill="none" stroke="{color}" stroke-width="{stroke}"
    stroke-dasharray="{c}" stroke-dashoffset="{c}" stroke-linecap="round"
    style="--circ:{c};--offset:{offset};transform:rotate(-90deg);transform-origin:center;"/>
    </svg>"""


# ─── HERO + METRICS ───────────────────────────────────────────────────────────

def render_hero(itin, req):
    dest=req.get("destination",""); src=req.get("source_city","")
    days=req.get("num_days",0); travelers=req.get("num_travellers",0)
    budget=req.get("budget",0); interests=req.get("interests",[])
    score=itin.get("trip_score",85); flag=dest_flag(dest)
    reasons=itin.get("score_reasons",[])
    w=itin.get("weather_summary",{}); temp=w.get("temperature",""); cond=w.get("condition","")
    wi=weather_icon(cond) if cond else ""
    wbadge = f'{wi} {temp}°C {cond}' if temp else ""

    badges = ''.join(f'<span style="display:inline-flex;align-items:center;gap:0.3rem;background:rgba(255,255,255,0.18);backdrop-filter:blur(8px);border:1px solid rgba(255,255,255,0.2);padding:0.3rem 0.85rem;border-radius:50px;font-size:0.82rem;color:#fff;font-weight:500;">{b}</span>' for b in [
        f'💰 ${budget:,.0f}', f'📅 {days}D', f'👥 {travelers}P',
        *[f'🎯 {i.title()}' for i in interests[:4]],
        f'🌤️ {wbadge}' if wbadge else None,
        f'{"💰" if req.get("hotel_preference")=="budget" else "🏨" if req.get("hotel_preference")=="standard" else "👑"} {req.get("hotel_preference","standard").title()}'
    ] if b)

    # Score reasons tooltip
    reasons_html = ""
    if reasons:
        items = ''.join(f'<span style="display:inline-flex;align-items:center;gap:0.25rem;font-size:0.72rem;color:rgba(255,255,255,0.75);"><span style="width:6px;height:6px;border-radius:50%;background:{"#86EFAC" if r.get("type")=="good" else "#FDE68A" if r.get("type")=="ok" else "#FCA5A5"};display:inline-block;"></span>{esc(r.get("text",""))}</span>' for r in reasons[:6])
        reasons_html = f'<div style="display:flex;flex-wrap:wrap;gap:0.4rem 0.8rem;margin-top:0.6rem;justify-content:flex-end;">{items}</div>'

    ring_svg = score_ring_html(score)

    breakdown_html = ""
    if reasons:
        bar_colors = {"good": "#22C55E", "ok": "#F59E0B", "warn": "#EF4444"}
        rows = ""
        for r in reasons[:8]:
            txt = esc(r.get("text", ""))
            tp = r.get("type", "ok")
            bc = bar_colors.get(tp, "#F59E0B")
            pct_val = {"good": 90, "ok": 60, "warn": 30}.get(tp, 50)
            rows += f'''<div class="score-row">
            <div class="score-label">{txt}</div>
            <div class="score-bar-track"><div class="score-bar-fill" style="width:{pct_val}%;background:{bc};"></div></div>
            </div>'''
        breakdown_html = f'''<div class="score-breakdown">
        <div style="font-size:0.68rem;color:rgba(255,255,255,0.5);text-transform:uppercase;letter-spacing:1px;margin-bottom:0.5rem;">Score Breakdown</div>
        {rows}
        </div>'''

    st.markdown(f"""<div class="anim-fade-up" style="background:#0F172A;
    border-radius:14px;padding:1.8rem 2rem;color:#fff;position:relative;overflow:hidden;margin-bottom:1.2rem;
    box-shadow:0 1px 3px rgba(0,0,0,0.1);">
    <div class="hero-flex" style="position:relative;z-index:1;display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:1rem;">
    <div class="hero-info" style="flex:1;min-width:300px;">
    <div style="font-size:2.2rem;font-weight:700;letter-spacing:-0.5px;">{flag} {esc(dest)}</div>
    <div style="font-size:1rem;color:rgba(255,255,255,0.82);margin:0.3rem 0 1rem 0;">{esc(src)} → {esc(dest)} · {days} days · {travelers} traveler{"s" if travelers!=1 else ""}</div>
    <div style="display:flex;flex-wrap:wrap;gap:0.45rem;">{badges}</div>
    </div>
    <div class="hero-score" style="text-align:center;background:rgba(255,255,255,0.12);backdrop-filter:blur(14px);
    border:1.5px solid rgba(255,255,255,0.2);border-radius:20px;padding:1.2rem 1.8rem;">
    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;">
    <div class="score-ring-box" style="position:relative;width:120px;height:120px;">
    {ring_svg}
    <div style="position:absolute;top:0;left:0;width:100%;height:100%;display:flex;align-items:center;justify-content:center;font-size:2rem;font-weight:800;color:#fff;line-height:1;">{score}</div>
    </div>
    <div style="margin-top:0.5rem;font-size:0.65rem;color:rgba(255,255,255,0.65);text-transform:uppercase;letter-spacing:2px;">Trip Score</div>
    </div>
    {breakdown_html}
    {reasons_html}
    </div></div></div>""", unsafe_allow_html=True)

def render_metrics(itin, req):
    b=itin.get("budget",{}); w=itin.get("weather_summary",{})
    h=itin.get("recommended_hotels",[]); a=itin.get("attractions",[]); r=itin.get("restaurants",[])
    items=[
        ("💰","${:,.0f}".format(b.get("total",0)),"Total Cost"),
        ("🏨",str(len(h)),"Hotels"),("🎯",str(len(a)),"Attractions"),
        ("🍽️",str(len(r)),"Restaurants"),
        ("🌡️","{}°C".format(w.get("temperature",0)),"Weather"),
        ("📅","{}D/{}P".format(req.get("num_days",0),req.get("num_travellers",0)),"Trip"),
    ]
    cols=st.columns(6)
    for col,(ic,val,lbl) in zip(cols,items):
        with col:
            st.markdown(f"""<div class="anim-scale-in hl-xs" style="background:#fff;border:1.5px solid #F1F5F9;border-radius:14px;
            padding:0.9rem 0.5rem;text-align:center;box-shadow:0 1px 4px rgba(124,58,237,0.05);
            transition:all 0.3s;">
            <div style="font-size:1.3rem;">{ic}</div>
            <div style="font-size:1.15rem;font-weight:700;color:#0F172A;">{val}</div>
            <div style="font-size:0.65rem;color:#94A3B8;text-transform:uppercase;letter-spacing:0.8px;margin-top:0.1rem;">{lbl}</div>
            </div>""", unsafe_allow_html=True)


# ─── SECTION HEADER HELPER ────────────────────────────────────────────────────

def section_header(title, emoji="", color="#4F46E5", bg="#EEF2FF", border="#E2E8F0"):
    st.markdown(f"""<div style="font-size:0.95rem;font-weight:600;color:#0F172A;
    margin:0.5rem 0 0.8rem 0;padding-bottom:0.4rem;border-bottom:1px solid #E2E8F0;
    display:flex;align-items:center;gap:0.5rem;">
    <span style="width:4px;height:18px;border-radius:2px;background:{color};display:inline-block;"></span>
    {title}</div>""", unsafe_allow_html=True)


# ─── WEATHER SECTION ──────────────────────────────────────────────────────────

def render_weather(w):
    if not w: return
    icon = weather_icon(w.get("condition",""))
    temp = w.get("temperature",0)
    cond = w.get("condition","N/A")
    desc = w.get("description","")
    feels = w.get("feels_like",0)
    hum = w.get("humidity",0)
    wind = w.get("wind_speed",0)
    rain = w.get("rain_chance")
    sr = w.get("sunrise","")
    ss = w.get("sunset","")
    pressure = w.get("pressure")
    visibility = w.get("visibility")
    clouds = w.get("cloud_pct") or w.get("clouds")

    rain_txt = f"{rain}%" if rain is not None else "N/A"
    hum_txt = f"{hum}%" if hum else "N/A"
    wind_txt = f"{wind} m/s" if wind else "N/A"
    sr_txt = sr or "N/A"
    ss_txt = ss or "N/A"

    vis_km = f"{round(visibility/1000, 1)} km" if visibility else "N/A"
    pres_txt = f"{pressure} hPa" if pressure else "N/A"
    cloud_txt = f"{clouds}%" if clouds is not None else "N/A"

    st.markdown(f"""<div class="anim-fade-up wx-hero">
    <div style="position:relative;z-index:1;display:flex;align-items:center;gap:2rem;flex-wrap:wrap;">
    <div class="wx-icon-anim" style="font-size:5rem;line-height:1;text-shadow:0 4px 20px rgba(0,0,0,0.15);">{icon}</div>
    <div style="flex:1;min-width:200px;">
    <div style="font-size:3.5rem;font-weight:700;line-height:1;color:#fff;">
    {temp}°C</div>
    <div style="margin-top:0.5rem;display:flex;flex-wrap:wrap;gap:0.4rem;">
    <span class="wx-badge">{icon} {esc(cond)}</span>
    <span class="wx-badge">Feels like {feels}°C</span>
    </div>
    {'<div style="color:rgba(255,255,255,0.75);font-size:0.88rem;margin-top:0.4rem;">'+esc(desc)+'</div>' if desc else ''}
    </div>
    </div>
    <div class="wx-grid" style="margin-top:1.2rem;">
    <div class="wx-card"><div class="wx-ic">💧</div><div class="wx-val">{hum_txt}</div><div class="wx-lbl">Humidity</div></div>
    <div class="wx-card"><div class="wx-ic">💨</div><div class="wx-val">{wind_txt}</div><div class="wx-lbl">Wind</div></div>
    <div class="wx-card"><div class="wx-ic">🌧️</div><div class="wx-val">{rain_txt}</div><div class="wx-lbl">Rain</div></div>
    <div class="wx-card"><div class="wx-ic">🌅</div><div class="wx-val">{sr_txt}</div><div class="wx-lbl">Sunrise</div></div>
    <div class="wx-card"><div class="wx-ic">🌇</div><div class="wx-val">{ss_txt}</div><div class="wx-lbl">Sunset</div></div>
    </div>
    <div class="wx-extra">
    <div class="wx-extra-card">🌡️ Pressure<span>{pres_txt}</span></div>
    <div class="wx-extra-card">👁️ Visibility<span>{vis_km}</span></div>
    <div class="wx-extra-card">☁️ Cloud Cover<span>{cloud_txt}</span></div>
    </div>
    </div>""", unsafe_allow_html=True)

    tips = _dynamic_weather_tips(temp, feels, rain, wind, hum, cond)
    if tips:
        tips_html = ''.join(f'<div class="wx-tip"><span>{t[0]}</span> {t[1]}</div>' for t in tips)
        st.markdown(f"""<div style="margin-top:0.8rem;background:linear-gradient(135deg,#0EA5E9,#0284C7);
        border-radius:16px;padding:1.2rem 1.4rem;">
        <div style="font-weight:700;color:#fff;font-size:0.9rem;margin-bottom:0.6rem;">💡 Weather Tips</div>
        {tips_html}
        </div>""", unsafe_allow_html=True)


def _dynamic_weather_tips(temp, feels, rain, wind, hum, cond):
    """Generate dynamic weather tips based on actual conditions."""
    tips = []
    if temp is not None and temp > 0:
        if feels and feels >= 35:
            tips.append(("🔥", "Extreme heat — stay hydrated, avoid midday sun"))
        elif feels and feels >= 30:
            tips.append(("☀️", "Very hot — wear sunscreen, carry water"))
        elif feels and feels <= 5:
            tips.append(("🥶", "Very cold — layer up, bring thermal wear"))
        elif feels and feels <= 10:
            tips.append(("🧤", "Cool weather — bring a jacket and gloves"))
        elif 18 <= temp <= 26:
            tips.append(("👌", "Pleasant temperature — great weather for outdoor activities"))

    if rain is not None:
        if rain >= 70:
            tips.append(("☂️", "High rain probability — bring an umbrella"))
        elif rain >= 40:
            tips.append(("🌦️", "Moderate rain chance — pack a light rain jacket"))
        elif rain >= 15:
            tips.append(("☁️", "Some rain possible — consider carrying an umbrella"))
    else:
        tips.append(("📊", "Rain forecast unavailable — check before going out"))

    if wind is not None:
        if wind >= 15:
            tips.append(("💨", "Strong winds — secure loose items, windbreaker recommended"))
        elif wind >= 10:
            tips.append(("🌬️", "Moderate winds — a light jacket will help"))

    if hum is not None:
        if hum >= 80:
            tips.append(("💦", "High humidity — expect it to feel warmer than the actual temperature"))
        elif hum <= 30:
            tips.append(("🏜️", "Low humidity — keep moisturized and drink plenty of water"))

    cond_l = (cond or "").lower()
    if "snow" in cond_l:
        tips.append(("❄️", "Snow expected — wear insulated boots and thermal layers"))
    if "thunder" in cond_l or "storm" in cond_l:
        tips.append(("⛈️", "Thunderstorm warning — avoid outdoor activities, seek shelter"))
    if "fog" in cond_l or "mist" in cond_l or "haze" in cond_l:
        tips.append(("🌫️", "Low visibility — drive carefully, use fog lights"))

    return tips[:6]


# ─── HOTELS SECTION ───────────────────────────────────────────────────────────

def render_hotels(hotels, dest=""):
    if not hotels: return
    section_header(f"Recommended Hotels ({len(hotels)})")

    for h in hotels:
        name=h.get("name","Hotel"); rating=h.get("rating",0); price=h.get("price_per_night",0)
        loc=h.get("location",""); reason=h.get("reason",""); amenities=h.get("amenities",[])
        pros=h.get("pros",[]); cons=h.get("cons",[]); dist=h.get("distance_from_center","")
        murl=safe_url(h.get("maps_url","")) or maps_url(name, dest)
        wurl=safe_url(h.get("website_url",""))
        burl=f"https://www.booking.com/searchresults.html?ss={urllib.parse.quote_plus(name)}"
        stars="⭐"*int(rating) if rating else ""
        tier_color = "#22C55E" if price < 150 else "#F59E0B" if price < 300 else "#4F46E5"
        tier_label = "💰 Budget" if price < 150 else "💎 Mid-Range" if price < 300 else "👑 Luxury"

        am_html=''.join(f'<span style="display:inline-block;background:#EFF6FF;color:#2563EB;padding:0.2rem 0.55rem;border-radius:50px;font-size:0.72rem;font-weight:500;margin:0.1rem;">{sanitize_text(a)}</span>' for a in amenities[:6])
        pros_html=''.join(f'<div style="color:#16A34A;font-size:0.85rem;font-weight:500;">✓ {sanitize_text(p)}</div>' for p in pros[:3])
        cons_html=''.join(f'<div style="color:#DC2626;font-size:0.85rem;font-weight:500;">✗ {sanitize_text(c)}</div>' for c in cons[:2])
        links=f'<a href="{murl}" target="_blank" style="display:inline-block;padding:0.38rem 0.75rem;border-radius:8px;font-size:0.78rem;font-weight:600;color:#4F46E5;background:#F8FAFC;border:1.5px solid #E2E8F0;text-decoration:none;transition:all 0.2s;margin:0.15rem 0.22rem 0.15rem 0;" class="lk">🗺️ Google Maps</a><a href="{burl}" target="_blank" style="display:inline-block;padding:0.38rem 0.75rem;border-radius:8px;font-size:0.78rem;font-weight:600;color:#fff;background:linear-gradient(135deg,#4F46E5,#4F46E5);text-decoration:none;transition:all 0.2s;margin:0.15rem 0.22rem 0.15rem 0;" class="lk-f">📋 Book Now</a>'
        if wurl: links+=f'<a href="{wurl}" target="_blank" style="display:inline-block;padding:0.38rem 0.75rem;border-radius:8px;font-size:0.78rem;font-weight:600;color:#4F46E5;background:#F8FAFC;border:1.5px solid #E2E8F0;text-decoration:none;margin:0.15rem 0.22rem 0.15rem 0;">🌐 Website</a>'

        st.markdown(f"""<div class="anim-fade-up hl" style="background:#fff;border:1.5px solid #E2E8F0;border-left:4px solid #4F46E5;border-radius:16px;
        padding:1.3rem;margin-bottom:0.7rem;box-shadow:0 2px 8px rgba(124,58,237,0.05);
        transition:all 0.3s;">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:0.6rem;">
        <div style="flex:1;min-width:240px;">
        <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.2rem;">
        <span style="background:{tier_color};color:#fff;padding:0.15rem 0.5rem;border-radius:50px;font-size:0.68rem;font-weight:600;">{tier_label}</span>
        <span style="color:#F59E0B;font-size:0.85rem;">{stars} {rating}/5</span>
        </div>
        <div style="font-size:1.15rem;font-weight:700;color:#0F172A;">{sanitize_text(name)}</div>
        <div style="display:flex;align-items:center;gap:0.5rem;margin:0.2rem 0;">
        <span style="color:#64748B;font-size:0.8rem;">📍 {sanitize_text(loc)}</span>
        {'<span style="color:#94A3B8;font-size:0.8rem;">· '+sanitize_text(dist)+'</span>' if dist else ''}
        </div></div>
        <div style="text-align:right;"><div style="font-size:1.4rem;font-weight:700;color:#4F46E5;">${price:,.0f}<span style="font-size:0.8rem;color:#94A3B8;font-weight:400;">/night</span></div></div>
        </div>
        {'<div style="margin:0.5rem 0;">'+am_html+'</div>' if am_html else ''}
        <p style="color:#334155;font-size:0.9rem;margin:0.4rem 0;line-height:1.5;">{sanitize_text(reason)}</p>
        {'<div style="display:flex;gap:1.5rem;flex-wrap:wrap;margin:0.4rem 0;"><div>'+pros_html+'</div><div>'+cons_html+'</div></div>' if pros_html or cons_html else ''}
        <div class="link-btns" style="margin-top:0.6rem;">{links}</div>
        </div>""", unsafe_allow_html=True)


# ─── ATTRACTIONS SECTION ──────────────────────────────────────────────────────

def render_attractions(attrs, dest=""):
    if not attrs: return
    section_header(f"Top Attractions ({len(attrs)})", color="#DB2777")

    for a in attrs:
        name=a.get("name",""); desc=a.get("description",""); cat=a.get("category","")
        rating=a.get("rating",0); fee=a.get("entry_fee",""); hours=a.get("opening_hours","")
        treq=a.get("time_required",""); best=a.get("best_time","")
        murl=safe_url(a.get("maps_url","")) or maps_url(name, dest); wurl=safe_url(a.get("website_url",""))

        cat_colors = {"museum":"#4F46E5","temple":"#F59E0B","park":"#22C55E","monument":"#DB2777","beach":"#0EA5E9","market":"#F97316"}
        cat_color = cat_colors.get(cat.lower(),"#4F46E5") if cat else "#4F46E5"
        cat_html=f'<span style="background:{cat_color}22;color:{cat_color};padding:0.18rem 0.55rem;border-radius:50px;font-size:0.7rem;font-weight:600;">{sanitize_text(cat)}</span>' if cat else ""

        details=[]
        if fee: details.append(f'🎫 {sanitize_text(fee)}')
        if hours: details.append(f'🕐 {sanitize_text(hours)}')
        if treq: details.append(f'⏱️ {sanitize_text(treq)}')
        if best: details.append(f'📅 {sanitize_text(best)}')

        links=f'<a href="{murl}" target="_blank" style="display:inline-block;padding:0.3rem 0.65rem;border-radius:8px;font-size:0.75rem;font-weight:600;color:#DB2777;background:#FDF2F8;border:1.5px solid #FCE7F3;text-decoration:none;margin:0.15rem 0.22rem 0.15rem 0;">🗺️ Maps</a>'
        if wurl: links+=f'<a href="{wurl}" target="_blank" style="display:inline-block;padding:0.3rem 0.65rem;border-radius:8px;font-size:0.75rem;font-weight:600;color:#DB2777;background:#FDF2F8;border:1.5px solid #FCE7F3;text-decoration:none;margin:0.15rem 0.22rem 0.15rem 0;">🌐 Website</a>'

        st.markdown(f"""<div class="anim-fade-up hl-pk" style="background:#fff;border:1.5px solid #FCE7F3;border-left:4px solid #DB2777;border-radius:14px;
        padding:1.1rem;margin-bottom:0.6rem;box-shadow:0 1px 3px rgba(236,72,153,0.06);
        transition:all 0.3s;">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;">
        <div>
        <div style="font-size:1.05rem;font-weight:700;color:#0F172A;">{sanitize_text(name)}</div>
        <div style="margin:0.25rem 0;">{cat_html} <span style="color:#F59E0B;font-size:0.8rem;margin-left:0.3rem;">⭐ {rating}</span></div>
        </div></div>
        <p style="color:#334155;font-size:0.88rem;margin:0.3rem 0;line-height:1.5;">{sanitize_text(desc)}</p>
        {'<div style="color:#64748B;font-size:0.8rem;">'+' · '.join(details)+'</div>' if details else ''}
        <div class="link-btns" style="margin-top:0.4rem;">{links}</div>
        </div>""", unsafe_allow_html=True)


# ─── DAILY ITINERARY (accordion) ─────────────────────────────────────────────

def render_daily_plans(plans):
    if not plans: return
    section_header(f"Day-by-Day Itinerary ({len(plans)} days)", color="#059669")

    for dp in plans:
        dn=dp.get("day_number",0); title=dp.get("title",f"Day {dn}")
        cost=dp.get("estimated_daily_cost",0); highlights=dp.get("highlights",[])

        hl=""
        if highlights:
            hl='<div style="margin-bottom:0.6rem;">'+''.join('<span style="display:inline-block;background:#DCFCE7;color:#166534;padding:0.18rem 0.55rem;border-radius:50px;font-size:0.72rem;font-weight:500;margin:0.08rem;">'+esc(h)+'</span>' for h in highlights[:5])+'</div>'

        with st.expander(f"Day {dn}: {esc(title)} — Est. ${cost:,.0f}", expanded=False):
            st.markdown(hl, unsafe_allow_html=True)
            for lbl,content,bdr in [("Morning",dp.get("morning",""),"#4F46E5"),("Afternoon",dp.get("afternoon",""),"#D97706"),
                ("Evening",dp.get("evening",""),"#4338CA"),("Night",dp.get("night",""),"#6366F1")]:
                if content:
                    st.markdown(f"""<div style="padding:0.6rem 0.9rem;border-left:3px solid {bdr};
                    background:#F8F5FF;border-radius:0 10px 10px 0;margin-bottom:0.4rem;">
                    <div style="font-weight:700;color:{bdr};font-size:0.72rem;text-transform:uppercase;letter-spacing:0.5px;">{lbl}</div>
                    <div style="color:#334155;font-size:0.9rem;line-height:1.5;margin-top:0.15rem;">{esc(content)}</div></div>""", unsafe_allow_html=True)
            meals=[]
            if dp.get("lunch"): meals.append(f'🍽️ **Lunch:** {esc(dp["lunch"])}')
            if dp.get("dinner"): meals.append(f'🍷 **Dinner:** {esc(dp["dinner"])}')
            if meals: st.markdown(" &nbsp;&nbsp; ".join(meals))


# ─── BUDGET ───────────────────────────────────────────────────────────────────

def render_budget(budget, req):
    if not budget: return
    section_header("Budget Dashboard", color="#059669")

    cats=["Hotel","Food","Transport","Activities","Misc"]
    vals=[budget.get("hotel",0),budget.get("food",0),budget.get("transport",0),
          budget.get("activities",0),budget.get("miscellaneous",0)]
    colors=["#4F46E5","#22C55E","#F59E0B","#4F46E5","#94A3B8"]
    icons=["🏨","🍽️","🚗","🎯","📦"]
    total=budget.get("total",0); user_b=req.get("budget",total)
    remaining=budget.get("remaining",user_b-total); pp=budget.get("per_person",0)
    within=budget.get("within_budget",True)

    c1,c2=st.columns([1,1])
    with c1:
        fig=go.Figure(data=[go.Pie(labels=cats,values=vals,hole=0.58,marker=dict(colors=colors),
            textinfo="label+percent",textfont=dict(size=11))])
        fig.update_layout(showlegend=False,margin=dict(t=15,b=15,l=15,r=15),
            paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font=dict(color="#0F172A"),height=280)
        st.plotly_chart(fig,width="stretch")
    with c2:
        status_bg = "linear-gradient(135deg,#22C55E,#16A34A)" if within else "linear-gradient(135deg,#EF4444,#DC2626)"
        status_txt = "✅ Within Budget" if within else "⚠️ Over Budget"
        st.markdown(f"""<div class="anim-scale-in" style="background:{status_bg};border-radius:18px;
        padding:1.5rem;color:#fff;text-align:center;box-shadow:0 6px 20px rgba(0,0,0,0.1);">
        <div style="font-size:2.2rem;font-weight:800;">${total:,.0f}</div>
        <div style="font-size:0.78rem;opacity:0.8;margin-bottom:0.8rem;">Total Cost</div>
        <div style="display:flex;justify-content:space-around;text-align:center;">
        <div><div style="font-size:1.1rem;font-weight:700;">${user_b:,.0f}</div><div style="font-size:0.68rem;opacity:0.7;">Budget</div></div>
        <div><div style="font-size:1.1rem;font-weight:700;">${pp:,.0f}</div><div style="font-size:0.68rem;opacity:0.7;">Per Person</div></div>
        <div><div style="font-size:1.1rem;font-weight:700;color:{'#86EFAC' if remaining>=0 else '#FCA5A5'};">${remaining:,.0f}</div><div style="font-size:0.68rem;opacity:0.7;">Left</div></div>
        </div>
        <div style="margin-top:0.8rem;padding:0.4rem;border-radius:8px;background:rgba(255,255,255,0.15);font-weight:600;font-size:0.85rem;">
        {status_txt}</div></div>""", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:0.6rem;'></div>",unsafe_allow_html=True)
    for cat,val,icon in zip(cats,vals,icons):
        c1,c2=st.columns([4,1])
        with c1: st.markdown(f"**{icon} {cat}**"); st.progress(min(val/max(total,1),1.0))
        with c2: st.markdown(f"**${val:,.0f}**")

    sugg=budget.get("suggestions",[])
    if sugg:
        with st.expander("💡 Cost-Saving Tips"):
            for s in sugg: st.markdown(f"• {esc(s)}")


# ─── FOOD SECTION ─────────────────────────────────────────────────────────────

def render_food(rests, dest=""):
    if not rests: return
    section_header(f"Food & Restaurants ({len(rests)})", color="#D97706")

    for r in rests:
        name=r.get("name",""); cuisine=r.get("cuisine",""); rating=r.get("rating",0)
        pr=r.get("price_range",""); desc=r.get("description",""); hours=r.get("opening_hours","")
        murl=safe_url(r.get("maps_url","")) or maps_url(name+" restaurant", dest); wurl=safe_url(r.get("website_url",""))

        links=f'<a href="{murl}" target="_blank" style="display:inline-block;padding:0.3rem 0.6rem;border-radius:8px;font-size:0.73rem;font-weight:600;color:#C2410C;background:#FFF7ED;border:1.5px solid #FED7AA;text-decoration:none;margin:0.15rem 0.22rem 0.15rem 0;">🗺️ Maps</a>'
        if wurl: links+=f'<a href="{wurl}" target="_blank" style="display:inline-block;padding:0.3rem 0.6rem;border-radius:8px;font-size:0.73rem;font-weight:600;color:#C2410C;background:#FFF7ED;border:1.5px solid #FED7AA;text-decoration:none;margin:0.15rem 0.22rem 0.15rem 0;">🌐 Website</a>'

        st.markdown(f"""<div class="anim-fade-up hl-or" style="background:#fff;border:1.5px solid #FED7AA;border-left:4px solid #F97316;border-radius:14px;
        padding:1.1rem;margin-bottom:0.6rem;box-shadow:0 1px 3px rgba(249,115,22,0.06);
        transition:all 0.3s;">
        <div style="font-weight:700;color:#0F172A;font-size:1rem;">{sanitize_text(name)}</div>
        <div style="margin:0.25rem 0;">
        {'<span style="background:#FFEDD5;color:#9A3412;padding:0.18rem 0.55rem;border-radius:50px;font-size:0.7rem;font-weight:600;">'+sanitize_text(cuisine)+'</span> ' if cuisine else ''}
        <span style="color:#F59E0B;font-size:0.8rem;">⭐ {rating}</span>
        {' <span style="background:#DCFCE7;color:#166534;padding:0.18rem 0.55rem;border-radius:50px;font-size:0.7rem;font-weight:600;margin-left:0.3rem;">'+sanitize_text(pr)+'</span>' if pr else ''}
        </div>
        {'<p style="color:#334155;font-size:0.85rem;margin:0.3rem 0;line-height:1.5;">'+sanitize_text(desc)+'</p>' if desc else ''}
        {'<div style="color:#64748B;font-size:0.78rem;">🕐 '+sanitize_text(hours)+'</div>' if hours else ''}
        <div class="link-btns" style="margin-top:0.4rem;">{links}</div>
        </div>""", unsafe_allow_html=True)


# ─── TRANSPORT ────────────────────────────────────────────────────────────────

def render_transport(transport):
    if not transport: return
    section_header("Getting Around", color="#4338CA")

    mi={"metro":"🚇","subway":"🚇","bus":"🚌","taxi":"🚕","uber":"📱","lyft":"📱",
        "walking":"🚶","rental":"🚗","tram":"🚊","train":"🚆","ferry":"⛴️","bicycle":"🚲"}
    for t in transport:
        mode=t.get("mode",""); icon=mi.get(mode.lower(),"🚗") if mode else "🚗"
        desc=t.get("description",""); t_est=t.get("estimated_time","")
        c_est=t.get("estimated_cost",""); tips=t.get("tips","")

        c1,c2=st.columns([1,4])
        with c1:
            st.markdown(f"""<div class="anim-scale-in" style="text-align:center;background:#F1F5F9;border-radius:16px;padding:1rem;">
            <div style="font-size:1.8rem;">{icon}</div>
            <div style="font-weight:700;color:#0F172A;text-transform:capitalize;font-size:0.85rem;margin-top:0.2rem;">{esc(mode)}</div></div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""<div style="background:#fff;border:1.5px solid #E2E8F0;border-left:4px solid #6366F1;border-radius:14px;
            padding:1rem;height:100%;box-shadow:0 1px 3px rgba(124,58,237,0.04);">
            <p style="color:#334155;margin:0;line-height:1.5;font-size:0.9rem;">{esc(desc)}</p>
            <div style="display:flex;gap:0.7rem;margin-top:0.4rem;flex-wrap:wrap;color:#64748B;font-size:0.8rem;">
            {'<span>⏱️ '+esc(t_est)+'</span>' if t_est else ''}
            {'<span>💵 '+esc(c_est)+'</span>' if c_est else ''}
            </div>
            {'<div style="color:#4F46E5;font-size:0.8rem;margin-top:0.3rem;font-weight:500;">💡 '+esc(tips)+'</div>' if tips else ''}
            </div>""", unsafe_allow_html=True)
        st.markdown("")


# ─── PACKING ──────────────────────────────────────────────────────────────────

def render_packing(packing):
    if not packing: return
    section_header("Packing Checklist", color="#D97706")

    gi={"documents":"📄","electronics":"📱","medicines":"💊","clothes":"👕","essentials":"🎒"}
    cols=st.columns(2)
    for i,(grp,items) in enumerate(packing.items()):
        if items:
            with cols[i%2]:
                icon=gi.get(grp.lower(),"📦")
                cbs=''.join(f'<div style="padding:0.3rem 0;border-bottom:1px solid #F3F4F6;color:#334155;font-size:0.88rem;">☐ {esc(item)}</div>' for item in items)
                st.markdown(f"""<div class="anim-scale-in anim-delay-{i+1}" style="background:#FFFBEB;border:1.5px solid #FDE68A;border-left:4px solid #F59E0B;border-radius:14px;
                padding:1rem;margin-bottom:0.6rem;box-shadow:0 2px 6px rgba(245,158,11,0.06);">
                <div style="font-weight:700;color:#92400E;margin-bottom:0.4rem;font-size:0.95rem;">{icon} {grp.title()}</div>{cbs}</div>""", unsafe_allow_html=True)


# ─── AI INSIGHTS ──────────────────────────────────────────────────────────────

def render_insights(insights):
    if not insights: return
    section_header("AI Travel Insights", color="#4F46E5")

    secs=[
        ("hidden_gems","Hidden Gems","#4F46E5"),("tourist_traps","Tourist Traps","#DC2626"),
        ("local_food","Must-Try Local Food","#D97706"),("safety_tips","Safety Tips","#059669"),
        ("money_tips","Money-Saving Tips","#4338CA"),("scam_alerts","Scam Alerts","#DC2626"),
        ("photography_spots","Best Photo Spots","#6366F1"),("sunrise_spots","Best Sunrise/Sunset","#D97706"),
    ]
    cols=st.columns(2)
    for i,(key,title,color) in enumerate(secs):
        items=insights.get(key,[])
        if items:
            with cols[i%2]:
                items_html=''.join(f'<li style="padding:0.25rem 0;color:#334155;font-size:0.88rem;line-height:1.5;">{esc(item)}</li>' for item in items)
                st.markdown(f"""<div class="anim-fade-up" style="background:#fff;border:1.5px solid #E2E8F0;border-left:4px solid {color};border-radius:14px;
                padding:1rem;margin-bottom:0.6rem;box-shadow:0 1px 4px rgba(124,58,237,0.05);">
                <div style="font-weight:700;color:{color};margin-bottom:0.5rem;font-size:0.95rem;">{title}</div>
                <ul style="margin:0;padding-left:1rem;">{items_html}</ul></div>""", unsafe_allow_html=True)


# ─── TRAVEL TIPS ──────────────────────────────────────────────────────────────

def render_tips(tips, carry, best_times):
    section_header("Travel Tips & Essentials", color="#4338CA")

    if tips:
        st.markdown('<div style="font-weight:700;color:#0F172A;margin-bottom:0.4rem;">📝 Travel Tips</div>', unsafe_allow_html=True)
        tips_html = ''.join(f'<div style="padding:0.4rem 0.6rem;background:#EEF2FF;border-left:3px solid #4F46E5;border-radius:0 8px 8px 0;margin-bottom:0.3rem;font-size:0.88rem;color:#334155;">{esc(t)}</div>' for t in tips)
        st.markdown(tips_html, unsafe_allow_html=True)
        st.markdown("")

    if carry:
        st.markdown('<div style="font-weight:700;color:#0F172A;margin-bottom:0.4rem;">🎒 Things to Carry</div>', unsafe_allow_html=True)
        carry_html = ''.join(f'<div style="padding:0.4rem 0.6rem;background:#EEF2FF;border-left:3px solid #6366F1;border-radius:0 8px 8px 0;margin-bottom:0.3rem;font-size:0.88rem;color:#334155;">{esc(c)}</div>' for c in carry)
        st.markdown(carry_html, unsafe_allow_html=True)
        st.markdown("")

    if best_times:
        st.markdown('<div style="font-weight:700;color:#0F172A;margin-bottom:0.4rem;">⏰ Best Times to Visit</div>', unsafe_allow_html=True)
        bt_html = ''.join(f'<div style="padding:0.4rem 0.6rem;background:#FEF3C7;border-left:3px solid #F59E0B;border-radius:0 8px 8px 0;margin-bottom:0.3rem;font-size:0.88rem;color:#334155;">{esc(b)}</div>' for b in best_times)
        st.markdown(bt_html, unsafe_allow_html=True)


# ─── OVERVIEW TAB CONTENT ─────────────────────────────────────────────────────

def render_overview(itin, req):
    with st.expander("📝 Trip Summary", expanded=True):
        st.markdown(clean_display(itin.get("trip_summary","")))

    with st.expander("🌍 Destination Overview", expanded=False):
        st.markdown(clean_display(itin.get("destination_overview","")))

    # Quick stats
    stats = [
        ("📅", f"{req.get('num_days',0)} days"),
        ("👥", f"{req.get('num_travellers',0)} travelers"),
        ("💰", f"${req.get('budget',0):,.0f} budget"),
        ("🎯", ", ".join(req.get("interests",[]))[:40]),
    ]
    stats_html = ''.join(f'<span style="display:inline-flex;align-items:center;gap:0.3rem;background:#F8FAFC;border:1px solid #E2E8F0;padding:0.3rem 0.7rem;border-radius:50px;font-size:0.82rem;color:#4F46E5;font-weight:500;margin:0.15rem;">{ic} {txt}</span>' for ic,txt in stats)
    st.markdown(f'<div style="margin-top:0.8rem;">{stats_html}</div>', unsafe_allow_html=True)


# ─── PDF EXPORT ───────────────────────────────────────────────────────────────

def export_pdf(itin, req):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.lib.colors import HexColor
        from reportlab.lib.enums import TA_CENTER
    except ImportError:
        st.error("reportlab not installed"); return None

    path=Path(__file__).parent.parent/"trip_itinerary.pdf"
    doc=SimpleDocTemplate(str(path),pagesize=A4,topMargin=18*mm,bottomMargin=18*mm,leftMargin=18*mm,rightMargin=18*mm)
    styles=getSampleStyleSheet()
    PUR=HexColor("#4F46E5"); PURL=HexColor("#F1F5F9"); PUD=HexColor("#4C1D95")
    TXT=HexColor("#0F172A"); GRAY=HexColor("#64748B"); W=HexColor("#FFFFFF")
    BLU=HexColor("#EFF6FF"); BLUD=HexColor("#1E40AF"); GRN=HexColor("#DCFCE7"); GRND=HexColor("#166534")
    ORG=HexColor("#FFEDD5"); ORGD=HexColor("#9A3412"); SKY=HexColor("#E0F2FE"); SKYD=HexColor("#0C4A6E")
    PNK=HexColor("#FFF1F2")

    s_title=ParagraphStyle("T",parent=styles["Title"],fontSize=24,textColor=PUR,fontName="Helvetica-Bold",spaceAfter=4)
    s_sub=ParagraphStyle("Sub",parent=styles["Normal"],fontSize=9,textColor=GRAY,spaceAfter=10)
    s_h2=ParagraphStyle("H2",parent=styles["Heading2"],fontSize=13,textColor=PUR,spaceBefore=8,spaceAfter=5,fontName="Helvetica-Bold")
    s_h3=ParagraphStyle("H3",parent=styles["Heading3"],fontSize=11,textColor=TXT,spaceBefore=5,spaceAfter=3,fontName="Helvetica-Bold")
    s_body=ParagraphStyle("B",parent=styles["BodyText"],fontSize=9.5,textColor=TXT,spaceAfter=3,leading=14)
    s_small=ParagraphStyle("S",parent=styles["BodyText"],fontSize=8.5,textColor=GRAY,spaceAfter=2,leading=12)
    s_bullet=ParagraphStyle("Bul",parent=styles["BodyText"],fontSize=9.5,textColor=TXT,spaceAfter=2,leading=13,leftIndent=10)
    story=[]

    dest=req.get("destination","Destination"); src=req.get("source_city","")
    days=req.get("num_days",0); travelers=req.get("num_travellers",0)
    budget=req.get("budget",0); interests=req.get("interests",[])

    def bar(title,emoji="",bg=PUR,fg=W):
        t=[[Paragraph(f"<b>{emoji} {title}</b>",ParagraphStyle("BT",parent=s_body,textColor=fg,fontSize=12,fontName="Helvetica-Bold"))]]
        t=Table(t,colWidths=[doc.width])
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),bg),("LEFTPADDING",(0,0),(-1,-1),10),
            ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7)]))
        story.append(Spacer(1,5*mm)); story.append(t); story.append(Spacer(1,2*mm))

    def card(flowables):
        inner=[[f] for f in flowables]
        t=Table(inner,colWidths=[doc.width-6*mm])
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),W),("BOX",(0,0),(-1,-1),0.5,HexColor("#F1F5F9")),
            ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),
            ("TOPPADDING",(0,0),(0,0),8),("BOTTOMPADDING",(-1,-1),(-1,-1),8)]))
        story.append(t); story.append(Spacer(1,2*mm))

    def lnk(url,label): return f'<a href="{url}" color="#4F46E5"><u>{label}</u></a>'

    story.append(Paragraph(f"{dest_flag(dest)} {dest}",s_title))
    story.append(Paragraph(f"{src} → {dest} | {days} days | {travelers} travelers | ${budget:,.0f} | {', '.join(interests)}",s_sub))
    story.append(HRFlowable(width="100%",thickness=2,color=PURL,spaceAfter=4))

    s=clean_display(itin.get("trip_summary",""))
    if s: bar("Trip Summary","📝"); card([Paragraph(s.replace("\n","<br/>"),s_body)])
    o=clean_display(itin.get("destination_overview",""))
    if o: bar("Destination Overview","🌍"); card([Paragraph(o.replace("\n","<br/>"),s_body)])

    w=itin.get("weather_summary",{})
    if w:
        bar("Weather Forecast","🌤️",bg=HexColor("#0EA5E9"),fg=W)
        wt=f"<b>Temperature:</b> {w.get('temperature',0)}°C | <b>Condition:</b> {esc(w.get('condition','N/A'))}"
        if w.get("description"): wt+=f"<br/><b>Description:</b> {esc(w['description'])}"
        rain_val = w.get('rain_chance')
        rain_str = f"{rain_val}%" if rain_val is not None else "N/A"
        wt+=f"<br/><b>Humidity:</b> {w.get('humidity',0)}% | <b>Wind:</b> {w.get('wind_speed',0)} m/s | <b>Rain:</b> {rain_str}"
        if w.get("sunrise"): wt+=f"<br/><b>Sunrise:</b> {esc(w['sunrise'])} | <b>Sunset:</b> {esc(w.get('sunset',''))}"
        card([Paragraph(wt,s_body)])
        for sg in w.get("suggestions",[]): story.append(Paragraph(f"• {sg}",s_bullet))

    hotels=itin.get("recommended_hotels",[])
    if hotels:
        bar("Recommended Hotels","🏨",bg=HexColor("#4F46E5"),fg=W)
        for h in hotels:
            lines=[Paragraph(f"<b>{esc(h.get('name',''))}</b> | ⭐ {h.get('rating',0)}/5 | ${h.get('price_per_night',0):,.0f}/night",s_h3)]
            lt=f"📍 {esc(h.get('location',''))}"
            if h.get("distance_from_center"): lt+=f" · {esc(h['distance_from_center'])}"
            lines.append(Paragraph(lt,s_small))
            if h.get("reason"): lines.append(Paragraph(esc(h["reason"]),s_body))
            if h.get("amenities"): lines.append(Paragraph("<b>Amenities:</b> "+", ".join(h["amenities"][:6]),s_small))
            for p in h.get("pros",[])[:3]: lines.append(Paragraph(f"<font color='#22C55E'>✓</font> {esc(p)}",s_small))
            for c in h.get("cons",[])[:2]: lines.append(Paragraph(f"<font color='#EF4444'>✗</font> {esc(c)}",s_small))
            m=safe_url(h.get("maps_url","")) or maps_url(h.get("name",""), dest)
            bu=f"https://www.booking.com/searchresults.html?ss={urllib.parse.quote_plus(h.get('name',''))}"
            lk=[lnk(m,"Google Maps"),lnk(bu,"Book Now")]
            if safe_url(h.get("website_url")): lk.append(lnk(safe_url(h["website_url"]),"Website"))
            lines.append(Paragraph("Links: "+" | ".join(lk),s_small))
            card(lines)

    attrs=itin.get("attractions",[])
    if attrs:
        bar("Top Attractions","🎯",bg=HexColor("#DB2777"),fg=W)
        for a in attrs:
            lt=f"<b>{esc(a.get('name',''))}</b>"
            if a.get("rating"): lt+=f" | ⭐ {a['rating']}"
            if a.get("category"): lt+=f" | <font color='#4F46E5'>[{esc(a['category'])}]</font>"
            lines=[Paragraph(lt,s_h3)]
            if a.get("description"): lines.append(Paragraph(esc(a["description"]),s_body))
            dp=[]
            if a.get("entry_fee"): dp.append(f"🎫 {esc(a['entry_fee'])}")
            if a.get("opening_hours"): dp.append(f"🕐 {esc(a['opening_hours'])}")
            if a.get("time_required"): dp.append(f"⏱️ {esc(a['time_required'])}")
            if a.get("best_time"): dp.append(f"📅 {esc(a['best_time'])}")
            if dp: lines.append(Paragraph(" | ".join(dp),s_small))
            m=safe_url(a.get("maps_url","")) or maps_url(a.get("name",""), dest)
            lk=[lnk(m,"Google Maps")]
            if safe_url(a.get("website_url")): lk.append(lnk(safe_url(a["website_url"]),"Website"))
            lines.append(Paragraph("Links: "+" | ".join(lk),s_small))
            card(lines)

    rests=itin.get("restaurants",[])
    if rests:
        bar("Food & Restaurants","🍽️",bg=HexColor("#F97316"),fg=W)
        for r in rests:
            lt=f"<b>{esc(r.get('name',''))}</b>"
            if r.get("rating"): lt+=f" | ⭐ {r['rating']}"
            if r.get("cuisine"): lt+=f" | <font color='#F97316'>[{esc(r['cuisine'])}]</font>"
            if r.get("price_range"): lt+=f" | <font color='#22C55E'>{esc(r['price_range'])}</font>"
            lines=[Paragraph(lt,s_h3)]
            if r.get("description"): lines.append(Paragraph(esc(r["description"]),s_body))
            if r.get("opening_hours"): lines.append(Paragraph(f"🕐 {esc(r['opening_hours'])}",s_small))
            m=safe_url(r.get("maps_url","")) or maps_url(r.get("name","")+" restaurant", dest)
            lk=[lnk(m,"Google Maps")]
            if safe_url(r.get("website_url")): lk.append(lnk(safe_url(r["website_url"]),"Website"))
            lines.append(Paragraph("Links: "+" | ".join(lk),s_small))
            card(lines)

    trans=itin.get("transport_options",[])
    if trans:
        bar("Getting Around","🚗",bg=HexColor("#6366F1"),fg=W)
        for t in trans:
            lines=[Paragraph(f"<b>{esc(t.get('mode','').title())}</b>",s_h3)]
            if t.get("description"): lines.append(Paragraph(esc(t["description"]),s_body))
            d=[]
            if t.get("estimated_time"): d.append(f"⏱️ {esc(t['estimated_time'])}")
            if t.get("estimated_cost"): d.append(f"💵 {esc(t['estimated_cost'])}")
            if d: lines.append(Paragraph(" | ".join(d),s_small))
            if t.get("tips"): lines.append(Paragraph(f"<font color='#4F46E5'>💡 {esc(t['tips'])}</font>",s_small))
            card(lines)

    bd=itin.get("budget",{})
    if bd:
        bar("Budget Breakdown","💰",bg=HexColor("#22C55E"),fg=W)
        rows=[["Category","Amount","% of Total"]]
        cats_data=[("🏨 Hotel",bd.get("hotel",0)),("🍽️ Food",bd.get("food",0)),("🚗 Transport",bd.get("transport",0)),
            ("🎯 Activities",bd.get("activities",0)),("📦 Misc",bd.get("miscellaneous",0))]
        total=bd.get("total",0)
        for cn,v in cats_data:
            rows.append([cn,f"${v:,.0f}",f"{v/max(total,1)*100:.0f}%" if total else "0%"])
        rows.append(["","",""]); rows.append(["💰 Total",f"${total:,.0f}",""])
        rows.append(["👤 Per Person",f"${bd.get('per_person',0):,.0f}",""])
        rows.append(["📊 Status","✅ Within Budget" if bd.get("within_budget",True) else "⚠️ Over Budget",f"Remaining: ${bd.get('remaining',0):,.0f}"])
        bt=Table(rows,colWidths=[doc.width*0.45,doc.width*0.3,doc.width*0.25])
        bt.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),HexColor("#DCFCE7")),("TEXTCOLOR",(0,0),(-1,0),GRND),
            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),9),
            ("FONTNAME",(0,-3),(-1,-1),"Helvetica-Bold"),("ALIGN",(1,0),(-1,-1),"RIGHT"),
            ("GRID",(0,0),(-1,-3),0.5,HexColor("#E5E7EB")),
            ("BACKGROUND",(0,-1),(-1,-1),HexColor("#DCFCE7") if bd.get("within_budget",True) else HexColor("#FEE2E2")),
            ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),("LEFTPADDING",(0,0),(-1,-1),7)]))
        story.append(bt); story.append(Spacer(1,2*mm))
        for sg in bd.get("suggestions",[]): story.append(Paragraph(f"• {sg}",s_bullet))

    plans=itin.get("daily_plans",[])
    if plans:
        bar("Day-by-Day Itinerary","📅",bg=HexColor("#059669"),fg=W)
        for d in plans:
            dn=d.get("day_number",0); title=d.get("title",f"Day {dn}"); cost=d.get("estimated_daily_cost",0)
            story.append(Paragraph(f"<b>Day {dn}: {esc(title)}</b> | <font color='#059669'>Est. ${cost:,.0f}</font>",s_h2))
            for lbl,content in [("🌅 Morning",d.get("morning","")),("☀️ Afternoon",d.get("afternoon","")),
                ("🌆 Evening",d.get("evening","")),("🌙 Night",d.get("night",""))]:
                if content: story.append(Paragraph(f"<font color='#4F46E5'><b>{lbl}:</b></font> {esc(content)}",s_body))
            ml=[]
            if d.get("lunch"): ml.append(f"<b>🍽️ Lunch:</b> {esc(d['lunch'])}")
            if d.get("dinner"): ml.append(f"<b>🍷 Dinner:</b> {esc(d['dinner'])}")
            if ml: story.append(Paragraph(" | ".join(ml),s_body))
            story.append(Spacer(1,2*mm))

    ai=itin.get("ai_insights",{})
    if ai:
        bar("AI Travel Insights","🧠",bg=HexColor("#4F46E5"),fg=W)
        for key,title in [("hidden_gems","💎 Hidden Gems"),("tourist_traps","⚠️ Tourist Traps"),
            ("local_food","🍜 Must-Try Local Food"),("safety_tips","🛡️ Safety Tips"),
            ("money_tips","💵 Money-Saving Tips"),("scam_alerts","🚨 Scam Alerts"),
            ("photography_spots","📸 Best Photo Spots"),("sunrise_spots","🌅 Best Sunrise/Sunset")]:
            items=ai.get(key,[])
            if items:
                story.append(Paragraph(f"<b>{title}</b>",s_h3))
                for it in items: story.append(Paragraph(f"• {esc(it)}",s_bullet))
                story.append(Spacer(1,2*mm))

    pk=itin.get("packing_checklist",{})
    if pk:
        bar("Packing Checklist","🧳",bg=HexColor("#DB2777"),fg=W)
        for grp,items in pk.items():
            if items:
                story.append(Paragraph(f"<b>{grp.title()}</b>",s_h3))
                for it in items: story.append(Paragraph(f"☐ {esc(it)}",s_bullet))
                story.append(Spacer(1,2*mm))

    tips=itin.get("travel_tips",[])
    if tips:
        bar("Travel Tips","✈️")
        for t in tips: story.append(Paragraph(f"• {esc(t)}",s_bullet))

    carry=itin.get("things_to_carry",[])
    if carry:
        story.append(Spacer(1,3*mm)); story.append(Paragraph("<b>🎒 Things to Carry</b>",s_h3))
        for c in carry: story.append(Paragraph(f"• {esc(c)}",s_bullet))

    bt_list=itin.get("best_times",[])
    if bt_list:
        story.append(Spacer(1,3*mm)); story.append(Paragraph("<b>⏰ Best Times to Visit</b>",s_h3))
        for b in bt_list: story.append(Paragraph(f"• {esc(b)}",s_bullet))

    story.append(Spacer(1,8*mm))
    story.append(HRFlowable(width="100%",thickness=1,color=PURL))
    story.append(Spacer(1,2*mm))
    story.append(Paragraph(f"Generated by AI Travel Planner | {datetime.now().strftime('%B %d, %Y')}",
        ParagraphStyle("Ft",parent=s_small,alignment=TA_CENTER,textColor=GRAY)))

    doc.build(story)
    return str(path)


# ─── SAVE / LOAD ──────────────────────────────────────────────────────────────

def save_trip_locally(itin, req):
    user_name = st.session_state.get("user_name", "anonymous")
    trip_id = db.save_trip(user_name, req, itin)
    return trip_id

def load_saved_trips():
    user_name = st.session_state.get("user_name", "anonymous")
    return db.load_trips(user_name)

def delete_saved_trip(trip_id):
    return db.delete_trip(trip_id)


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    if "user_name" not in st.session_state or not st.session_state["user_name"]:
        render_welcome()
        return

    source_city, destination, num_days, budget, num_travellers, interests, hotel_pref, plan_clicked = render_sidebar()

    if plan_clicked:
        if not source_city or not destination:
            st.error("Please enter both source city and destination."); return
        if not interests:
            st.error("Please select at least one interest."); return

        trip_data={
            "source_city":source_city,"destination":destination,
            "num_days":int(num_days),"budget":float(budget),
            "num_travellers":int(num_travellers),"interests":interests,
            "hotel_preference":hotel_pref,
        }

        progress=st.progress(0,text="🚀 Starting AI agents...")
        with st.status("🤖 AI Agents Planning Your Trip...",expanded=True) as status:
            st.write("🏨 Hotel Specialist: Researching accommodations...")
            progress.progress(15,"🏨 Researching hotels..."); time.sleep(0.3)
            st.write("🎯 Attraction Guide: Finding top sights...")
            progress.progress(30,"🎯 Finding attractions..."); time.sleep(0.3)
            st.write("🌤️ Weather Advisor: Checking forecasts...")
            progress.progress(45,"🌤️ Checking weather...")
            t0=time.time()
            result=plan_trip_api(trip_data)
            elapsed=time.time()-t0
            if "error" not in result:
                st.write("✅ Planning complete!")
                progress.progress(100,f"✅ Done in {elapsed:.0f}s!")
                status.update(label="✅ Trip Planned Successfully!",state="complete",expanded=False)
            else:
                status.update(label="❌ Planning Failed",state="error")
        progress.empty()
        if "error" in result: st.error(f"❌ {result['error']}"); return
        st.session_state.itinerary=result
        st.session_state.trip_request=trip_data

    if "itinerary" in st.session_state:
        itin=st.session_state.itinerary
        req=st.session_state.trip_request

        # Back to Home button
        if st.button("← Back to Home", type="secondary"):
            del st.session_state.itinerary
            del st.session_state.trip_request

        render_hero(itin,req)
        render_metrics(itin,req)
        st.markdown("")

        tabs=st.tabs(["📋 Overview","🏨 Hotels","🎯 Attractions","📅 Itinerary","🌤️ Weather",
                       "💰 Budget","🍽️ Food","🚗 Transport","✈️ Travel Tips",
                       "🧳 Packing","🧠 AI Insights","📄 Export"])

        with tabs[0]:
            render_overview(itin,req)
        with tabs[1]:
            render_hotels(itin.get("recommended_hotels",[]), req.get("destination",""))
        with tabs[2]:
            render_attractions(itin.get("attractions",[]), req.get("destination",""))
        with tabs[3]:
            render_daily_plans(itin.get("daily_plans",[]))
        with tabs[4]:
            render_weather(itin.get("weather_summary",{}))
        with tabs[5]:
            render_budget(itin.get("budget",{}),req)
        with tabs[6]:
            render_food(itin.get("restaurants",[]), req.get("destination",""))
        with tabs[7]:
            render_transport(itin.get("transport_options",[]))
        with tabs[8]:
            render_tips(itin.get("travel_tips",[]),itin.get("things_to_carry",[]),itin.get("best_times",[]))
        with tabs[9]:
            render_packing(itin.get("packing_checklist",{}))
        with tabs[10]:
            render_insights(itin.get("ai_insights",{}))
        with tabs[11]:
            st.markdown("### 📥 Download Your Travel Brochure")
            st.markdown("The PDF mirrors the website design with colored section bars, cards, clickable links, and all trip data.")
            if st.button("📄 Generate & Download PDF",type="primary",width="stretch"):
                with st.spinner("Generating your travel brochure..."):
                    pdf=export_pdf(itin,req)
                if pdf:
                    with open(pdf,"rb") as f:
                        st.download_button("⬇️ Click to Download",data=f.read(),
                            file_name=f"{req.get('destination','trip')}_itinerary.pdf",mime="application/pdf",width="stretch")
                    st.success("✅ PDF generated!")

            st.markdown("---")
            c1,c2=st.columns(2)
            with c1:
                if st.button("💾 Save Trip",width="stretch",type="secondary"):
                    trip_id=save_trip_locally(itin,req)
                    st.success(f"✅ Trip saved! ID: {trip_id}")
                    st.rerun()
            with c2:
                if st.button("🔄 Plan Another Trip",width="stretch"):
                    del st.session_state.itinerary
                    del st.session_state.trip_request
                    st.rerun()
    else:
        render_landing()


if __name__=="__main__":
    main()
