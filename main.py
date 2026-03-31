from fastapi import FastAPI, Request
from sqlalchemy import create_engine, Column, Integer, String, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import requests
import json

# ----------------------
# CONFIG
# ----------------------
DATABASE_URL = "postgresql://postgres.fieqbixfeysdtvzzkaws:Shagun20013001@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres"

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3"

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
# BUSINESS LOGIC
# ----------------------
def classify_lead(budget):
    try:
        return "HIGH" if int(str(budget).replace(",", "").replace(".", "").strip()) >= 50000 else "LOW"
    except:
        return "UNKNOWN"

# ----------------------
# TRANSCRIPT EXTRACTOR
# Handles every payload shape Bolna might send
# ----------------------
def extract_transcript(data: dict) -> str:
    return (
        data.get("transcript") or
        data.get("arguments", {}).get("transcript") or
        data.get("param", {}).get("transcript") or
        data.get("data", {}).get("transcript") or
        data.get("tool_input", {}).get("transcript") or
        ""
    )

# ----------------------
# OLLAMA EXTRACTION
# ----------------------
def extract_with_ollama(transcript: str):
    prompt = f"""
You are a strict JSON extractor.

Extract:
- name
- interest
- budget

Rules:
- Return ONLY JSON, nothing else
- No explanation, no markdown, no backticks
- Budget must be a number only
- Always close the JSON properly
- Name must be written in English (romanized), even if spoken in Hindi or another language
- Interest must be in English

Format:
{{
  "name": "string",
  "interest": "string",
  "budget": "number"
}}

Conversation:
{transcript}
"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False
            },
            timeout=120
        )

        result = response.json()
        text_output = result.get("response", "").strip()
        print("RAW OLLAMA OUTPUT:", text_output)

        # Clean out markdown fences if present
        text_output = text_output.replace("```json", "").replace("```", "").strip()

        # Extract JSON block safely
        start = text_output.find("{")
        end = text_output.rfind("}")

        if start != -1 and end != -1:
            cleaned = text_output[start:end+1]
        else:
            cleaned = text_output

        if not cleaned.endswith("}"):
            cleaned += "}"

        print("CLEANED JSON:", cleaned)
        return json.loads(cleaned)

    except Exception as e:
        print("OLLAMA ERROR:", str(e))
        return {
            "name": "Unknown",
            "interest": "Unknown",
            "budget": "0"
        }

# ----------------------
# DEBUG ENDPOINT
# Point Bolna here temporarily to see exact payload shape
# Visit http://localhost:4040 in browser to see ngrok logs
# ----------------------
@app.post("/debug")
async def debug_payload(request: Request):
    try:
        data = await request.json()
    except:
        data = {}
    print("=== BOLNA DEBUG PAYLOAD ===")
    print(json.dumps(data, indent=2))
    return {"received": data}

# ----------------------
# MAIN ENDPOINT
# ----------------------
@app.post("/api/lead")
async def create_lead(request: Request):
    try:
        data = await request.json()
    except Exception as e:
        return {"error": f"Failed to parse request body: {str(e)}"}

    print("RAW FROM BOLNA:", json.dumps(data, indent=2))

    transcript = extract_transcript(data)

    if not transcript:
        return {
            "error": "No transcript found in payload",
            "received_keys": list(data.keys()),
            "full_payload": data  # remove this line once working
        }

    print("TRANSCRIPT PREVIEW:", transcript[:300])

    extracted = extract_with_ollama(transcript)

    name     = extracted.get("name", "Unknown")
    interest = extracted.get("interest", "Unknown")
    budget   = str(extracted.get("budget", "0"))
    lead_type = classify_lead(budget)

    db = SessionLocal()
    try:
        db_lead = LeadDB(
            name=name,
            interest=interest,
            budget=budget,
            lead_type=lead_type
        )
        db.add(db_lead)
        db.commit()
    except Exception as e:
        db.rollback()
        print("DB ERROR:", str(e))
        return {"error": f"Database error: {str(e)}"}
    finally:
        db.close()

    return {
        "message": "Lead stored successfully",
        "data": extracted,
        "lead_type": lead_type
    }

# ----------------------
# GET ALL LEADS
# ----------------------
@app.get("/api/leads")
def get_leads():
    db = SessionLocal()
    try:
        return db.query(LeadDB).all()
    finally:
        db.close()