from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Dict
from schemas import WeatherSnapshot, RouteDetails, CalendarEvent, CommutePlan
from preference_retriever import PreferenceRetriever
import os
import laya

agent = laya.load("convaiinnovations/laya")
retriever = PreferenceRetriever()

def format_routes_summary(routes : Dict[str, Optional[RouteDetails]]) -> Dict[str, dict] :
    summary = {}
    for mode, route in routes.items():
        if route :
            summary[mode] = {
                "distance_km": route.distance_km,
                "travel_time_minutes": route.travel_time_minutes,
                "traffic_delay_minutes": route.traffic_delay_minutes,
                "has_heavy_traffic": route.has_heavy_traffic
            }
    return summary


def evaluate_commute_decision(
    event : CalendarEvent,
    weather : WeatherSnapshot,
    routes : Dict[str, Optional[RouteDetails]]
) -> CommutePlan :
    query = (
        f"Event: {event.title}. "
        f"Rain probability: {weather.precipitation_probability}%. "
        f"Currently raining: {weather.is_raining}. "
        f"Temperature: {weather.apparent_temperature_celsius}C."
    )
    retrieved_docs = retriever.retrieve(query)
    user_rules = [d.page_content for d in retrieved_docs]
    
    state = {
        "event" : {
            "title" : event.title,
            "start_time" : event.start_time.strftime("%Y-%m-%d %H:%M"),
            "location" : event.location_raw
        },
        "weather" : {
            "temperature_celsius": weather.temperature_celsius,
            "apparent_temperature_celsius": weather.apparent_temperature_celsius,
            "precipitation_probability": weather.precipitation_probability,
            "is_raining": weather.is_raining
        },
        "candidate_routes" : format_routes_summary(routes),
        "preference_rules" : user_rules
    }
    
    questions = {
        "urgency": {
            "type": "score",
            "instructions": "Rate the criticality and urgency of attending this event on time.",
            "criteria": [
                "casual flexible leisure or errand",
                "routine standard scheduled activity",
                "high-stakes critical deadline exam or interview"
            ]
        },
        "transport_mode": {
            "type": "choice",
            "instructions": "Select the optimal transport mode according strictly to weather friction and physical distance limits.",
            "criteria": {
                "walk": "Distance is under 1.5 km and no rain",
                "bike": "Distance is between 1.5 km and 8 km and no rain",
                "cab": "Distance exceeds 8 km, rain probability 30% or higher, or extreme weather"
            }
        }
    }
    
    result = agent.predict(state, questions)
    answers = result["answers"]
    
    urgency_raw = answers["urgency"]["score"]
    urgency_score = int(round((urgency_raw / 3.0)* 10))
    urgency_score = max(1, min(10, urgency_score))
    
    if urgency_score >= 8:
        buffer_minutes = 45
    elif urgency_score >= 5:
        buffer_minutes = 20
    else:
        buffer_minutes = 10
        
    mode_answer = answers["transport_mode"]
    chosen_mode = mode_answer["choice"].lower()
    mode_confidence = mode_answer.get("confidence", 1.0)
    mode_prob = mode_answer.get("probabilities", {}).get(chosen_mode, 1.0)
    
    selected_route = routes.get(chosen_mode)
    travel_time = selected_route.travel_time_minutes if selected_route else 0.0
    total_time_needed = travel_time + buffer_minutes
    departure_time = event.start_time - timedelta(minutes=total_time_needed)
    
    reasons = [
        f"Laya Urgency Score: {urgency_score}/10 (Expected: {urgency_raw:.2f})",
        f"Allocated Safety Buffer: {buffer_minutes} mins",
        f"Selected Mode: {chosen_mode.upper()} (Confidence: {mode_confidence:.2f}, Probability: {mode_prob:.2f})"
    ]
    
    return CommutePlan(
        chosen_mode=chosen_mode,
        departure_time=departure_time,
        safety_buffer_minutes=buffer_minutes,
        total_travel_minutes=travel_time,
        reasoning=reasons
    )
    
if __name__ == "__main__" :
    from datetime import datetime, timezone
    from schemas import Coordinates
    from traffic_client import calculate_route

    test_event = CalendarEvent(
        title="movie",
        start_time=datetime.now(timezone.utc) + timedelta(hours=3),
        location_raw="P&M Mall, Bistupur"
    )

    test_weather = WeatherSnapshot(
        temperature_celsius=26.5,
        apparent_temperature_celsius=27.2,
        precipitation_probability=0,
        wind_speed_kmh=4.0,
        is_raining=False
    )

    origin_coords = Coordinates(latitude=22.7770, longitude=86.1441)
    dest_coords = Coordinates(latitude=22.7848, longitude=86.1794)

    test_routes = {
        "walk": calculate_route(origin_coords, dest_coords, mode="walk"),
        "bike": calculate_route(origin_coords, dest_coords, mode="bike"),
        "cab": calculate_route(origin_coords, dest_coords, mode="cab")
    }

    plan = evaluate_commute_decision(test_event, test_weather, test_routes)

    print("\nMode:", plan.chosen_mode)
    print("Departure Time:", plan.departure_time)
    print("Travel Time:", plan.total_travel_minutes)
    print("Buffer:", plan.safety_buffer_minutes)
    print("Reasoning:")
    for r in plan.reasoning:
        print(" -", r)