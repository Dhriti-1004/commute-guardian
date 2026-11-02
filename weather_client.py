import httpx
from typing import Optional
from schemas import Coordinates, WeatherSnapshot

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

def fetch_weather(coords : Coordinates) -> Optional[WeatherSnapshot] :
    if not coords: 
        return None
    params = {
        "latitude" : coords.latitude,
        "longitude" : coords.longitude,
        "current" : [
            "temperature_2m",
            "apparent_temperature",
            "precipitation",
            "wind_speed_10m"
        ],
        "hourly" : ["precipitation_probability"],
        "forecast_hours" : 1,
        "timezone" : "auto"
    }
    
    try :
        response = httpx.get(OPEN_METEO_URL, params=params, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        current = data.get("current", {})
        hourly = data.get("hourly", {})
        
        rain_prob = 0
        if "precipitation_probability" in hourly and hourly["precipitation_probability"]:
            rain_prob = int(hourly["precipitation_probability"][0])
            
        current_precipitation = float(current.get("precipitation", 0.0))
        
        return WeatherSnapshot(
            temperature_celsius=float(current.get("temperature_2m", 0.0)),
            apparent_temperature_celsius=float(current.get("apparent_temperature", 0.0)),
            precipitation_probability=rain_prob,
            wind_speed_kmh=float(current.get("wind_speed_10m", 0.0)),
            is_raining=current_precipitation > 0.3
        )
    except Exception as e :
        print(f"{e}")
        return None
    
if __name__ == "__main__" :
    test_coords = Coordinates(latitude=22.8028, longitude=86.1854)
    weather = fetch_weather(test_coords)
    print(weather)