import os
from dotenv import load_dotenv
from schemas import Coordinates
from calendar_sync import get_upcoming_events
from geocoder import resolve_location
from weather_client import fetch_weather
from traffic_client import calculate_route
from jev_engine import evaluate_commute_decision

load_dotenv()
ORIGIN_LAT = float(os.getenv("DEFAULT_ORIGIN_LAT", "22.7770"))
ORIGIN_LON = float(os.getenv("DEFAULT_ORIGIN_LON", "86.1441"))

def run_commute_guardian() :
    origin = Coordinates(latitude=ORIGIN_LAT, longitude=ORIGIN_LON)
    events = get_upcoming_events(lookahead_hours=24)
    if not events:
        return None
    
    for event in events:
        print(f"Processing Event: {event.title}")
        print(f"Scheduled Time:   {event.start_time}")
        print(f"Raw Location:     {event.location_raw}")
        
        if not event.location_raw:
            print("No physical location specified. Skipping commute planning.\n")
            continue
        
        destination = resolve_location(event.location_raw)
        
        if not destination:
            print(f"Could not geocode destination: {event.location_raw}\n")
            continue

        print(f"Destination: ({destination.latitude}, {destination.longitude}) [Cached: {destination.cached}]")

        weather = fetch_weather(destination)
        if not weather:
            print("Failed to fetch weather data.\n")
            continue

        print(f"Weather: {weather.temperature_celsius}°C | Rain Risk: {weather.precipitation_probability}%")

        candidate_routes = {
            "walk": calculate_route(origin, destination, mode="walk"),
            "bike": calculate_route(origin, destination, mode="bike"),
            "cab": calculate_route(origin, destination, mode="cab")
        }

        plan = evaluate_commute_decision(
            event=event,
            weather=weather,
            routes=candidate_routes
        )

        print(f"Recommended Mode:  {plan.chosen_mode.upper()}")
        print(f"Departure Time:    {plan.departure_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"Estimated Travel:  {plan.total_travel_minutes} mins")
        print(f"Safety Buffer:     {plan.safety_buffer_minutes} mins")
        print("Decision Factors:")
        for reason in plan.reasoning:
            print(f"  * {reason}")

if __name__ == "__main__":
    run_commute_guardian()