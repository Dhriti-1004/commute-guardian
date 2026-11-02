import sqlite3
import httpx
import os
from typing import Optional
from dotenv import load_dotenv
from schemas import Coordinates

load_dotenv()
DB_NAME = "addresses.db"
TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY")

def init_db():
    with sqlite3.connect(DB_NAME) as conn :
        conn.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                raw_address TEXT UNIQUE,
                latitude REAL,
                longitude REAL
            )                     
         """)
        
def resolve_location(address_str : str) -> Optional[Coordinates]:
    if not address_str :
        return None
    clean_name = address_str.lower().strip()
    init_db()
    
    with sqlite3.connect(DB_NAME) as conn :
        cursor = conn.cursor()
        cursor.execute("SELECT latitude, longitude FROM locations WHERE raw_address = ?", (clean_name,))
        row = cursor.fetchone()
        if row :
            return Coordinates(latitude=row[0], longitude=row[1], cached = True)
        
    url = f"https://api.tomtom.com/search/2/search/{address_str}.json"
    params = {"key" : TOMTOM_API_KEY, "limit" : 1}
    
    try :
        response = httpx.get(
            url,
            params=params,
            timeout=10.0
        )
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        
        if not data:
            return None
        
        position = results[0]["position"]
        lat, lon = float(position["lat"]), float(position["lon"])
        
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO locations (raw_address, latitude, longitude) VALUES (?, ?, ?)",
                (clean_name, lat, lon)
            )
            
        return Coordinates(latitude=lat, longitude=lon, cached = False) 
    
    except Exception:
        return None
    
if __name__ == "__main__" :
    test_loc = "Zudio, near Little Italy Restaurant, Kadma Road, Jamshedpur 831014"
    
    print(resolve_location(test_loc))
    print(resolve_location(test_loc))