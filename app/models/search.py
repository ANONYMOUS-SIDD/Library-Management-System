"""
Search History Module For The Library Management System.

This Module Handles All Operations Related To User Search History,
Including Recording Search Queries And Retrieving Past Searches For A User.
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


def add_search(user_id, query):
    """
    Record A Search Query Performed By A User.

    This Function Inserts A New Record Into The searches Table With The
    User ID, The Search Query Text, And The Current Timestamp. This Data
    Is Used To Populate The "Search History" Feature On The User's Account.

    Parameters:
        user_id (int): The ID Of The User Performing The Search.
        query (str): The Search Query Text Entered By The User.
    """
    # Establish A Database Connection And Create A Cursor.
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Insert The Search Record Into The searches Table.
        # The searched_at Column Is Automatically Set To The Current Timestamp.
        cur.execute("""
            INSERT INTO searches (user_id, query_text, searched_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
        """, (user_id, query))

        # Commit The Transaction To Save The Changes.
        conn.commit()

    finally:
        # Ensure The Cursor And Connection Are Closed To Free Resources.
        cur.close()
        conn.close()


def get_search_history(user_id, limit=20):
    """
    Retrieve The Recent Search History For A Specific User.

    This Function Fetches The Most Recent Search Queries Performed By
    The Given User, Ordered By The Search Timestamp In Descending Order
    (Most Recent First). The Number Of Results Can Be Limited Using The
    Limit Parameter (Default 20).

    Parameters:
        user_id (int): The ID Of The User Whose Search History Is To Be Retrieved.
        limit (int): Maximum Number Of Recent Searches To Return (Default 20).

    Returns:
        list: A List Of Dictionaries, Each Containing The Search ID,
              The Query Text, And The Timestamp (ISO Format).
    """
    # Establish A Database Connection And Create A Cursor.
    conn = get_db_connection()
    cur = conn.cursor()

    # Execute The Query To Fetch The User's Recent Search History.
    # The Query Filters By User ID, Orders By searched_at Descending,
    # And Limits The Number Of Results To The Specified Limit.
    cur.execute("""
        SELECT search_id, query_text, searched_at
        FROM searches
        WHERE user_id = %s
        ORDER BY searched_at DESC
        LIMIT %s
    """, (user_id, limit))

    # Fetch All Rows Returned By The Query.
    rows = cur.fetchall()

    # Close The Cursor And Database Connection To Free Resources.
    cur.close()
    conn.close()

    # Transform Each Row Into A Dictionary And Return The List.
    return [{
        "id": r[0],
        "query": r[1],
        "timestamp": r[2].isoformat() if r[2] else None
    } for r in rows]