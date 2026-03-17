from sqlalchemy import create_engine, text
import os

db_path = 'sqlite:///data/polybet.db'
engine = create_engine(db_path)

with engine.connect() as conn:
    # Delete unknown markets so they can be re-resolved
    conn.execute(text("DELETE FROM markets WHERE city='unknown';"))
    
    # Delete unknown analysis results
    conn.execute(text("DELETE FROM analysis_results WHERE city='unknown';"))
    
    conn.commit()
    print("✅ Cleaned up 'unknown' entries from database.")
