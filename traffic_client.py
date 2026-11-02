import httpx
from schemas import Coordinates, RouteDetails
from dotenv import load_dotenv
import os
from typing import Optional

load_dotenv()
TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY")
MODE_MAPPING = {
    "walk": "pedestrian",
    "bike": "motorcycle",
    "cab": "car",
    "car": "car"
}

def calculate_route(origin : Coordinates, destination : Coordinates, mode : str = "car") -> Optional[RouteDetails] :
    if not origin or not destination or not TOMTOM_API_KEY :
        return None
    
    locations_str = f"{origin.latitude},{origin.longitude}:{destination.latitude},{destination.longitude}"
    url = f"https://api.tomtom.com/routing/1/calculateRoute/{locations_str}/json"
    mode = MODE_MAPPING.get(mode.lower(), "car")
    
    params = {
        "key" : TOMTOM_API_KEY,
        "traffic" : True,
        "travelMode" : mode,
        "departAt": "now",
        "computeTravelTimeFor": "all"
    }
    
    try:
        response = httpx.get(url = url, params = params, timeout = 10.0)
        response.raise_for_status()
        data = response.json()
        routes = data.get("routes", [])
        if not routes : 
            return None
        summary = routes[0]["summary"]
        length_meters = summary.get("lengthInMeters", 0)
        travel_time_seconds = summary.get("travelTimeInSeconds", 0)
        traffic_delay_seconds = summary.get("trafficDelayInSeconds", 0)
        distance_km = round(length_meters / 1000.0, 2)
        travel_time_minutes = round(travel_time_seconds / 60.0, 1)
        traffic_delay_minutes = round(traffic_delay_seconds / 60.0, 1)
        return RouteDetails(
            distance_km=distance_km,
            travel_time_minutes=travel_time_minutes,
            traffic_delay_minutes=traffic_delay_minutes,
            has_heavy_traffic=traffic_delay_minutes >= 10.0
        )
    
    except Exception:
        return None
    
if __name__ == "__main__":
    origin_coords = Coordinates(latitude=22.7770, longitude=86.1441)
    dest_coords = Coordinates(latitude=22.7848, longitude=86.1794)

    print("Cab route:", calculate_route(origin_coords, dest_coords, mode="cab"))
    print("Bike route:", calculate_route(origin_coords, dest_coords, mode="bike"))
    print("Walking route:", calculate_route(origin_coords, dest_coords, mode="walk"))