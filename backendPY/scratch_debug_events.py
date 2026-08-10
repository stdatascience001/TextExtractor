import asyncio
import sys
import os
import traceback

sys.path.append(r"d:\PdfReader\backendPY")

from sqlalchemy import select, and_
from database.database import SessionLocal
from models.models import ActivityEvent

async def debug_events():
    output_path = r"C:\Users\Admin\.gemini\antigravity-ide\brain\07bf26d0-fb98-4a64-b418-b20124e45d1e\scratch\traceback.txt"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w") as f:
        f.write("Debug run started...\n")
        
    try:
        async with SessionLocal() as db:
            doc_id = "7aede106-5e53-4136-b75a-d3e46437a0a8"
            stmt = (
                select(ActivityEvent)
                .where(
                    ActivityEvent.payload["document_id"].astext == doc_id
                )
            )
            res = await db.execute(stmt)
            events = res.scalars().all()
            
            with open(output_path, "a") as f:
                f.write(f"Success! Found {len(events)} events.\n")
                for e in events:
                    f.write(f"Event: {e.id}, Action: {e.action_name}\n")
    except Exception as e:
        tb = traceback.format_exc()
        with open(output_path, "a") as f:
            f.write("Error occurred:\n")
            f.write(tb)
            f.write("\n")

if __name__ == "__main__":
    asyncio.run(debug_events())
