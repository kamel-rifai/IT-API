import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

COMPLAINT_DB_URL = os.getenv("COMPLAINT_DB_URL", "postgresql+psycopg2://postgres:postgres@192.168.88.100:5433/planka")

engine = create_engine(COMPLAINT_DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_complaint_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
