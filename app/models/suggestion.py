"""
Purchase Suggestions Module For The Library Management System.

This Module Handles All Operations Related To Book Purchase Suggestions
Submitted By Users, Including Creating Suggestions, Retrieving User
Suggestions, Viewing All Suggestions (Librarian), And Updating Suggestion
Status.
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


def create_suggestion(user_id, title, author, notes):
    """
    Submit A New Purchase Suggestion By A User.

    This Function Inserts A New Record Into The suggestions Table With
    The Given Details. The Status Is Automatically Set To 'pending' And
    The Submission Date Is Set To The Current Timestamp.

    Parameters:
        user_id (int): The ID Of The User Submitting The Suggestion.
        title (str): The Title Of The Suggested Book.
        author (str): The Author Of The Suggested Book (Can Be None).
        notes (str): Additional Notes Or Comments Regarding The Suggestion.

    Returns:
        int: The ID Of The Newly Created Suggestion Record.
    """
    # Establish A Database Connection And Create A Cursor.
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Insert The Suggestion Record With Default Status 'pending'.
        # The submission_date Is Set To CURRENT_TIMESTAMP.
        # The RETURNING Clause Returns The Generated suggestion_id.
        cur.execute("""
            INSERT INTO suggestions (user_id, title, author, notes, status, submission_date)
            VALUES (%s, %s, %s, %s, 'pending', CURRENT_TIMESTAMP)
            RETURNING suggestion_id
        """, (user_id, title, author, notes))

        # Retrieve The Newly Generated Suggestion ID.
        suggestion_id = cur.fetchone()[0]

        # Commit The Transaction To Save The Changes.
        conn.commit()

        # Return The ID Of The Created Suggestion.
        return suggestion_id

    finally:
        # Ensure The Cursor And Connection Are Closed To Free Resources.
        cur.close()
        conn.close()


def get_user_suggestions(user_id):
    """
    Retrieve All Suggestions Submitted By A Specific User.

    This Function Fetches Suggestion Records From The suggestions Table
    For The Given User, Ordered By Submission Date In Descending Order
    (Most Recent First).

    Parameters:
        user_id (int): The ID Of The User Whose Suggestions Are To Be Retrieved.

    Returns:
        list: A List Of Dictionaries, Each Containing The Suggestion ID,
              Title, Author, Notes, Status, And Submission Date (ISO Format).
    """
    # Establish A Database Connection And Create A Cursor.
    conn = get_db_connection()
    cur = conn.cursor()

    # Execute The Query To Fetch The User's Suggestions.
    # The Query Filters By User ID And Orders By submission_date Descending.
    cur.execute("""
        SELECT suggestion_id, title, author, notes, status, submission_date
        FROM suggestions
        WHERE user_id = %s
        ORDER BY submission_date DESC
    """, (user_id,))

    # Fetch All Rows Returned By The Query.
    rows = cur.fetchall()

    # Close The Cursor And Database Connection To Free Resources.
    cur.close()
    conn.close()

    # Transform Each Row Into A Dictionary And Return The List.
    return [{
        "id": r[0],
        "title": r[1],
        "author": r[2],
        "notes": r[3],
        "status": r[4],
        "submitted": r[5].isoformat() if r[5] else None
    } for r in rows]


def get_all_suggestions():
    """
    Retrieve All Purchase Suggestions From All Users (Librarian View).

    This Function Fetches All Suggestion Records Along With The User Name
    Who Submitted Them. It Is Intended For Librarians To Review All
    Suggestions In One Place. Results Are Ordered By Submission Date In
    Descending Order (Most Recent First).

    Returns:
        list: A List Of Dictionaries, Each Containing The Suggestion ID,
              Title, Author, Notes, Status, Submission Date (ISO Format),
              And The User Name.
    """
    # Establish A Database Connection And Create A Cursor.
    conn = get_db_connection()
    cur = conn.cursor()

    # Execute The Query To Fetch All Suggestions With User Names.
    # This Query Joins The suggestions Table With The users Table To
    # Retrieve The Submitter's Name. Results Are Ordered By Submission
    # Date Descending.
    cur.execute("""
        SELECT s.suggestion_id, s.title, s.author, s.notes, s.status,
               s.submission_date, u.name AS user_name
        FROM suggestions s
        JOIN users u ON s.user_id = u.user_id
        ORDER BY s.submission_date DESC
    """)

    # Fetch All Rows Returned By The Query.
    rows = cur.fetchall()

    # Close The Cursor And Database Connection To Free Resources.
    cur.close()
    conn.close()

    # Transform Each Row Into A Dictionary And Return The List.
    return [{
        "id": r[0],
        "title": r[1],
        "author": r[2],
        "notes": r[3],
        "status": r[4],
        "submitted": r[5].isoformat() if r[5] else None,
        "user": r[6]
    } for r in rows]


def update_suggestion_status(suggestion_id, status, reviewer_id=None):
    """
    Update The Status Of A Purchase Suggestion (Librarian Only).

    This Function Updates The Status Of A Suggestion And Records The
    Librarian's ID Who Reviewed It. The Allowed Status Values Are:
    'pending', 'reviewed', 'approved', 'rejected'.

    Parameters:
        suggestion_id (int): The ID Of The Suggestion To Update.
        status (str): The New Status ('pending', 'reviewed', 'approved', 'rejected').
        reviewer_id (int, optional): The ID Of The Librarian Performing The Update.

    Returns:
        bool: True If The Update Was Successful, False If The Status Is Invalid
              Or The Suggestion Does Not Exist.
    """
    # Validate The Provided Status Against Allowed Values.
    if status not in ('pending', 'reviewed', 'approved', 'rejected'):
        return False

    # Establish A Database Connection And Create A Cursor.
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Update The Suggestion With The New Status And Reviewer ID.
        # The UPDATE Statement Uses The Suggestion ID To Identify The Record.
        # The RETURNING Clause Helps Verify If A Row Was Updated.
        cur.execute("""
            UPDATE suggestions
            SET status = %s, reviewed_by = %s
            WHERE suggestion_id = %s
            RETURNING suggestion_id
        """, (status, reviewer_id, suggestion_id))

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