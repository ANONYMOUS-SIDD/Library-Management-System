import os
from dotenv import load_dotenv

# Load Environment Variables From The .env File Into The Application.
load_dotenv()

class Config:
    """
    Central Configuration Class For The Library Management System.

    All Settings Are Loaded From Environment Variables With Sensible Defaults.
    """

    # --- Database Connection Settings ---

    # Hostname Or IP Address Of The PostgreSQL Database Server.
    DB_HOST = os.getenv('DB_HOST', 'localhost')

    # Port Number On Which The PostgreSQL Database Server Is Listening.
    DB_PORT = os.getenv('DB_PORT', '5432')

    # Name Of The Database To Connect To (e.g., 'lms').
    DB_NAME = os.getenv('DB_NAME', 'lms')

    # Username Used To Authenticate With The PostgreSQL Database.
    DB_USER = os.getenv('DB_USER', 'postgres')

    # Password For The Database User. If Not Set In .env, It Remains Empty.
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')

    # --- JSON Web Token (JWT) Configuration ---

    # Secret Key Used To Sign And Verify JWTs. Must Be Kept Confidential.
    # The Default Value Is For Development Only; In Production, Always Set This
    # In The .env File To A Strong, Unique String.
    JWT_SECRET = os.getenv('JWT_SECRET', 'default_secret_change_me')