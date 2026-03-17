from sqlalchemy import create_engine, text
import os

db_path = 'sqlite:///db/polybet.db'
engine = create_engine(db_path)

print("--- City Distribution ---")
with engine.connect() as conn:
    res = conn.execute(text('SELECT city, count(*) FROM markets GROUP BY city ORDER BY count(*) DESC;'))
    for row in res:
        print(f"{row[0]}: {row[1]}")

print("\n--- Recent Unknown Questions ---")
with engine.connect() as conn:
    res = conn.execute(text("SELECT question FROM markets WHERE city='unknown' LIMIT 5;"))
    for row in res:
        print(f"- {row[0]}")
