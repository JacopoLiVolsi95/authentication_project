import os
import datetime

from database import get_db, return_db_connection
from pydantic import BaseModel
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException


PROTECTED_SERVICE_ID = os.getenv("PROTECTED_SERVICE_ID")
PROTECTED_SERVICE_NAME = os.getenv("PROTECTED_SERVICE_NAME")
PROTECTED_SERVICE_PORT =  os.getenv("PROTECTED_SERVICE_PORT", "8001")
PROTECTED_SERVICE_TITLE = f"Protected Service {PROTECTED_SERVICE_ID}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        with return_db_connection() as conn:
            with conn.cursor() as cur:
                # Register the new protected service on startup
                cur.execute(
                    """
                    INSERT INTO protected_services (protected_service_id, protected_service_name) 
                    VALUES (%s, %s)
                    ON CONFLICT (protected_service_id) DO NOTHING;
                    """,
                    (PROTECTED_SERVICE_ID, PROTECTED_SERVICE_NAME)
                )
                conn.commit()
        print(f"Protected Service {PROTECTED_SERVICE_ID} successfully inserted on start.")
    except Exception as e:
        print(f"Failed to register service on startup: {e}")
    # Pass control over to the running FastAPI application
    yield 

    try:
        with return_db_connection() as conn:
            with conn.cursor() as cur:
                # Remove the service when Docker stops the container
                cur.execute("DELETE FROM protected_services WHERE service_id = %s;", (PROTECTED_SERVICE_ID,))
                conn.commit()
        print(f"Protected Service {PROTECTED_SERVICE_ID} successfully removed on stop.")
    except Exception as e:
        print(f"Failed to remove protected service on stop: {e}")


app = FastAPI(
    title=PROTECTED_SERVICE_TITLE,
    description="Manages a generic protected service.",
    version="1.0.0",
    lifespan=lifespan
)


#### Pydantic Schemas ####
class TokenAuthentication(BaseModel):
    protected_service_id: int
    temporary_token: str


#### Endpoints ####
@app.get("/", tags=["System"])
def root():
    return {
        "service": PROTECTED_SERVICE_TITLE,
        "status": "online",
        "documentation": f"Visit http://localhost:{PROTECTED_SERVICE_PORT}/docs to test the API"
    }

@app.post("/token-login", tags=["Token"])
def token_login(tk: TokenAuthentication, db = Depends(get_db)):
    with db.cursor() as cur:
        cur.execute("SELECT * FROM protected_services_tokens WHERE protected_service_id = %s AND temporary_token = %s;", (tk.protected_service_id, tk.temporary_token,))  # Prevent SQL injection
        found_token = cur.fetchone()
    if not found_token:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    now = datetime.datetime.now()
    expires_at = found_token["expires_at"]
    print(f"Comparing now time {now} with token expiration date {expires_at}")
    if now > expires_at:
        raise HTTPException(status_code=401, detail="Token expired")

    return  {"status": "success", "message": "Token accepted successfully"}
