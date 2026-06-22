"""
Authentication Utility Module For The Library Management System.

This Module Provides Helper Functions For Extracting And Validating
JSON Web Tokens (JWT) From Incoming HTTP Requests.
"""

import jwt
from flask import request
from app.config.config import Config


def get_user_from_token():
    """
    Extract And Decode The JWT Token From The Authorization Header.

    This Function Retrieves The Token From The 'Authorization' Header,
    Validates Its Signature And Expiration, And Returns The Decoded
    Payload. It Is Used As A Middleware For Protecting API Routes.

    The Header Is Expected To Be In The Format:
        Authorization: Bearer <token>

    Returns:
        tuple: A Tuple Containing:
            - decoded (dict or None): The Decoded JWT Payload (Contains
              user_id, email, role, exp, Etc.) If The Token Is Valid.
            - error (dict or None): An Error Response Dictionary If
              The Token Is Missing, Expired, Or Invalid.
            - status_code (int or None): The HTTP Status Code For The
              Error (401 Unauthorized) Or None If Successful.

    Possible Errors:
        - Token Missing: Returns (None, {"error": "Token missing"}, 401)
        - Token Expired: Returns (None, {"error": "Token expired"}, 401)
        - Invalid Token: Returns (None, {"error": "Invalid token"}, 401)
    """
    # Retrieve The Authorization Header From The Request.
    token = request.headers.get('Authorization')

    # If The Header Is Missing, Return An Error Response.
    if not token:
        return None, {"error": "Token missing"}, 401

    # Remove The 'Bearer ' Prefix If Present.
    # The Token Is Expected To Be In The Format 'Bearer <token>'.
    if token.startswith('Bearer '):
        token = token[7:]  # Strip The 'Bearer ' Prefix.

    try:
        # Decode The Token Using The Secret Key And The HS256 Algorithm.
        # The Decode Process Automatically Verifies The Signature And
        # Checks The Expiration Time (exp Claim).
        decoded = jwt.decode(token, Config.JWT_SECRET, algorithms=['HS256'])

        # Return The Decoded Payload On Success.
        return decoded, None, None

    except jwt.ExpiredSignatureError:
        # The Token Has Exceeded Its Expiration Time.
        return None, {"error": "Token expired"}, 401

    except jwt.InvalidTokenError:
        # The Token Is Malformed, Has An Invalid Signature, Or Contains
        # Invalid Claims.
        return None, {"error": "Invalid token"}, 401