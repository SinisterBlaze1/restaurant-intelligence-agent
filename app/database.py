import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

# Use Neon cloud DB if available, otherwise fall back to local
DATABASE_URL = os.getenv("NEON_DATABASE_URL") or "postgresql://postgres:12345678@localhost:5432/restaurant_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()