# src/main.py
import uvicorn
from api.rag_api import app

if __name__ == "__main__":
    # Run the application using Uvicorn
    # In production, you would run this via the command line or Docker CMD:
    # uvicorn src.api.rag_api:app --host 0.0.0.0 --port 8000
    uvicorn.run("api.rag_api:app", host="0.0.0.0", port=8000, reload=True)
