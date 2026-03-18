"""Add global cities table with worldwide city data

Revision ID: 002_add_cities
Revises: 001_initial
Create Date: 2026-03-18

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_add_cities'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# All cities data - global coverage for Polymarket weather market recognition
CITIES_DATA = [
    # === UNITED STATES ===
    ("new_york", "New York", 40.7128, -74.0060, "US", "America/New_York", True),
    ("los_angeles", "Los Angeles", 34.0522, -118.2437, "US", "America/Los_Angeles", True),
    ("chicago", "Chicago", 41.8781, -87.6298, "US", "America/Chicago", True),
    ("miami", "Miami", 25.7617, -80.1918, "US", "America/New_York", True),
    ("houston", "Houston", 29.7604, -95.3698, "US", "America/Chicago", True),
    ("phoenix", "Phoenix", 33.4484, -112.0740, "US", "America/Phoenix", True),
    ("philadelphia", "Philadelphia", 39.9526, -75.1652, "US", "America/New_York", True),
    ("san_antonio", "San Antonio", 29.4241, -98.4936, "US", "America/Chicago", False),
    ("san_diego", "San Diego", 32.7157, -117.1611, "US", "America/Los_Angeles", False),
    ("dallas", "Dallas", 32.7767, -96.7970, "US", "America/Chicago", True),
    ("austin", "Austin", 30.2672, -97.7431, "US", "America/Chicago", True),
    ("san_francisco", "San Francisco", 37.7749, -122.4194, "US", "America/Los_Angeles", True),
    ("seattle", "Seattle", 47.6062, -122.3321, "US", "America/Los_Angeles", True),
    ("denver", "Denver", 39.7392, -104.9903, "US", "America/Denver", True),
    ("washington_dc", "Washington DC", 38.9072, -77.0369, "US", "America/New_York", True),
    ("boston", "Boston", 42.3601, -71.0589, "US", "America/New_York", True),
    ("atlanta", "Atlanta", 33.7490, -84.3880, "US", "America/New_York", True),
    ("detroit", "Detroit", 42.3314, -83.0458, "US", "America/Detroit", False),
    ("minneapolis", "Minneapolis", 44.9778, -93.2650, "US", "America/Chicago", False),
    ("portland", "Portland", 45.5152, -122.6784, "US", "America/Los_Angeles", True),
    ("las_vegas", "Las Vegas", 36.1699, -115.1398, "US", "America/Los_Angeles", True),
    ("nashville", "Nashville", 36.1627, -86.7816, "US", "America/Chicago", False),
    ("baltimore", "Baltimore", 39.2904, -76.6122, "US", "America/New_York", False),
    ("tampa", "Tampa", 27.9506, -82.4572, "US", "America/New_York", False),
    ("orlando", "Orlando", 28.5383, -81.3792, "US", "America/New_York", False),
    ("salt_lake_city", "Salt Lake City", 40.7608, -111.8910, "US", "America/Denver", False),

    # === CANADA ===
    ("toronto", "Toronto", 43.6532, -79.3832, "CA", "America/Toronto", True),
    ("vancouver", "Vancouver", 49.2827, -123.1207, "CA", "America/Vancouver", True),
    ("montreal", "Montreal", 45.5017, -73.5673, "CA", "America/Montreal", True),
    ("calgary", "Calgary", 51.0447, -114.0719, "CA", "America/Edmonton", False),
    ("ottawa", "Ottawa", 45.4215, -75.6972, "CA", "America/Toronto", False),
    ("edmonton", "Edmonton", 53.5461, -113.4938, "CA", "America/Edmonton", False),
    ("winnipeg", "Winnipeg", 49.8951, -97.1384, "CA", "America/Winnipeg", False),

    # === WESTERN EUROPE ===
    ("london", "London", 51.5074, -0.1278, "GB", "Europe/London", True),
    ("paris", "Paris", 48.8566, 2.3522, "FR", "Europe/Paris", True),
    ("berlin", "Berlin", 52.5200, 13.4050, "DE", "Europe/Berlin", True),
    ("madrid", "Madrid", 40.4168, -3.7038, "ES", "Europe/Madrid", True),
    ("barcelona", "Barcelona", 41.3851, 2.1734, "ES", "Europe/Madrid", True),
    ("rome", "Rome", 41.9028, 12.4964, "IT", "Europe/Rome", True),
    ("milan", "Milan", 45.4642, 9.1900, "IT", "Europe/Rome", True),
    ("naples", "Naples", 40.8518, 14.2681, "IT", "Europe/Rome", False),
    ("amsterdam", "Amsterdam", 52.3676, 4.9041, "NL", "Europe/Amsterdam", True),
    ("vienna", "Vienna", 48.2082, 16.3738, "AT", "Europe/Vienna", True),
    ("zurich", "Zurich", 47.3769, 8.5417, "CH", "Europe/Zurich", True),
    ("geneva", "Geneva", 46.2044, 6.1432, "CH", "Europe/Zurich", False),
    ("munich", "Munich", 48.1351, 11.5820, "DE", "Europe/Berlin", True),
    ("frankfurt", "Frankfurt", 50.1109, 8.6821, "DE", "Europe/Berlin", False),
    ("hamburg", "Hamburg", 53.5511, 9.9937, "DE", "Europe/Berlin", False),
    ("cologne", "Cologne", 50.9375, 6.9603, "DE", "Europe/Berlin", False),
    ("lisbon", "Lisbon", 38.7223, -9.1393, "PT", "Europe/Lisbon", True),
    ("porto", "Porto", 41.1579, -8.6291, "PT", "Europe/Lisbon", False),
    ("dublin", "Dublin", 53.3498, -6.2603, "IE", "Europe/Dublin", True),
    ("brussels", "Brussels", 50.8503, 4.3517, "BE", "Europe/Brussels", False),

    # === NORDIC ===
    ("stockholm", "Stockholm", 59.3293, 18.0686, "SE", "Europe/Stockholm", True),
    ("oslo", "Oslo", 59.9139, 10.7522, "NO", "Europe/Oslo", True),
    ("copenhagen", "Copenhagen", 55.6761, 12.5683, "DK", "Europe/Copenhagen", True),
    ("helsinki", "Helsinki", 60.1699, 24.9384, "FI", "Europe/Helsinki", True),
    ("reykjavik", "Reykjavik", 64.1466, -21.9426, "IS", "Atlantic/Reykjavik", False),

    # === CENTRAL & EASTERN EUROPE ===
    ("warsaw", "Warsaw", 52.2297, 21.0122, "PL", "Europe/Warsaw", True),
    ("krakow", "Krakow", 50.0647, 19.9450, "PL", "Europe/Warsaw", False),
    ("prague", "Prague", 50.0755, 14.4378, "CZ", "Europe/Prague", True),
    ("budapest", "Budapest", 47.4979, 19.0402, "HU", "Europe/Budapest", True),
    ("athens", "Athens", 37.9838, 23.7275, "GR", "Europe/Athens", True),
    ("istanbul", "Istanbul", 41.0082, 28.9784, "TR", "Europe/Istanbul", True),
    ("moscow", "Moscow", 55.7558, 37.6173, "RU", "Europe/Moscow", True),
    ("saint_petersburg", "Saint Petersburg", 59.9311, 30.3609, "RU", "Europe/Moscow", True),
    ("kazan", "Kazan", 55.8304, 49.0661, "RU", "Europe/Moscow", False),
    ("sochi", "Sochi", 43.5992, 39.7257, "RU", "Europe/Moscow", False),

    # === UKRAINE ===
    ("kyiv", "Kyiv", 50.4501, 30.5234, "UA", "Europe/Kiev", True),
    ("kiev", "Kyiv", 50.4501, 30.5234, "UA", "Europe/Kiev", True),
    ("kharkiv", "Kharkiv", 49.9935, 36.2304, "UA", "Europe/Kiev", False),
    ("odessa", "Odessa", 46.4825, 30.7233, "UA", "Europe/Kiev", False),
    ("dnipro", "Dnipro", 48.4647, 35.0462, "UA", "Europe/Kiev", False),
    ("lviv", "Lviv", 49.8397, 24.0297, "UA", "Europe/Kiev", False),
    ("zaporizhzhia", "Zaporizhzhia", 47.8388, 35.1396, "UA", "Europe/Kiev", False),
    ("kryvyi_rih", "Kryvyi Rih", 47.9102, 33.3916, "UA", "Europe/Kiev", False),
    ("mykolaiv", "Mykolaiv", 46.9759, 31.9956, "UA", "Europe/Kiev", False),
    ("vinnytsia", "Vinnytsia", 49.2331, 28.4682, "UA", "Europe/Kiev", False),
    ("poltava", "Poltava", 49.5883, 34.5514, "UA", "Europe/Kiev", False),
    ("chernihiv", "Chernihiv", 51.4982, 31.3274, "UA", "Europe/Kiev", False),
    ("zhytomyr", "Zhytomyr", 50.2547, 28.6586, "UA", "Europe/Kiev", False),
    ("sumy", "Sumy", 50.9077, 34.7996, "UA", "Europe/Kiev", False),
    ("kropyvnytskyi", "Kropyvnytskyi", 48.5091, 32.2646, "UA", "Europe/Kiev", False),
    ("rivne", "Rivne", 50.6233, 26.2270, "UA", "Europe/Kiev", False),
    ("ternopil", "Ternopil", 49.5539, 25.5948, "UA", "Europe/Kiev", False),
    ("lutsk", "Lutsk", 50.7472, 25.3253, "UA", "Europe/Kiev", False),
    ("uzhhorod", "Uzhhorod", 48.6208, 22.2878, "UA", "Europe/Kiev", False),
    ("ivano_frankivsk", "Ivano-Frankivsk", 48.9227, 24.7111, "UA", "Europe/Kiev", False),
    ("kherson", "Kherson", 46.6425, 32.6247, "UA", "Europe/Kiev", False),
    ("cherkasy", "Cherkasy", 49.4285, 32.0621, "UA", "Europe/Kiev", False),
    ("khmelnytskyi", "Khmelnytskyi", 49.4229, 26.9966, "UA", "Europe/Kiev", False),
    ("rodynske", "Rodynske", 48.0333, 36.2833, "UA", "Europe/Kiev", False),

    # === OTHER EASTERN EUROPE ===
    ("bucharest", "Bucharest", 44.4268, 26.1025, "RO", "Europe/Bucharest", True),
    ("sofia", "Sofia", 42.6977, 23.3219, "BG", "Europe/Sofia", True),
    ("belgrade", "Belgrade", 44.7866, 20.4489, "RS", "Europe/Belgrade", True),
    ("zagreb", "Zagreb", 45.8150, 15.9819, "HR", "Europe/Zagreb", True),
    ("ljubljana", "Ljubljana", 46.0569, 14.5058, "SI", "Europe/Ljubljana", True),
    ("tallinn", "Tallinn", 59.4370, 24.7536, "EE", "Europe/Tallinn", True),
    ("riga", "Riga", 56.9496, 24.1052, "LV", "Europe/Riga", True),
    ("vilnius", "Vilnius", 54.6872, 25.2797, "LT", "Europe/Vilnius", True),
    ("minsk", "Minsk", 53.9006, 27.5590, "BY", "Europe/Minsk", False),

    # === ASIA - EAST ===
    ("tokyo", "Tokyo", 35.6762, 139.6503, "JP", "Asia/Tokyo", True),
    ("osaka", "Osaka", 34.6937, 135.5023, "JP", "Asia/Tokyo", True),
    ("kyoto", "Kyoto", 35.0116, 135.7681, "JP", "Asia/Tokyo", False),
    ("yokohama", "Yokohama", 35.4437, 139.6380, "JP", "Asia/Tokyo", False),
    ("nagoya", "Nagoya", 35.1815, 136.9066, "JP", "Asia/Tokyo", False),
    ("sapporo", "Sapporo", 43.0618, 141.3545, "JP", "Asia/Tokyo", False),
    ("seoul", "Seoul", 37.5665, 126.9780, "KR", "Asia/Seoul", True),
    ("busan", "Busan", 35.1796, 129.0756, "KR", "Asia/Seoul", False),
    ("shanghai", "Shanghai", 31.2304, 121.4737, "CN", "Asia/Shanghai", True),
    ("beijing", "Beijing", 39.9042, 116.4074, "CN", "Asia/Shanghai", True),
    ("guangzhou", "Guangzhou", 23.1291, 113.2644, "CN", "Asia/Shanghai", False),
    ("shenzhen", "Shenzhen", 22.5431, 114.0579, "CN", "Asia/Shanghai", False),
    ("chengdu", "Chengdu", 30.5728, 104.0668, "CN", "Asia/Shanghai", False),
    ("hong_kong", "Hong Kong", 22.3193, 114.1694, "HK", "Asia/Hong_Kong", True),
    ("taipei", "Taipei", 25.0330, 121.5654, "TW", "Asia/Taipei", True),

    # === ASIA - SOUTH & SOUTHEAST ===
    ("mumbai", "Mumbai", 19.0760, 72.8777, "IN", "Asia/Kolkata", True),
    ("delhi", "Delhi", 28.7041, 77.1025, "IN", "Asia/Kolkata", True),
    ("bangalore", "Bangalore", 12.9716, 77.5946, "IN", "Asia/Kolkata", False),
    ("kolkata", "Kolkata", 22.5726, 88.3639, "IN", "Asia/Kolkata", False),
    ("chennai", "Chennai", 13.0827, 80.2707, "IN", "Asia/Kolkata", False),
    ("hyderabad", "Hyderabad", 17.3850, 78.4867, "IN", "Asia/Kolkata", False),
    ("karachi", "Karachi", 24.8607, 67.0011, "PK", "Asia/Karachi", False),
    ("lahore", "Lahore", 31.5204, 74.3587, "PK", "Asia/Karachi", False),
    ("dhaka", "Dhaka", 23.8103, 90.4125, "BD", "Asia/Dhaka", False),
    ("bangkok", "Bangkok", 13.7563, 100.5018, "TH", "Asia/Bangkok", True),
    ("jakarta", "Jakarta", -6.2088, 106.8456, "ID", "Asia/Jakarta", True),
    ("bali", "Bali", -8.4095, 115.1889, "ID", "Asia/Makassar", False),
    ("manila", "Manila", 14.5995, 120.9842, "PH", "Asia/Manila", True),
    ("kuala_lumpur", "Kuala Lumpur", 3.1390, 101.6869, "MY", "Asia/Kuala_Lumpur", True),
    ("singapore", "Singapore", 1.3521, 103.8198, "SG", "Asia/Singapore", True),
    ("ho_chi_minh", "Ho Chi Minh City", 10.8231, 106.6297, "VN", "Asia/Ho_Chi_Minh", True),
    ("hanoi", "Hanoi", 21.0278, 105.8342, "VN", "Asia/Ho_Chi_Minh", False),

    # === MIDDLE EAST ===
    ("dubai", "Dubai", 25.2048, 55.2708, "AE", "Asia/Dubai", True),
    ("abu_dhabi", "Abu Dhabi", 24.4539, 54.3773, "AE", "Asia/Dubai", True),
    ("doha", "Doha", 25.2854, 51.5310, "QA", "Asia/Qatar", True),
    ("riyadh", "Riyadh", 24.7136, 46.6753, "SA", "Asia/Riyadh", True),
    ("jeddah", "Jeddah", 21.4858, 39.1925, "SA", "Asia/Riyadh", False),
    ("tel_aviv", "Tel Aviv", 32.0853, 34.7818, "IL", "Asia/Jerusalem", True),
    ("jerusalem", "Jerusalem", 31.7683, 35.2137, "IL", "Asia/Jerusalem", False),
    ("kuwait_city", "Kuwait City", 29.3759, 47.9774, "KW", "Asia/Kuwait", False),
    ("muscat", "Muscat", 23.5880, 58.3829, "OM", "Asia/Muscat", False),
    ("beirut", "Beirut", 33.8938, 35.5018, "LB", "Asia/Beirut", False),
    ("amman", "Amman", 31.9454, 35.9284, "JO", "Asia/Amman", False),

    # === AUSTRALIA & OCEANIA ===
    ("sydney", "Sydney", -33.8688, 151.2093, "AU", "Australia/Sydney", True),
    ("melbourne", "Melbourne", -37.8136, 144.9631, "AU", "Australia/Melbourne", True),
    ("brisbane", "Brisbane", -27.4698, 153.0251, "AU", "Australia/Brisbane", True),
    ("perth", "Perth", -31.9505, 115.8605, "AU", "Australia/Perth", False),
    ("adelaide", "Adelaide", -34.9285, 138.6007, "AU", "Australia/Adelaide", False),
    ("auckland", "Auckland", -36.8509, 174.7645, "NZ", "Pacific/Auckland", True),
    ("wellington", "Wellington", -41.2865, 174.7762, "NZ", "Pacific/Auckland", False),
    ("honolulu", "Honolulu", 21.3069, -157.8583, "US", "Pacific/Honolulu", True),

    # === AFRICA ===
    ("cairo", "Cairo", 30.0444, 31.2357, "EG", "Africa/Cairo", True),
    ("alexandria", "Alexandria", 31.2001, 29.9187, "EG", "Africa/Cairo", False),
    ("luxor", "Luxor", 25.6872, 32.6396, "EG", "Africa/Cairo", False),
    ("cape_town", "Cape Town", -33.9249, 18.4241, "ZA", "Africa/Johannesburg", True),
    ("johannesburg", "Johannesburg", -26.2041, 28.0473, "ZA", "Africa/Johannesburg", True),
    ("lagos", "Lagos", 6.5244, 3.3792, "NG", "Africa/Lagos", True),
    ("nairobi", "Nairobi", -1.2921, 36.8219, "KE", "Africa/Nairobi", True),
    ("casablanca", "Casablanca", 33.5731, -7.5898, "MA", "Africa/Casablanca", True),
    ("marrakech", "Marrakech", 31.6295, -7.9811, "MA", "Africa/Casablanca", False),
    ("rabat", "Rabat", 34.0209, -6.8416, "MA", "Africa/Casablanca", False),
    ("tunis", "Tunis", 36.8065, 10.1815, "TN", "Africa/Tunis", False),
    ("accra", "Accra", 5.6037, -0.1870, "GH", "Africa/Accra", True),
    ("addis_ababa", "Addis Ababa", 8.9806, 38.7578, "ET", "Africa/Addis_Ababa", False),
    ("dar_es_salaam", "Dar es Salaam", -6.7924, 39.2083, "TZ", "Africa/Dar_es_Salaam", False),
    ("kampala", "Kampala", 0.3476, 32.5825, "UG", "Africa/Kampala", False),
    ("dakar", "Dakar", 14.7167, -17.4677, "SN", "Africa/Dakar", False),
    ("luanda", "Luanda", -8.8390, 13.2894, "AO", "Africa/Luanda", False),

    # === MEXICO & CENTRAL AMERICA ===
    ("mexico_city", "Mexico City", 19.4326, -99.1332, "MX", "America/Mexico_City", True),
    ("guadalajara", "Guadalajara", 20.6597, -103.3496, "MX", "America/Mexico_City", True),
    ("monterrey", "Monterrey", 25.6866, -100.3161, "MX", "America/Monterrey", True),
    ("cancun", "Cancun", 21.1619, -86.8515, "MX", "America/Cancun", False),
    ("tijuana", "Tijuana", 32.5149, -117.0382, "MX", "America/Tijuana", False),
    ("panama_city", "Panama City", 8.9824, -79.5199, "PA", "America/Panama", True),
    ("san_jose", "San Jose", 9.9281, -84.0907, "CR", "America/Costa_Rica", True),
    ("san_salvador", "San Salvador", 13.6929, -89.2182, "SV", "America/El_Salvador", False),
    ("tegucigalpa", "Tegucigalpa", 14.0723, -87.1921, "HN", "America/Tegucigalpa", False),
    ("managua", "Managua", 12.1150, -86.2362, "NI", "America/Managua", False),
    ("guatemala_city", "Guatemala City", 14.6349, -90.5069, "GT", "America/Guatemala", False),

    # === CARIBBEAN ===
    ("havana", "Havana", 23.1136, -82.3666, "CU", "America/Havana", False),
    ("santo_domingo", "Santo Domingo", 18.4861, -69.9312, "DO", "America/Santo_Domingo", False),
    ("san_juan", "San Juan", 18.4655, -66.1057, "PR", "America/Puerto_Rico", False),
    ("kingston", "Kingston", 17.9714, -76.7936, "JM", "America/Jamaica", False),
    ("nassau", "Nassau", 25.0343, -77.3963, "BS", "America/Nassau", False),

    # === SOUTH AMERICA ===
    ("bogota", "Bogota", 4.7110, -74.0721, "CO", "America/Bogota", True),
    ("medellin", "Medellin", 6.2442, -75.5812, "CO", "America/Bogota", False),
    ("cali", "Cali", 3.4516, -76.5320, "CO", "America/Bogota", False),
    ("buenos_aires", "Buenos Aires", -34.6037, -58.3816, "AR", "America/Argentina/Buenos_Aires", True),
    ("santiago", "Santiago", -33.4489, -70.6693, "CL", "America/Santiago", True),
    ("sao_paulo", "Sao Paulo", -23.5505, -46.6333, "BR", "America/Sao_Paulo", True),
    ("rio_de_janeiro", "Rio de Janeiro", -22.9068, -43.1729, "BR", "America/Sao_Paulo", True),
    ("brasilia", "Brasilia", -15.7975, -47.8919, "BR", "America/Sao_Paulo", True),
    ("salvador", "Salvador", -12.9714, -38.5014, "BR", "America/Bahia", False),
    ("recife", "Recife", -8.0476, -34.8770, "BR", "America/Recife", False),
    ("fortaleza", "Fortaleza", -3.7172, -38.5433, "BR", "America/Fortaleza", False),
    ("lima", "Lima", -12.0464, -77.0428, "PE", "America/Lima", True),
    ("cusco", "Cusco", -13.5319, -71.9675, "PE", "America/Lima", False),
    ("arequipa", "Arequipa", -16.4090, -71.5375, "PE", "America/Lima", False),
    ("caracas", "Caracas", 10.4806, -66.9036, "VE", "America/Caracas", True),
    ("quito", "Quito", -0.1807, -78.4678, "EC", "America/Guayaquil", True),
    ("guayaquil", "Guayaquil", -2.1894, -79.8890, "EC", "America/Guayaquil", False),
    ("montevideo", "Montevideo", -34.9011, -56.1645, "UY", "America/Montevideo", True),
    ("asuncion", "Asuncion", -25.2637, -57.5759, "PY", "America/Asuncion", False),
    ("la_paz", "La Paz", -16.4897, -68.1193, "BO", "America/La_Paz", True),
    ("santa_cruz", "Santa Cruz", -17.8146, -63.1561, "BO", "America/La_Paz", False),
]


def upgrade() -> None:
    # Create cities table
    op.create_table(
        'cities',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('city_id', sa.String(64), nullable=False),  # internal ID: new_york, london, etc
        sa.Column('name', sa.String(128), nullable=False),   # display name: New York, London
        sa.Column('lat', sa.Float(), nullable=True),
        sa.Column('lon', sa.Float(), nullable=True),
        sa.Column('country_code', sa.String(2), nullable=True),
        sa.Column('timezone', sa.String(64), nullable=True),
        sa.Column('is_tracked', sa.Boolean(), nullable=True, default=False),  # for risk management
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('city_id')
    )
    op.create_index('ix_cities_city_id', 'cities', ['city_id'])
    op.create_index('ix_cities_name', 'cities', ['name'])
    op.create_index('ix_cities_country_code', 'cities', ['country_code'])

    # Seed all cities - use OR IGNORE to skip duplicates
    op.execute("""
        INSERT OR IGNORE INTO cities (city_id, name, lat, lon, country_code, timezone, is_tracked)
        VALUES
    """ + ",\n".join([
        f"('{c[0]}', '{c[1]}', {c[2]}, {c[3]}, '{c[4]}', '{c[5]}', {str(c[6]).lower()})"
        for c in CITIES_DATA
    ]))


def downgrade() -> None:
    op.drop_table('cities')
