import os
import psycopg2
import psycopg2.extras

# Connection parameters for PostgreSQL database
PG_DOCKER_HOST = "postgres"
PG_DOCKER_PORT = 5432

# Database and table names
AUTHENTICATION_SERVICE_DB = "authentication_service"
USERS_TABLE = "users"
PROTECTED_SERVICES_TABLE = "protected_services_tokens"


def get_env_credential() -> dict[str, object]:
    user = os.getenv("POSTGRES_USER", None)
    password = os.getenv("POSTGRES_PASSWORD", None)
    host = os.getenv("POSTGRES_HOST", PG_DOCKER_HOST)
    port = int(os.getenv("POSTGRES_PORT", PG_DOCKER_PORT))
    db_name = os.getenv("POSTGRES_DB", AUTHENTICATION_SERVICE_DB)

    return {
        "host": host,
        "port": port,
        "dbname": db_name,
        "user": user,
        "password": password,
    }


def return_db_connection(credentials: dict[str, object] = None):
    if credentials is None:
        credentials = get_env_credential()
    return psycopg2.connect(**credentials, cursor_factory=psycopg2.extras.RealDictCursor)


def get_db():
    connection = psycopg2.connect(**get_env_credential(), cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        yield connection
    finally:
        connection.close()
