from sqlalchemy import create_engine, inspect, text
from db import URL_DATABASE

def migrate():
    engine = create_engine(URL_DATABASE)
    inspector = inspect(engine)
    
    # Check if DEVICES table exists
    if not inspector.has_table("DEVICES"):
        print("Table 'DEVICES' does not exist.")
        return

    columns = [c['name'] for c in inspector.get_columns('DEVICES')]
    
    if 'cableNumber' not in columns:
        print("Adding 'cableNumber' column to DEVICES table...")
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE DEVICES ADD COLUMN cableNumber VARCHAR(100)"))
            conn.commit()
        print("Successfully added 'cableNumber' column.")
    else:
        print("'cableNumber' column already exists in DEVICES table.")

if __name__ == "__main__":
    migrate()
