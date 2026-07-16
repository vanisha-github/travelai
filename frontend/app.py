import streamlit as st
import requests
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(
    page_title="AI Travel Planner",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.2rem;
        border-radius: 12px;
        color: white;
        text-align: center;
    }
    .hotel-card {
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        background: #fafafa;
    }
    .day-header {
        background: #1E88E5;
        color: white;
        padding: 0.6rem 1.2rem;
        border-radius: 8px;
        font-weight: 600;
        margin-bottom: 0.8rem;
    }
    .time-block {
        padding: 0.6rem 1rem;
        border-left: 3px solid #1E88E5;
        margin-bottom: 0.5rem;
        background: #f8f9fa;
        border-radius: 0 8px 8px 0;
    }
    .budget-bar {
        height: 24px;
        border-radius: 12px;
        display: flex;
        overflow: hidden;
        margin: 0.5rem 0;
    }
    .tip-item {
        padding: 0.4rem 0;
        border-bottom: 1px solid #f0f0f0;
    }
</style>
""", unsafe_allow_html=True)


def ensure_backend_running() -> bool:
    try:
        resp = requests.get(f"{BACKEND_URL}/health", timeout=3)
        return resp.status_code == 200
    except requests.ConnectionError:
        return False


def start_backend():
    backend_main = Path(__file__).parent.parent / "backend" / "main.py"
    if backend_main.exists():
        subprocess.Popen(
            [sys.executable, str(backend_main)],
            cwd=str(backend_main.parent),
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
        )
        time.sleep(3)
    return ensure_backend_running()


def plan_trip(trip_data: dict) -> dict:
    try:
        resp = requests.post(f"{BACKEND_URL}/plan-trip", json=trip_data, timeout=300)
        resp.raise_for_status()
        return resp.json()
    except requests.ConnectionError:
        return {"error": "Backend server is not running. Please start the backend first."}
    except requests.HTTPError as e:
        return {"error": f"Server error: {e.response.status_code} - {e.response.text}"}
    except requests.Timeout:
        return {"error": "Request timed out. The trip planning is taking longer than expected."}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


def display_trip_summary(itinerary: dict):
    st.markdown("### 📋 Trip Summary")
    st.info(itinerary.get("trip_summary", "No summary available."))

    st.markdown("### 🌍 Destination Overview")
    st.write(itinerary.get("destination_overview", "No overview available."))


def display_weather(weather: dict):
    st.markdown("### 🌤️ Weather Summary")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🌡️ Temperature", f"{weather.get('temperature', 'N/A')}°C")
    with col2:
        st.metric("💧 Humidity", f"{weather.get('humidity', 'N/A')}%")
    with col3:
        st.metric("☁️ Condition", weather.get("condition", "N/A"))

    suggestions = weather.get("suggestions", [])
    if suggestions:
        st.markdown("**AI Suggestions:**")
        for s in suggestions:
            st.markdown(f"- {s}")


def display_hotels(hotels: list):
    st.markdown("### 🏨 Recommended Hotels")

    for hotel in hotels:
        with st.container():
            cols = st.columns([3, 1, 1])
            with cols[0]:
                st.markdown(f"**{hotel.get('name', 'Unknown')}**")
                st.caption(hotel.get("location", ""))
            with cols[1]:
                rating = hotel.get("rating", 0)
                stars = "⭐" * int(rating)
                st.markdown(f"{stars} ({rating})")
            with cols[2]:
                st.markdown(f"**${hotel.get('price_per_night', 0):,.0f}**/night")

            reason = hotel.get("reason", "")
            if reason:
                st.caption(f"💡 {reason}")
            st.divider()


def display_budget(budget: dict):
    st.markdown("### 💰 Budget Breakdown")

    categories = {
        "🏨 Hotel": budget.get("hotel", 0),
        "🍽️ Food": budget.get("food", 0),
        "🚌 Transport": budget.get("transport", 0),
        "🎭 Activities": budget.get("activities", 0),
        "📦 Miscellaneous": budget.get("miscellaneous", 0),
    }

    total = budget.get("total", 1)
    colors = ["#1E88E5", "#43A047", "#FB8C00", "#E53935", "#8E24AA"]

    bar_html = '<div class="budget-bar">'
    for i, (label, amount) in enumerate(categories.items()):
        pct = (amount / total * 100) if total > 0 else 0
        bar_html += f'<div style="width:{pct}%;background:{colors[i]}" title="{label}: ${amount:,.0f}"></div>'
    bar_html += "</div>"
    st.markdown(bar_html, unsafe_allow_html=True)

    cols = st.columns(len(categories))
    for i, (label, amount) in enumerate(categories.items()):
        with cols[i]:
            st.markdown(f"<small>{label}</small>", unsafe_allow_html=True)
            st.markdown(f"**${amount:,.0f}**")

    st.divider()
    total_cost = budget.get("total", 0)
    within = budget.get("within_budget", True)

    if within:
        st.success(f"✅ **Total Estimated Cost: ${total_cost:,.0f}** — Within your budget!")
    else:
        st.warning(f"⚠️ **Total Estimated Cost: ${total_cost:,.0f}** — Exceeds your budget!")

    suggestions = budget.get("suggestions", [])
    if suggestions:
        with st.expander("💡 Cost-Saving Suggestions"):
            for s in suggestions:
                st.markdown(f"- {s}")


def display_itinerary(daily_plans: list):
    st.markdown("### 📅 Day-by-Day Itinerary")

    for day_plan in daily_plans:
        day_num = day_plan.get("day_number", 0)
        with st.expander(f"Day {day_num} — Est. ${day_plan.get('estimated_daily_cost', 0):,.0f}", expanded=(day_num == 1)):
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown("**🌅 Morning**")
                st.write(day_plan.get("morning", "N/A"))
            with c2:
                st.markdown("**☀️ Afternoon**")
                st.write(day_plan.get("afternoon", "N/A"))
            with c3:
                st.markdown("**🌙 Evening**")
                st.write(day_plan.get("evening", "N/A"))


def display_tips(tips: list, carry: list, best_times: list):
    st.markdown("### 🧳 Travel Tips & Packing")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Travel Tips**")
        for tip in tips:
            st.markdown(f"- {tip}")

    with col2:
        st.markdown("**Things to Carry**")
        for item in carry:
            st.markdown(f"- {item}")

    if best_times:
        st.markdown("**Best Times to Visit Attractions:**")
        for bt in best_times:
            st.markdown(f"- {bt}")


def export_as_pdf(itinerary: dict):
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch

        pdf_path = Path(__file__).parent.parent / "trip_itinerary.pdf"
        doc = SimpleDocTemplate(str(pdf_path), pagesize=letter, topMargin=0.75 * inch, bottomMargin=0.75 * inch)
        styles = getSampleStyleSheet()
        story = []

        title_style = ParagraphStyle("CustomTitle", parent=styles["Title"], fontSize=22, spaceAfter=12)
        heading_style = ParagraphStyle("CustomHeading", parent=styles["Heading2"], fontSize=14, spaceAfter=8, textColor="#1E88E5")

        story.append(Paragraph("AI Travel Planner - Trip Itinerary", title_style))
        story.append(Spacer(1, 0.3 * inch))

        story.append(Paragraph("Trip Summary", heading_style))
        story.append(Paragraph(itinerary.get("trip_summary", ""), styles["BodyText"]))
        story.append(Spacer(1, 0.2 * inch))

        story.append(Paragraph("Destination Overview", heading_style))
        story.append(Paragraph(itinerary.get("destination_overview", ""), styles["BodyText"]))
        story.append(Spacer(1, 0.2 * inch))

        hotels = itinerary.get("recommended_hotels", [])
        if hotels:
            story.append(Paragraph("Recommended Hotels", heading_style))
            for h in hotels:
                text = f"<b>{h.get('name', '')}</b> - Rating: {h.get('rating', 0)}/5 - ${h.get('price_per_night', 0):,.0f}/night<br/>{h.get('location', '')}<br/>{h.get('reason', '')}"
                story.append(Paragraph(text, styles["BodyText"]))
                story.append(Spacer(1, 0.1 * inch))

        budget = itinerary.get("budget", {})
        if budget:
            story.append(Paragraph("Budget Breakdown", heading_style))
            for cat in ["hotel", "food", "transport", "activities", "miscellaneous"]:
                story.append(Paragraph(f"{cat.title()}: ${budget.get(cat, 0):,.0f}", styles["BodyText"]))
            story.append(Paragraph(f"<b>Total: ${budget.get('total', 0):,.0f}</b>", styles["BodyText"]))
            story.append(Spacer(1, 0.2 * inch))

        daily_plans = itinerary.get("daily_plans", [])
        if daily_plans:
            story.append(Paragraph("Day-by-Day Itinerary", heading_style))
            for day in daily_plans:
                story.append(Paragraph(f"<b>Day {day.get('day_number', 0)}</b> (Est. ${day.get('estimated_daily_cost', 0):,.0f})", styles["Heading3"]))
                story.append(Paragraph(f"<b>Morning:</b> {day.get('morning', '')}", styles["BodyText"]))
                story.append(Paragraph(f"<b>Afternoon:</b> {day.get('afternoon', '')}", styles["BodyText"]))
                story.append(Paragraph(f"<b>Evening:</b> {day.get('evening', '')}", styles["BodyText"]))
                story.append(Spacer(1, 0.15 * inch))

        tips = itinerary.get("travel_tips", [])
        if tips:
            story.append(Paragraph("Travel Tips", heading_style))
            for tip in tips:
                story.append(Paragraph(f"- {tip}", styles["BodyText"]))

        carry = itinerary.get("things_to_carry", [])
        if carry:
            story.append(Paragraph("Things to Carry", heading_style))
            for item in carry:
                story.append(Paragraph(f"- {item}", styles["BodyText"]))

        doc.build(story)
        return str(pdf_path)
    except Exception as e:
        st.error(f"PDF generation failed: {e}")
        return None


def save_trip_locally(itinerary: dict, request_data: dict):
    trips_dir = Path(__file__).parent.parent / "saved_trips"
    trips_dir.mkdir(exist_ok=True)

    trip_id = datetime.now().strftime("trip_%Y%m%d_%H%M%S")
    trip_data = {"request": request_data, "itinerary": itinerary}

    trip_path = trips_dir / f"{trip_id}.json"
    with open(trip_path, "w") as f:
        json.dump(trip_data, f, indent=2, default=str)

    return str(trip_path)


def main():
    st.markdown('<div class="main-header">✈️ AI Travel Planner</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Multi-Agent system powered by CrewAI & Google Gemini</div>', unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("## 🗺️ Trip Details")

        source_city = st.text_input("Source City", placeholder="e.g., New York")
        destination = st.text_input("Destination", placeholder="e.g., Paris, France")
        num_days = st.number_input("Number of Days", min_value=1, max_value=30, value=5)
        budget = st.number_input("Budget (USD)", min_value=100, max_value=100000, value=2000, step=100)
        num_travellers = st.number_input("Travellers", min_value=1, max_value=20, value=2)

        st.markdown("**Travel Interests**")
        interest_options = ["nature", "adventure", "food", "history", "shopping", "beach", "nightlife"]
        selected_interests = st.multiselect("Select interests", interest_options, default=["food", "history"])

        st.markdown("**Hotel Preference**")
        hotel_pref = st.radio("Hotel tier", ["budget", "standard", "luxury"], index=1)

        st.divider()
        plan_button = st.button("🚀 Plan My Trip", type="primary", use_container_width=True)

    if plan_button:
        if not source_city or not destination:
            st.error("Please enter both source city and destination.")
            return

        if not selected_interests:
            st.error("Please select at least one interest.")
            return

        trip_data = {
            "source_city": source_city,
            "destination": destination,
            "num_days": int(num_days),
            "budget": float(budget),
            "num_travellers": int(num_travellers),
            "interests": selected_interests,
            "hotel_preference": hotel_pref,
        }

        with st.spinner("🤖 AI agents are planning your trip... This may take a few minutes."):
            result = plan_trip(trip_data)

        if "error" in result:
            st.error(f"❌ {result['error']}")
            return

        st.session_state.itinerary = result
        st.session_state.trip_request = trip_data

    if "itinerary" in st.session_state:
        itinerary = st.session_state.itinerary
        trip_request = st.session_state.trip_request

        display_trip_summary(itinerary)

        st.markdown("---")
        display_weather(itinerary.get("weather_summary", {}))

        st.markdown("---")
        display_hotels(itinerary.get("recommended_hotels", []))

        st.markdown("---")
        display_budget(itinerary.get("budget", {}))

        st.markdown("---")
        display_itinerary(itinerary.get("daily_plans", []))

        st.markdown("---")
        display_tips(
            itinerary.get("travel_tips", []),
            itinerary.get("things_to_carry", []),
            itinerary.get("best_times", []),
        )

        st.markdown("---")
        st.markdown("### 📥 Export & Save")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("📄 Export as PDF", use_container_width=True):
                pdf_path = export_as_pdf(itinerary)
                if pdf_path:
                    st.success(f"PDF saved to: {pdf_path}")
                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            "⬇️ Download PDF",
                            data=f.read(),
                            file_name="trip_itinerary.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                        )

        with col2:
            if st.button("💾 Save Trip Locally", use_container_width=True):
                path = save_trip_locally(itinerary, trip_request)
                st.success(f"Trip saved to: {path}")


if __name__ == "__main__":
    if not ensure_backend_running():
        st.info("🔄 Starting backend server...")
        if start_backend():
            st.success("✅ Backend started!")
            time.sleep(1)
        else:
            st.warning("⚠️ Backend not available. Starting in standalone mode.")

    main()
