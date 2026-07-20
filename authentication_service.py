import os
import bcrypt
import string
import random
import datetime
import psycopg2.errors

from database import get_db
from pydantic import BaseModel
from fastapi import FastAPI, Depends, HTTPException, status


AUTHENTICATION_TITLE = "Central Authentication Service"
AUTHENTICATION_PORT = os.getenv("AUTHENTICATION_PORT", "8000")

app = FastAPI(
    title=AUTHENTICATION_TITLE,
    description="Manages users registration, login and token issuance for protected services.",
    version="1.0.0"
)


#### Helper Functions for Password Hashing and Verification ####
def hash_password(password: str) -> str:
    """
    Function to hash a password using bcrypt.
    Args:
        password (str): The plain text password to hash.
    Returns:
        str: The hashed password.
    """
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Function to verify a plain text password against a hashed password.
    Args:
        plain_password (str): The plain text password to verify.
        hashed_password (str): The hashed password to compare against.
    Returns:
        bool: True if the passwords match, False otherwise.
    """
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))



def create_token() -> str:
    """
    Create a random access token.
    Returns:
        str: the created token.
    """
    token_length = 10  # Fixed token length
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=token_length))


#### Pydantic Schemas ####
class UserAuth(BaseModel):
    username: str
    password: str


class TokenRequest(BaseModel):
    username: str
    password: str
    protected_service_id: int
    valid_seconds: int


class TokenInvalidation(BaseModel):
    temporary_token: str


#### Endpoints ####
@app.get("/", tags=["System"])
def root():
    return {
        "service": AUTHENTICATION_TITLE,
        "status": "online",
        "documentation": f"Visit http://localhost:{AUTHENTICATION_PORT}/docs to test the API"
    }

@app.post("/register", status_code=status.HTTP_201_CREATED, tags=["Users"])
def register_user(user: UserAuth, db = Depends(get_db)):
    with db.cursor() as cur:
        # Check if the username already exists
        cur.execute("SELECT id FROM users WHERE username = %s;", (user.username,))  # Prevent SQL injection
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Username already registered")

        # Store the new user with his hashed password
        hashed = hash_password(user.password)
        cur.execute(
            "INSERT INTO users (username, password) VALUES (%s, %s) RETURNING username;",
            (user.username, hashed)
        )
        new_user = cur.fetchone()
        db.commit()
    # Return a success message with the new user's username
    return {"message": "User registered successfully", "username": new_user["username"]}


@app.post("/login", tags=["Users"])
def login_user(user: UserAuth, db = Depends(get_db)):
    with db.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE username = %s;", (user.username,))  # Prevent SQL injection
        db_user = cur.fetchone()

    if not db_user or not verify_password(user.password, db_user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {"message": "Login successful", "username": db_user["username"]}


@app.post("/issue-token", tags=["Token"])
def issue_token(req: TokenRequest, db = Depends(get_db)):
    # Verify username and password credential
    with db.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE username = %s;", (req.username,))  # Prevent SQL injection
        db_user = cur.fetchone()
    if not db_user or not verify_password(req.password, db_user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    with db.cursor() as cur:
        cur.execute("SELECT protected_service_id FROM protected_services WHERE protected_service_id = %s;", (req.protected_service_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Protected service ID {req.protected_service_id} is not found.")

    temporary_token = create_token()
    created_at = datetime.datetime.now()
    expires_at = created_at + datetime.timedelta(seconds=req.valid_seconds)

    with db.cursor() as cur:
        try:
            cur.execute(
                """
                INSERT INTO protected_services_tokens (protected_service_id, username, temporary_token, created_at, expires_at)
                VALUES (%s, %s, %s, %s, %s);""",
                (req.protected_service_id, req.username, temporary_token, created_at, expires_at)
            )
            db.commit()
        # Ensure that token is UNIQUE
        except psycopg2.errors.UniqueViolation as pguv:
            print(f"occurred error: {pguv}")
            db.rollback()  # Resets the aborted database transaction
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Token collision: this temporary token already exists.")

    return {
        "status": "success",
        "message": "Token generated successfully",
        "temporary_token": temporary_token,
        "expires_at": expires_at.isoformat() + "Z",
        "valid_seconds": req.valid_seconds
    }


@app.post("/logout", tags=["Token"])
def logout_token(req: TokenInvalidation, db = Depends(get_db)):
    with db.cursor() as cur:
        # Delete the token and return its ID to confirm it existed
        cur.execute(
            "DELETE FROM protected_services_tokens WHERE temporary_token = %s RETURNING id;",
            (req.temporary_token,)
        )
        deleted_token = cur.fetchone()
        db.commit()

    # If nothing was returned, the token was either already deleted or never existed
    if not deleted_token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Token not found or already invalidated"
        )

    return {"status": "success", "message": "Credential successfully invalidated and logged out"}
