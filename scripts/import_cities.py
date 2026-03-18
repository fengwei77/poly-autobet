"""
Import cities from worldcities.csv into the database.
"""
import csv
import sqlite3
import re
from pathlib import Path

# Country to timezone mapping
COUNTRY_TIMEZONE = {
    "US": "America/New_York",
    "CA": "America/Toronto",
    "MX": "America/Mexico_City",
    "GB": "Europe/London",
    "FR": "Europe/Paris",
    "DE": "Europe/Berlin",
    "IT": "Europe/Rome",
    "ES": "Europe/Madrid",
    "PT": "Europe/Lisbon",
    "NL": "Europe/Amsterdam",
    "BE": "Europe/Brussels",
    "AT": "Europe/Vienna",
    "CH": "Europe/Zurich",
    "SE": "Europe/Stockholm",
    "NO": "Europe/Oslo",
    "DK": "Europe/Copenhagen",
    "FI": "Europe/Helsinki",
    "IE": "Europe/Dublin",
    "PL": "Europe/Warsaw",
    "CZ": "Europe/Prague",
    "HU": "Europe/Budapest",
    "GR": "Europe/Athens",
    "RO": "Europe/Bucharest",
    "BG": "Europe/Sofia",
    "RS": "Europe/Belgrade",
    "HR": "Europe/Zagreb",
    "SI": "Europe/Ljubljana",
    "SK": "Europe/Bratislava",
    "UA": "Europe/Kiev",
    "RU": "Europe/Moscow",
    "TR": "Europe/Istanbul",
    "JP": "Asia/Tokyo",
    "KR": "Asia/Seoul",
    "CN": "Asia/Shanghai",
    "HK": "Asia/Hong_Kong",
    "TW": "Asia/Taipei",
    "SG": "Asia/Singapore",
    "MY": "Asia/Kuala_Lumpur",
    "TH": "Asia/Bangkok",
    "ID": "Asia/Jakarta",
    "PH": "Asia/Manila",
    "VN": "Asia/Ho_Chi_Minh",
    "IN": "Asia/Kolkata",
    "PK": "Asia/Karachi",
    "BD": "Asia/Dhaka",
    "AE": "Asia/Dubai",
    "SA": "Asia/Riyadh",
    "QA": "Asia/Qatar",
    "KW": "Asia/Kuwait",
    "IL": "Asia/Jerusalem",
    "JO": "Asia/Amman",
    "LB": "Asia/Beirut",
    "EG": "Africa/Cairo",
    "ZA": "Africa/Johannesburg",
    "NG": "Africa/Lagos",
    "KE": "Africa/Nairobi",
    "MA": "Africa/Casablanca",
    "TN": "Africa/Tunis",
    "GH": "Africa/Accra",
    "ET": "Africa/Addis_Ababa",
    "AU": "Australia/Sydney",
    "NZ": "Pacific/Auckland",
    "AR": "America/Argentina/Buenos_Aires",
    "BR": "America/Sao_Paulo",
    "CL": "America/Santiago",
    "CO": "America/Bogota",
    "PE": "America/Lima",
    "VE": "America/Caracas",
    "EC": "America/Guayaquil",
    "UY": "America/Montevideo",
    "PY": "America/Asuncion",
    "BO": "America/La_Paz",
    "CR": "America/Costa_Rica",
    "PA": "America/Panama",
    "GT": "America/Guatemala",
    "HN": "America/Tegucigalpa",
    "SV": "America/El_Salvador",
    "NI": "America/Managua",
    "DO": "America/Santo_Domingo",
    "CU": "America/Havana",
    "JM": "America/Jamaica",
    "PR": "America/Puerto_Rico",
    "BS": "America/Nassau",
}

# Major cities that should be tracked (high volume Polymarket markets)
MAJOR_CITIES = {
    # US
    "new_york", "los_angeles", "chicago", "miami", "houston", "phoenix",
    "philadelphia", "san_antonio", "san_diego", "dallas", "austin",
    "san_francisco", "seattle", "denver", "washington_dc", "boston",
    "atlanta", "detroit", "minneapolis", "portland", "las_vegas",
    "nashville", "baltimore", "tampa", "orlando", "salt_lake_city",
    # Canada
    "toronto", "vancouver", "montreal", "calgary", "ottawa", "edmonton", "winnipeg",
    # Europe
    "london", "paris", "berlin", "madrid", "barcelona", "rome", "milan",
    "amsterdam", "vienna", "zurich", "munich", "frankfurt", "hamburg",
    "lisbon", "porto", "dublin", "brussels", "stockholm", "oslo",
    "copenhagen", "helsinki", "reykjavik", "warsaw", "krakow", "prague",
    "budapest", "athens", "istanbul", "moscow", "saint_petersburg",
    # Ukraine
    "kyiv", "kiev", "kharkiv", "odessa", "dnipro", "lviv",
    # Asia
    "tokyo", "osaka", "kyoto", "seoul", "shanghai", "beijing", "guangzhou",
    "shenzhen", "hong_kong", "taipei", "singapore", "kuala_lumpur",
    "bangkok", "jakarta", "manila", "mumbai", "delhi", "bangalore",
    "dubai", "abu_dhabi", "doha", "riyadh", "tel_aviv",
    # Australia
    "sydney", "melbourne", "brisbane", "perth", "auckland",
    # Africa
    "cairo", "cape_town", "johannesburg", "lagos", "nairobi", "casablanca",
    # Latin America
    "mexico_city", "guadalajara", "monterrey", "bogota", "sao_paulo",
    "rio_de_janeiro", "buenos_aires", "santiago", "lima", "caracas",
}


def normalize_city_name(name: str) -> str:
    """Convert city name to normalized city_id."""
    # Remove accents and special chars
    name = name.lower()
    name = re.sub(r"[^\w\s]", "", name)
    name = re.sub(r"\s+", "_", name)
    return name


def get_timezone(iso2: str) -> str:
    """Get timezone for country code."""
    return COUNTRY_TIMEZONE.get(iso2, "UTC")


def import_cities(db_path: str, csv_path: str):
    """Import cities from CSV to database."""
    conn = sqlite3.connect(db_path)

    # Clear existing cities
    conn.execute("DELETE FROM cities")
    print("Cleared existing cities table")

    # Read CSV
    cities_to_insert = []
    seen = set()

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            city_ascii = row["city_ascii"]
            if not city_ascii:
                continue

            # Create normalized city_id
            city_id = normalize_city_name(city_ascii)

            # Skip duplicates (keep first occurrence)
            if city_id in seen:
                continue
            seen.add(city_id)

            # Determine if tracked
            is_tracked = city_id in MAJOR_CITIES or row.get("capital") in ["primary", "admin"]

            # Get timezone
            iso2 = row.get("iso2", "")
            timezone = get_timezone(iso2)

            cities_to_insert.append((
                city_id,
                city_ascii,
                row["lat"],
                row["lng"],
                iso2,
                timezone,
                1 if is_tracked else 0,
            ))

    # Insert in batches
    batch_size = 1000
    for i in range(0, len(cities_to_insert), batch_size):
        batch = cities_to_insert[i:i+batch_size]
        conn.executemany("""
            INSERT OR IGNORE INTO cities (city_id, name, lat, lon, country_code, timezone, is_tracked)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, batch)
        print(f"Inserted {min(i+batch_size, len(cities_to_insert))}/{len(cities_to_insert)} cities")

    conn.commit()

    # Verify
    cursor = conn.execute("SELECT COUNT(*) FROM cities")
    total = cursor.fetchone()[0]
    cursor = conn.execute("SELECT COUNT(*) FROM cities WHERE is_tracked = 1")
    tracked = cursor.fetchone()[0]

    print(f"\nTotal cities: {total}")
    print(f"Tracked cities: {tracked}")

    # Show some examples
    cursor = conn.execute("SELECT city_id, name, country_code FROM cities WHERE country_code = 'UA' LIMIT 10")
    print(f"\nUkrainian cities: {cursor.fetchall()}")

    conn.close()


if __name__ == "__main__":
    import sys
    db_path = sys.argv[1] if len(sys.argv) > 1 else "/app/db/polybet.db"
    csv_path = sys.argv[2] if len(sys.argv) > 2 else "/app/worldcities.csv"
    import_cities(db_path, csv_path)
