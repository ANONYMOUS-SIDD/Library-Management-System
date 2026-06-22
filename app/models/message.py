"""
Messaging Module For The Library Management System.

This Module Handles All Operations Related To User Messages And Notifications,
Including Sending Messages, Retrieving User Messages, And Marking Messages As Read.
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


def send_message(user_id, sender, subject, body):
    """
    Send A New Message To A Specific User.

    This Function Inserts A New Record Into The messages Table With The
    Provided Details. The Sent Date Is Automatically Set To The Current
    Timestamp And The Message Is Initially Marked As Unread.

    Parameters:
        user_id (int): The ID Of The Recipient User.
        sender (str): The Sender Identifier (E.g., 'System' Or 'Librarian Name').
        subject (str): The Subject Line Of The Message.
        body (str): The Full Content Of The Message.

    Returns:
        int: The ID Of The Newly Created Message.
    """
    # Establish A Database Connection And Create A Cursor.
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Insert The New Message Record.
        # The sent_date Is Set To CURRENT_TIMESTAMP (Current Date And Time).
        # The is_read Flag Is Set To False By Default.
        cur.execute("""
            INSERT INTO messages (user_id, sender, subject, body, sent_date, is_read)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, false)
            RETURNING message_id
        """, (user_id, sender, subject, body))

        # Retrieve The Newly Generated Message ID.
        msg_id = cur.fetchone()[0]

        # Commit The Transaction To Save The Changes.
        conn.commit()

        # Return The ID Of The New Message.
        return msg_id

    finally:
        # Ensure The Cursor And Connection Are Closed To Free Resources.
        cur.close()
        conn.close()


def get_user_messages(user_id, unread_only=False):
    """
    Retrieve All Messages For A Specific User, Optionally Filtering By Read Status.

    This Function Fetches Messages From The messages Table For The Given User.
    If unread_only Is Set To True, Only Messages That Are Not Yet Read Are Returned.
    Results Are Ordered By Sent Date In Descending Order (Most Recent First).

    Parameters:
        user_id (int): The ID Of The User Whose Messages Are To Be Retrieved.
        unread_only (bool): If True, Return Only Unread Messages.
                            Default Is False (Return All Messages).

    Returns:
        list: A List Of Dictionaries, Each Containing The Message ID, Sender,
              Subject, Body, Sent Date (ISO Format), And Read Status.
    """
    # Establish A Database Connection And Create A Cursor.
    conn = get_db_connection()
    cur = conn.cursor()

    # Build The Base Query With Placeholder For The User ID.
    query = """
        SELECT message_id, sender, subject, body, sent_date, is_read
        FROM messages
        WHERE user_id = %s
    """
    params = [user_id]

    # Add Filter For Unread Messages If Requested.
    if unread_only:
        query += " AND is_read = false"

    # Order Results By Sent Date Descending (Newest First).
    query += " ORDER BY sent_date DESC"

    # Execute The Query With The Prepared Parameters.
    cur.execute(query, params)

    # Fetch All Rows Returned By The Query.
    rows = cur.fetchall()

    # Close The Cursor And Database Connection To Free Resources.
    cur.close()
    conn.close()

    # Transform Each Row Into A Dictionary And Return The List.
    return [{
        "id": r[0],
        "sender": r[1],
        "subject": r[2],
        "body": r[3],
        "sent_date": r[4].isoformat() if r[4] else None,
        "is_read": r[5]
    } for r in rows]


def mark_message_read(message_id, user_id):
    """
    Mark A Specific Message As Read For A Given User.

    This Function Updates The is_read Flag To True For The Specified
    Message ID, But Only If The Message Belongs To The Given User
    (Ownership Check).

    Parameters:
        message_id (int): The ID Of The Message To Mark As Read.
        user_id (int): The ID Of The User Who Owns The Message.

    Returns:
        bool: True If The Message Was Successfully Updated, False Otherwise.
    """
    # Establish A Database Connection And Create A Cursor.
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Update The Message's is_read Flag To True.
        # The Update Includes Both message_id And user_id For Security,
        # Ensuring That Only The Owner Can Mark Their Own Message As Read.
        cur.execute("""
            UPDATE messages
            SET is_read = true
            WHERE message_id = %s AND user_id = %s
            RETURNING message_id
        """, (message_id, user_id))

        # Check If Any Row Was Updated.
        updated = cur.fetchone() is not None

        # Commit The Transaction To Save The Changes.
        conn.commit()

        # Return True If A Row Was Updated, Else False.
        return updated

    finally:
        # Ensure The Cursor And Connection Are Closed To Free Resources.
        cur.close()
        conn.close()