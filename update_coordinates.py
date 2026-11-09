import sqlite3
import requests
import time

conn = sqlite3.connect("safezone.db")
cursor = conn.cursor()

cursor.execute("""
    SELECT id, area FROM crimes
    WHERE latitude IS NULL OR longitude IS NULL
""")

records = cursor.fetchall()

for record_id, area in records:
    print("Searching:", area)

    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": ("Howrah" if area.lower() == "howrha" else area) + ", West Bengal, India",
                "format": "json",
                "limit": 1
            },
            headers={
                "User-Agent": "SafeZoneCrimeAnalyzer/1.0"
            },
            timeout=15
        )

        response.raise_for_status()
        results = response.json()

        if results:
            lat = float(results[0]["lat"])
            lon = float(results[0]["lon"])

            cursor.execute("""
                UPDATE crimes
                SET latitude = ?, longitude = ?
                WHERE id = ?
            """, (lat, lon, record_id))

            conn.commit()
            print("Updated:", area)
        else:
            print("Not found:", area)

    except requests.RequestException as error:
        print("Error:", error)

    time.sleep(1)

conn.close()
print("Finished!")