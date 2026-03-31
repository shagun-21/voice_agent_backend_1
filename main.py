from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from fastapi import Request

# DB CONFIG (replace with your Supabase credentials)
DATABASE_URL = "postgresql://postgres.fieqbixfeysdtvzzkaws:Shagun20013001@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()

app = FastAPI()

# ----------------------
# DB MODEL
# ----------------------
class LeadDB(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    interest = Column(String)
    budget = Column(String)
    lead_type = Column(String)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# ----------------------
# REQUEST MODEL
# ----------------------
class Lead(BaseModel):
    name: str
    interest: str
    budget: str

# ----------------------
# BUSINESS LOGIC
# ----------------------
def classify_lead(budget):
    try:
        if int(budget) >= 50000:
            return "HIGH"
        else:
            return "LOW"
    except:
        return "UNKNOWN"

# ----------------------
# API ENDPOINT
# ----------------------
# @app.post("/api/lead")
# def create_lead(lead: Lead):
#     db = SessionLocal()

#     lead_type = classify_lead(lead.budget)

#     db_lead = LeadDB(
#         name=lead.name,
#         interest=lead.interest,
#         budget=lead.budget,
#         lead_type=lead_type
#     )

#     db.add(db_lead)
#     db.commit()
#     db.refresh(db_lead)

#     return {
#         "message": "Lead stored successfully",
#         "lead_type": lead_type
#     }

@app.post("/api/lead")
async def create_lead(request: Request):
    data = await request.json()
    print("RAW DATA:", data)
    return {"status": "received"}


@app.get("/api/leads")
def get_leads():
    db = SessionLocal()
    return db.query(LeadDB).all()