"""
User Management Module For The Library Management System.

This Module Handles All User-Related Database Operations Including
User Registration, Retrieval, Profile Updates, And Password Changes.
"""

import psycopg2
import bcrypt
from app.config.config import Config


def get_db_connection():
    """
    Establish And Return A New Connection To The PostgreSQL Database
    Using The Settings Defined In The Config Class.
    """
    return psycopg2.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        database=Config.DB_NAME,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD
    )


def create_user(name, email, password, role='student', contact_info=None):
    """
    Register A New User In The Database.

    This Function Hashes The Provided Password Using Bcrypt, Then Inserts
    A New User Record Into The users Table. If The Email Already Exists,
    The Function Returns None.

    Parameters:
        name (str): The Full Name Of The User.
        email (str): The User's Email Address (Must Be Unique).
        password (str): The Plain-Text Password (Will Be Hashed).
        role (str): The User Role ('student' Or 'librarian').
        contact_info (str, optional): Additional Contact Details.

    Returns:
        int or None: The ID Of The Newly Created User On Success,
                     Or None If The Email Already Exists.
    """
    # Generate A Salted Hash Of The Password Using Bcrypt.
    # The Hash Is Stored As A Unicode String In The Database.
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Establish A Database Connection And Create A Cursor.
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Insert The New User Record With The Hashed Password.
        # The RETURNING Clause Returns The Generated user_id.
        cur.execute("""
            INSERT INTO users (name, email, password_hash, role, contact_info)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING user_id
        """, (name, email, hashed, role, contact_info))

        # Retrieve The Newly Generated User ID.
        user_id = cur.fetchone()[0]

        # Commit The Transaction To Save The Changes.
        conn.commit()

        # Return The ID Of The Created User.
        return user_id

    except psycopg2.errors.UniqueViolation:
        # If The Email Already Exists, The Database Raises A Unique Violation.
        # Return None To Indicate That The Registration Failed.
        return None

    finally:
        # Ensure The Cursor And Connection Are Closed To Free Resources.
        cur.close()
        conn.close()


def get_user_by_email(email):
    """
    Retrieve A User Record By Email Address.

    This Function Fetches The Complete User Record (Including The Hashed
    Password) For A Given Email Address. It Is Used During Login To
    Verify Credentials.

    Parameters:
        email (str): The Email Address Of The User To Retrieve.

    Returns:
        tuple or None: A Tuple Containing (user_id, name, email,
                        password_hash, role, photo_path, contact_info),
                        Or None If No User With That Email Exists.
    """
    # Establish A Database Connection And Create A Cursor.
    conn = get_db_connection()
    cur = conn.cursor()

    # Execute The Query To Fetch The User Record For The Given Email.
    cur.execute("""
        SELECT user_id, name, email, password_hash, role,
               photo_path, contact_info
        FROM users
        WHERE email = %s
    """, (email,))

    # Fetch The First Row (If Any) Or None.
    user = cur.fetchone()

    # Close The Cursor And Database Connection To Free Resources.
    cur.close()
    conn.close()

    # Return The Retrieved User Tuple Or None.
    return user


def update_user_profile(user_id, name=None, contact_info=None, photo_path=None):
    """
    Update A User's Profile Fields.

    This Function Updates Only The Fields That Are Provided As Arguments.
    It Supports Updating The Name, Contact Information, And Photo Path.

    Parameters:
        user_id (int): The ID Of The User Whose Profile Is To Be Updated.
        name (str, optional): New Name (If Provided).
        contact_info (str, optional): New Contact Information (If Provided).
        photo_path (str, optional): New Photo File Path (If Provided).
    """
    # Establish A Database Connection And Create A Cursor.
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Build The Dynamic UPDATE Query Based On Provided Fields.
        updates = []
        params = []

        if name is not None:
            updates.append("name = %s")
            params.append(name)

        if contact_info is not None:
            updates.append("contact_info = %s")
            params.append(contact_info)

        if photo_path is not None:
            updates.append("photo_path = %s")
            params.append(photo_path)

        # If No Fields Were Provided, Exit Early To Avoid A Syntax Error.
        if not updates:
            return

        # Add The User ID To The Parameter List For The WHERE Clause.
        params.append(user_id)

        # Construct And Execute The UPDATE Query.
        cur.execute(f"""
            UPDATE users
            SET {', '.join(updates)}
            WHERE user_id = %s
        """, params)

        # Commit The Transaction To Save The Changes.
        conn.commit()

    finally:
        # Ensure The Cursor And Connection Are Closed To Free Resources.
        cur.close()
        conn.close()


def change_user_password(user_id, new_password):
    """
    Change A User's Password.

    This Function Hashes The New Password Using Bcrypt And Updates The
    password_hash Field For The Specified User.

    Parameters:
        user_id (int): The ID Of The User Whose Password Is To Be Changed.
        new_password (str): The New Plain-Text Password (Will Be Hashed).
    """
    # Hash The New Password Using Bcrypt.
    hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Establish A Database Connection And Create A Cursor.
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Update The User's Password Hash In The Database.
        cur.execute("""
            UPDATE users
            SET password_hash = %s
            WHERE user_id = %s
        """, (hashed, user_id))

        # Commit The Transaction To Save The Changes.
        conn.commit()

    finally:
        # Ensure The Cursor And Connection Are Closed To Free Resources.
        cur.close()
        conn.close()