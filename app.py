import streamlit as st
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from timezonefinder import TimezoneFinder

from schemas import Coordinates, CalendarEvent
from geocoder import resolve_location
from weather_client import fetch_weather
from traffic_client import calculate_route
from jev_engine import evaluate_commute_decision
from duration_estimator import estimate_event_duration
from calendar_sync import get_upcoming_events

load_dotenv()

st.set_page_config(page_title="Commute Guardian", page_icon="🧭", layout="wide")
tf = TimezoneFinder()

def get_tz(coords: Coordinates) -> ZoneInfo:
    tz_name = tf.timezone_at(lat=coords.latitude, lng=coords.longitude)
    return ZoneInfo(tz_name if tz_name else "UTC")

BASE_LAT = float(os.getenv("DEFAULT_ORIGIN_LAT", "22.7770"))
BASE_LON = float(os.getenv("DEFAULT_ORIGIN_LON", "86.1441"))
base_coords = Coordinates(latitude=BASE_LAT, longitude=BASE_LON)

st.title("🧭 Commute Guardian")
st.caption("Autonomous multi-agent commute planning & System 1 decision engine powered by Laya")

st.sidebar.header("Configuration")
data_source = st.sidebar.radio("Data Source", ["Live Google Calendar", "Demo Outing (Movie -> Date -> Shopping)"])
lookahead = st.sidebar.slider("Lookahead Window (hours)", 12, 72, 24)

events = []
if data_source == "Live Google Calendar":
    try:
        events = get_upcoming_events(lookahead_hours=lookahead)
        if not events:
            st.sidebar.warning("No events found in Calendar. Switched to Demo Outing.")
            data_source = "Demo Outing (Movie -> Date -> Shopping)"
    except Exception as e:
        st.sidebar.error(f"Calendar Sync Error: {e}")
        data_source = "Demo Outing (Movie -> Date -> Shopping)"

if data_source == "Demo Outing (Movie -> Date -> Shopping)":
    now = datetime.now(timezone.utc)
    events = [
        CalendarEvent(title="movie", start_time=now + timedelta(hours=2), location_raw="P&M Mall, Bistupur, Jamshedpur"),
        CalendarEvent(title="date in restaurant", start_time=now + timedelta(hours=5), location_raw="Novelty Restaurant, Bistupur, Jamshedpur"),
        CalendarEvent(title="shopping in mall", start_time=now + timedelta(hours=7, minutes=30), location_raw="Zudio, Kadma, Jamshedpur")
    ]

curr_origin_coords = base_coords
curr_origin_name = "Hostel / Base"
prev_end_time = None

legs = []
with st.spinner("Processing routes, traffic, and Laya decisions..."):
    for ev in events:
        if not ev.location_raw:
            continue

        dest_coords = resolve_location(ev.location_raw)
        if not dest_coords:
            continue

        t_min, t_exp, t_max = estimate_event_duration(ev.title)
        current_end_time = ev.start_time + timedelta(minutes=t_exp)

        condition = None
        if prev_end_time:
            gap = (ev.start_time - prev_end_time).total_seconds() / 60.0
            if gap <= 120:
                pass
            elif gap <= 240:
                condition = f"Chained from {curr_origin_name} (Gap: {int(gap)} mins)"
            else:
                curr_origin_coords = base_coords
                curr_origin_name = "Hostel / Base"
        else:
            curr_origin_coords = base_coords
            curr_origin_name = "Hostel / Base"

        weather = fetch_weather(dest_coords)
        routes = {
            "walk": calculate_route(curr_origin_coords, dest_coords, mode="walk"),
            "bike": calculate_route(curr_origin_coords, dest_coords, mode="bike"),
            "cab": calculate_route(curr_origin_coords, dest_coords, mode="cab")
        }

        plan = evaluate_commute_decision(ev, weather, routes)
        plan.predicted_duration_minutes = t_exp

        legs.append({
            "event": ev, "origin_name": curr_origin_name, "origin_coords": curr_origin_coords,
            "dest_coords": dest_coords, "weather": weather, "plan": plan,
            "duration_range": (t_min, t_max), "condition": condition
        })

        curr_origin_coords = dest_coords
        curr_origin_name = ev.title
        prev_end_time = current_end_time

st.subheader(f"Chained Itinerary Legs ({len(legs)})")

for idx, leg in enumerate(legs, 1):
    ev, plan, w = leg["event"], leg["plan"], leg["weather"]
    tz = get_tz(leg["origin_coords"])

    start_local = ev.start_time.astimezone(tz)
    depart_local = plan.departure_time.astimezone(tz)
    icon = {"walk": "🚶", "bike": "🛵", "cab": "🚕", "car": "🚗"}.get(plan.chosen_mode, "🚗")

    with st.expander(f"**Leg {idx}: {ev.title.upper()}** — Depart: **{depart_local.strftime('%I:%M %p')}** via {icon} {plan.chosen_mode.upper()}", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Scheduled Start", start_local.strftime("%I:%M %p"))
        col2.metric("Recommended Departure", depart_local.strftime("%I:%M %p"))
        col3.metric("Transit Time", f"{plan.total_travel_minutes} mins")
        col4.metric("Safety Buffer", f"{plan.safety_buffer_minutes} mins")

        st.markdown(f"**Route:** `{leg['origin_name']}` $\\rightarrow$ `{ev.location_raw}`")
        if leg["condition"]:
            st.caption(f"ℹ️ *{leg['condition']}*")

        st.markdown(f"**Predicted Commitment:** `{plan.predicted_duration_minutes} mins` (Range: `{leg['duration_range'][0]}` - `{leg['duration_range'][1]}` mins)")
        if w:
            st.markdown(f"**Weather:** `{w.temperature_celsius}°C` (Feels `{w.apparent_temperature_celsius}°C`) | Rain Probability: `{w.precipitation_probability}%`")

        st.markdown("**Laya Decision Factors:**")
        for r in plan.reasoning:
            st.markdown(f"- {r}")