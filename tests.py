import os
import time
import requests
import unittest

from database import get_env_credential, return_db_connection
from authentication_service import hash_password, verify_password

#  Credentials defined in init.sql for testing purposes
TEST_POSTGRES_USER = "test-user"
TEST_POSTGRES_PASSWORD = "test-psw"


class TestPasswordHashing(unittest.TestCase):
    """ Unit tests for password hashing and verification. """

    def test_hash_and_verify_password(self):
        password = "my_secure_password"
        hashed = hash_password(password)
        self.assertTrue(verify_password(password, hashed), "Password should match the hashed version")
        self.assertFalse(verify_password("wrong_password", hashed), "Password should not match the hashed version, but it does!")
        print("test_hash_and_verify_password passed.")


class TestPostgresConnection(unittest.TestCase):
    """ Test for reaching the PostgreSQL database. """

    def setUp(self) -> None:
        self.connection_credentials = get_env_credential()
        error = 0
        msg = "Error in environment variable configuration:\n"
        for key, val in self.connection_credentials.items():
            if val is None:
                error += 1
                msg += f"Missing environment variable for {key}\n"
        self.assertEqual(error, 0, msg)

    def test_connection_to_auth_db(self) -> None:
        connection_kwargs = self.connection_credentials
        try:
            _ = return_db_connection(connection_kwargs)
            print("test_connection_to_auth_db passed.")
        except Exception as e:
            self.fail(f"Failed to connect to the database: {e}")

    def test_query_test_user(self) -> None:
        connection_kwargs = self.connection_credentials
        db = return_db_connection(connection_kwargs)
        with db as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE username = %s", (TEST_POSTGRES_USER,))
                result = cursor.fetchone()
                self.assertIsNotNone(result, f"User '{TEST_POSTGRES_USER}' should exist in the database.")
                self.assertEqual(result["username"], TEST_POSTGRES_USER, f"Expected username {TEST_POSTGRES_USER}, got {result['username']}")
                self.assertTrue(verify_password(TEST_POSTGRES_PASSWORD, result["password"]), "Password verification failed for the test user.")
        print("test_query_test_user passed.")


DEFAULT_AUTHENTICATION_PORT = 8000
AUTHENTICATION_PORT = os.getenv("AUTHENTICATION_PORT", DEFAULT_AUTHENTICATION_PORT)
AUTHENTICATION_CONTAINER_NAME = "authentication"
AUTHENTICATION_URL = f"http://{AUTHENTICATION_CONTAINER_NAME}:{AUTHENTICATION_PORT}"


class TestAuthenticationAPI(unittest.TestCase):
    """ Unit tests for the Authentication Service API. """

    def setUp(self) -> None:
        self.username = "new-user"
        self.password = "secret-psw"
        self.user_payload = {
            "username": self.username,
            "password": self.password
        }

    # N.B. test name order matters, that's why we put numbers in the function's names
    def test_01_register_user_success(self):
        # Add epoch to username and create new payload in order to prevent test failure if called more than once
        now_epoch = str(int(time.time()))
        user_payload = {
            "username": self.username + now_epoch,
            "password": self.password
        }
        response = requests.post(f"{AUTHENTICATION_URL}/register", json=user_payload)
        self.assertEqual(response.status_code, 201, f"Expected 201, got {response.status_code}: {response.text}")
        data = response.json()
        self.assertEqual(data["username"], self.username + now_epoch)
        self.assertEqual(data["message"], "User registered successfully")
        print("test_01_register_user_success passed.")

    def test_02_register_duplicate_user_fails(self):
        _ = requests.post(f"{AUTHENTICATION_URL}/register", json=self.user_payload)
        time.sleep(0.5)
        response = requests.post(f"{AUTHENTICATION_URL}/register", json=self.user_payload)
        self.assertEqual(response.status_code, 400, f"User {self.username} did not fail")
        self.assertEqual(response.json()["detail"], "Username already registered")
        print("test_02_register_duplicate_user_fails passed.")

    def test_03_login_success(self):
        response = requests.post(f"{AUTHENTICATION_URL}/login", json=self.user_payload)
        self.assertEqual(response.status_code, 200, f"Expected 200, got {response.status_code}: {response.text}")
        print("test_03_login_success passed.")

    def test_04_login_wrong_password_fails(self):
        wrong_credentials = {
            "username": self.username,
            "password": "wrong-psw"
        }
        response = requests.post(f"{AUTHENTICATION_URL}/login", json=wrong_credentials)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Invalid credentials")
        print("test_04_login_wrong_password_fails passed.")

    def test_05_login_unexisting_user_fails(self):
        fake_credentials = {
            "username": "unexisting-user",
            "password": "unexisting-psw"
        }
        response = requests.post(f"{AUTHENTICATION_URL}/login", json=fake_credentials)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Invalid credentials")
        print("test_05_login_unexisting_user_fails passed.")

    def test_06_unexisting_protected_service(self):
        valid_seconds = 10
        max_service_id = 1
        db = return_db_connection()
        with db as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT MAX(protected_service_id) FROM protected_services")
                result = cursor.fetchone()
                if result:
                    max_service_id = result["max"] + 1
        issue_token_payload =  {
            "username": self.username,
            "password": self.password,
            "protected_service_id": max_service_id,
            "valid_seconds": valid_seconds
        }
        response = requests.post(f"{AUTHENTICATION_URL}/issue-token", json=issue_token_payload)
        self.assertEqual(response.status_code, 404, f"Expected 404, got {response.status_code}: {response.text}")
        self.assertEqual(response.json()["detail"], f"Protected service ID {max_service_id} is not found.")
        print("test_06_unexisting_protected_service passed.")


DEFAULT_PROTECTED_SERVICE_PORT = 8001
PROTECTED_SERVICE_PORT = os.getenv("PROTECTED_SERVICE_PORT_0", DEFAULT_AUTHENTICATION_PORT)
PROTECTED_SERVICE_CONTAINER_NAME = "protected_service_0"
PROTECTED_SERVICE_URL = f"http://{PROTECTED_SERVICE_CONTAINER_NAME}:{PROTECTED_SERVICE_PORT}"


class TestProtectedServiceAPI(unittest.TestCase):
    """ Unit tests for the Protected Service API. """

    def setUp(self) -> None:
        self.username = TEST_POSTGRES_USER
        self.password = TEST_POSTGRES_PASSWORD
        self.test_protected_service_id = 0
        self.test_valid_seconds = 2
        self.issue_token_payload = {
            "username": self.username,
            "password": self.password,
            "protected_service_id": self.test_protected_service_id,
            "valid_seconds": self.test_valid_seconds
        }

    def test_01_issue_token_success(self):
        response = requests.post(f"{AUTHENTICATION_URL}/issue-token", json=self.issue_token_payload)
        self.assertEqual(response.status_code, 200, f"Expected 200, got {response.status_code}: {response.text}")
        self.assertEqual(response.json()["message"], "Token generated successfully")
        print("test_01_issue_token_success passed.")

    def test_02_token_login_success(self):
        response = requests.post(f"{AUTHENTICATION_URL}/issue-token", json=self.issue_token_payload)
        token_login_payload = {"protected_service_id": self.test_protected_service_id, "temporary_token": response.json()["temporary_token"]}
        protected_response = requests.post(f"{PROTECTED_SERVICE_URL}/token-login", json=token_login_payload)
        self.assertEqual(protected_response.status_code, 200, f"Expected 200, got {protected_response.status_code}: {protected_response.text}")
        print("test_02_token_login_success passed.")

    def test_03_token_login_failure(self):
        unexisting_token_payload = {"protected_service_id": self.test_protected_service_id, "temporary_token": "unexisting-token"}
        response = requests.post(f"{PROTECTED_SERVICE_URL}/token-login", json=unexisting_token_payload)
        self.assertEqual(response.status_code, 401, f"Expected 401, got {response.status_code}: {response.text}")
        self.assertEqual(response.json()["detail"], "Invalid credentials")
        print("test_03_token_login_failure passed.")

    def test_04_token_login_expired(self):
        response = requests.post(f"{AUTHENTICATION_URL}/issue-token", json=self.issue_token_payload)
        token_login_payload = {"protected_service_id": self.test_protected_service_id, "temporary_token": response.json()["temporary_token"]}
        time.sleep(self.test_valid_seconds + 1)
        protected_response = requests.post(f"{PROTECTED_SERVICE_URL}/token-login", json=token_login_payload)
        self.assertEqual(protected_response.status_code, 401, f"Expected 401, got {protected_response.status_code}: {protected_response.text}")
        self.assertEqual(protected_response.json()["detail"], "Token expired")
        print("test_04_token_login_expired passed.")

    def test_05_token_invalidation(self):
        response = requests.post(f"{AUTHENTICATION_URL}/issue-token", json=self.issue_token_payload)
        token_logout_payload = {"temporary_token": response.json()["temporary_token"]}
        logout_response = requests.post(f"{AUTHENTICATION_URL}/logout", json=token_logout_payload)
        self.assertEqual(logout_response.status_code, 200, f"Expected 200, got {logout_response.status_code}: {logout_response.text}")
        token_login_payload = {"protected_service_id": self.test_protected_service_id, "temporary_token": response.json()["temporary_token"]}
        protected_response = requests.post(f"{PROTECTED_SERVICE_URL}/token-login", json=token_login_payload)
        self.assertEqual(protected_response.status_code, 401, f"Expected 401, got {protected_response.status_code}: {protected_response.text}")
        self.assertEqual(protected_response.json()["detail"], "Invalid credentials")
        print("test_05_token_invalidation passed.")


if __name__ == '__main__':
    unittest.main()
