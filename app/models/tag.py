"""
Tags Module For The Library Management System.

This Module Handles All Operations Related To User-Generated Tags On Books,
Including Adding Tags, Retrieving A User's Tags, And Deleting Tags.
"""

import psycopg2
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


def add_tag(user_id, book_id, tag_text):
    """
    Add A New Tag To A Specific Book For A Given User.

    This Function Inserts A Tag Record Into The tags Table. The tag_text
    Is Associated With A Specific Book And User. A Unique Constraint On
    (user_id, book_id, tag_text) Prevents Duplicate Tags.

    Parameters:
        user_id (int): The ID Of The User Creating The Tag.
        book_id (int): The ID Of The Book Being Tagged.
        tag_text (str): The Tag Text (E.g., 'fiction', 'classic', 'to-read').

    Returns:
        int or None: The ID Of The Newly Created Tag If Successful,
                     Or None If The Tag Already Exists For This User And Book.
    """
    # Establish A Database Connection And Create A Cursor.
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Insert The New Tag Record Into The tags Table.
        # The created_at Timestamp Is Automatically Set To The Current Time.
        # The RETURNING Clause Returns The Generated tag_id.
        cur.execute("""
            INSERT INTO tags (user_id, book_id, tag_text, created_at)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            RETURNING tag_id
        """, (user_id, book_id, tag_text))

        # Retrieve The Newly Generated Tag ID.
        tag_id = cur.fetchone()[0]

        # Commit The Transaction To Save The Changes.
        conn.commit()

        # Return The ID Of The Created Tag.
        return tag_id

    except psycopg2.errors.UniqueViolation:
        # A Unique Constraint Violation Occurs If The Same Tag Already Exists
        # For This User And Book Combination.
        # Rollback The Transaction To Avoid Partial Changes.
        conn.rollback()
        # Return None To Indicate That The Tag Already Exists.
        return None

    finally:
        # Ensure The Cursor And Connection Are Closed To Free Resources.
        cur.close()
        conn.close()


def get_user_tags(user_id):
    """
    Retrieve All Tags Created By A Specific User.

    This Function Fetches All Tag Records For The Given User, Along With
    The Associated Book Title. Results Are Ordered By Creation Date In
    Descending Order (Most Recent Tags First).

    Parameters:
        user_id (int): The ID Of The User Whose Tags Are To Be Retrieved.

    Returns:
        list: A List Of Dictionaries, Each Containing The Tag ID, Book ID,
              Book Title, Tag Text, And Creation Date (ISO Format).
    """
    # Establish A Database Connection And Create A Cursor.
    conn = get_db_connection()
    cur = conn.cursor()

    # Execute The Query To Fetch The User's Tags.
    # This Query Joins The tags Table With The books Table To Retrieve
    # The Book Title. It Filters By The Given User ID And Orders By
    # Created Date Descending (Most Recent First).
    cur.execute("""
        SELECT t.tag_id, t.book_id, b.title, t.tag_text, t.created_at
        FROM tags t
        JOIN books b ON t.book_id = b.book_id
        WHERE t.user_id = %s
        ORDER BY t.created_at DESC
    """, (user_id,))

    # Fetch All Rows Returned By The Query.
    rows = cur.fetchall()

    # Close The Cursor And Database Connection To Free Resources.
    cur.close()
    conn.close()

    # Transform Each Row Into A Dictionary And Return The List.
    return [{
        "tag_id": r[0],
        "book_id": r[1],
        "book_title": r[2],
        "tag": r[3],
        "created_at": r[4].isoformat() if r[4] else None
    } for r in rows]


def delete_tag(tag_id, user_id):
    """
    Delete A Specific Tag Created By A Given User.

    This Function Removes A Tag From The Database Only If The Tag ID
    Matches And The User ID Matches (Ownership Check). This Prevents
    Users From Deleting Tags Created By Other Users.

    Parameters:
        tag_id (int): The ID Of The Tag To Be Deleted.
        user_id (int): The ID Of The User Attempting To Delete The Tag.

    Returns:
        bool: True If The Tag Was Successfully Deleted, False Otherwise.
    """
    # Establish A Database Connection And Create A Cursor.
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Delete The Tag With The Given Tag ID And User ID.
        # The DELETE Statement Includes Both Conditions To Ensure Ownership.
        # The RETURNING Clause Helps Verify If A Row Was Actually Deleted.
        cur.execute("""
            DELETE FROM tags
            WHERE tag_id = %s AND user_id = %s
            RETURNING tag_id
        """, (tag_id, user_id))

        # Check If Any Row Was Deleted.
        deleted = cur.fetchone() is not None

        # Commit The Transaction To Save The Changes.
        conn.commit()

        # Return True If A Row Was Deleted, Else False.
        return deleted

    finally:
        # Ensure The Cursor And Connection Are Closed To Free Resources.
        cur.close()
        conn.close()