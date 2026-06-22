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


def create_list(user_id, list_name):
    """
    Create A New Reading List For A Specific User.

    This Function Inserts A New Record Into The lists Table With The
    Given User ID And List Name. The Creation Timestamp Is Automatically
    Set To The Current Time.

    Parameters:
        user_id (int): The ID Of The User Creating The List.
        list_name (str): The Name Of The New List.

    Returns:
        int: The ID Of The Newly Created List.
    """
    # Establish A Database Connection And Create A Cursor.
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Insert The New List Record And Retrieve The Generated list_id.
        # The RETURNING Clause Returns The ID Of The Newly Inserted Row.
        cur.execute("""
            INSERT INTO lists (user_id, list_name, created_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            RETURNING list_id
        """, (user_id, list_name))

        # Fetch The Returned List ID.
        list_id = cur.fetchone()[0]

        # Commit The Transaction To Save The Changes.
        conn.commit()

        # Return The Newly Created List ID.
        return list_id

    finally:
        # Ensure The Cursor And Connection Are Closed To Free Resources.
        cur.close()
        conn.close()


def get_user_lists(user_id):
    """
    Retrieve All Reading Lists Created By A Specific User.

    This Function Fetches All Lists Belonging To The Given User,
    Ordered By Creation Date In Descending Order (Most Recent First).

    Parameters:
        user_id (int): The ID Of The User Whose Lists Are To Be Retrieved.

    Returns:
        list: A List Of Dictionaries, Each Containing The List ID,
              List Name, And Creation Date (ISO Format).
    """
    # Establish A Database Connection And Create A Cursor.
    conn = get_db_connection()
    cur = conn.cursor()

    # Execute The Query To Fetch The User's Lists.
    # The Query Filters By User ID And Orders By created_at Descending.
    cur.execute("""
        SELECT list_id, list_name, created_at
        FROM lists
        WHERE user_id = %s
        ORDER BY created_at DESC
    """, (user_id,))

    # Fetch All Rows Returned By The Query.
    rows = cur.fetchall()

    # Close The Cursor And Database Connection To Free Resources.
    cur.close()
    conn.close()

    # Transform Each Row Into A Dictionary And Return The List.
    return [{
        "list_id": r[0],
        "list_name": r[1],
        "created_at": r[2].isoformat() if r[2] else None
    } for r in rows]


def delete_list(list_id, user_id):
    """
    Delete A Specific Reading List If It Belongs To The Given User.

    This Function Removes A List From The Database Only If The
    List ID Matches And The User ID Matches (Ownership Check).

    Parameters:
        list_id (int): The ID Of The List To Be Deleted.
        user_id (int): The ID Of The User Attempting To Delete.

    Returns:
        bool: True If The List Was Successfully Deleted, False Otherwise.
    """
    # Establish A Database Connection And Create A Cursor.
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Delete The List With The Given ID And User ID.
        # The RETURNING Clause Helps Verify If A Row Was Actually Deleted.
        cur.execute("""
            DELETE FROM lists
            WHERE list_id = %s AND user_id = %s
            RETURNING list_id
        """, (list_id, user_id))

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


def rename_list(list_id, user_id, new_name):
    """
    Rename An Existing Reading List If It Belongs To The Given User.

    This Function Updates The List Name Only If The List ID And
    User ID Match (Ownership Check).

    Parameters:
        list_id (int): The ID Of The List To Be Renamed.
        user_id (int): The ID Of The User Attempting To Rename.
        new_name (str): The New Name For The List.

    Returns:
        bool: True If The List Was Successfully Renamed, False Otherwise.
    """
    # Establish A Database Connection And Create A Cursor.
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Update The List Name With The New Value.
        # The UPDATE Statement Includes Both list_id And user_id For Security.
        cur.execute("""
            UPDATE lists
            SET list_name = %s
            WHERE list_id = %s AND user_id = %s
            RETURNING list_id
        """, (new_name, list_id, user_id))

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


def add_list_item(list_id, user_id, book_id):
    """
    Add A Book To A Specific Reading List.

    This Function First Verifies That The List Belongs To The Given User,
    Then Inserts A New Entry Into The list_items Table. A Unique Constraint
    Prevents Adding The Same Book Twice To The Same List.

    Parameters:
        list_id (int): The ID Of The List To Which The Book Should Be Added.
        user_id (int): The ID Of The User (For Ownership Verification).
        book_id (int): The ID Of The Book To Be Added.

    Returns:
        bool: True If The Book Was Successfully Added, False If The List
              Was Not Found, Does Not Belong To The User, Or The Book Is
              Already In The List.
    """
    # Establish A Database Connection And Create A Cursor.
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Verify That The List Belongs To The Given User.
        # This Prevents Users From Adding Items To Lists They Do Not Own.
        cur.execute("""
            SELECT list_id
            FROM lists
            WHERE list_id = %s AND user_id = %s
        """, (list_id, user_id))

        if not cur.fetchone():
            # List Not Found Or Does Not Belong To The User.
            return False

        # Insert The Book Into The List.
        # The added_at Timestamp Is Automatically Set To The Current Time.
        cur.execute("""
            INSERT INTO list_items (list_id, book_id, added_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            RETURNING list_item_id
        """, (list_id, book_id))

        # Commit The Transaction To Save The Changes.
        conn.commit()

        # Return True To Indicate Success.
        return True

    except psycopg2.errors.UniqueViolation:
        # A Unique Constraint Violation Occurs If The Book Is Already In The List.
        # Rollback The Transaction To Avoid Partial Changes.
        conn.rollback()
        # Return False To Indicate That The Operation Failed.
        return False

    finally:
        # Ensure The Cursor And Connection Are Closed To Free Resources.
        cur.close()
        conn.close()


def remove_list_item(list_id, user_id, book_id):
    """
    Remove A Book From A Specific Reading List.

    This Function Deletes The Entry From The list_items Table Only If
    The List Belongs To The Given User (Verified Through A JOIN With
    The lists Table).

    Parameters:
        list_id (int): The ID Of The List From Which The Book Should Be Removed.
        user_id (int): The ID Of The User (For Ownership Verification).
        book_id (int): The ID Of The Book To Be Removed.

    Returns:
        bool: True If The Book Was Successfully Removed, False Otherwise.
    """
    # Establish A Database Connection And Create A Cursor.
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Delete The List Item Using A JOIN To Ensure Ownership.
        # The DELETE Statement Uses The lists Table To Verify That The
        # Specified List Belongs To The Given User.
        cur.execute("""
            DELETE FROM list_items
            USING lists
            WHERE list_items.list_id = lists.list_id
              AND lists.list_id = %s
              AND lists.user_id = %s
              AND list_items.book_id = %s
        """, (list_id, user_id, book_id))

        # Check How Many Rows Were Affected.
        rows_deleted = cur.rowcount

        # Commit The Transaction To Save The Changes.
        conn.commit()

        # Return True If At Least One Row Was Deleted.
        return rows_deleted > 0

    finally:
        # Ensure The Cursor And Connection Are Closed To Free Resources.
        cur.close()
        conn.close()


def get_list_items(list_id, user_id):
    """
    Retrieve All Books In A Specific Reading List.

    This Function Fetches Book Details (ID, Title, ISBN, Publisher, And
    The Date Added) For A Given List. It Ensures That The List Belongs To
    The Specified User.

    Parameters:
        list_id (int): The ID Of The List Whose Items Are To Be Retrieved.
        user_id (int): The ID Of The User (For Ownership Verification).

    Returns:
        list: A List Of Dictionaries, Each Containing The Book ID, Title,
              ISBN, Publisher, And The Date Added (ISO Format).
    """
    # Establish A Database Connection And Create A Cursor.
    conn = get_db_connection()
    cur = conn.cursor()

    # Execute The Query To Fetch The List Items.
    # This Query Joins The list_items, books, And lists Tables To Retrieve
    # Book Details And Ensure The List Belongs To The Given User.
    # The Results Are Ordered By The Date Added In Descending Order.
    cur.execute("""
        SELECT b.book_id, b.title, b.isbn, b.publisher, li.added_at
        FROM list_items li
        JOIN books b ON li.book_id = b.book_id
        JOIN lists l ON li.list_id = l.list_id
        WHERE l.list_id = %s AND l.user_id = %s
        ORDER BY li.added_at DESC
    """, (list_id, user_id))

    # Fetch All Rows Returned By The Query.
    rows = cur.fetchall()

    # Close The Cursor And Database Connection To Free Resources.
    cur.close()
    conn.close()

    # Transform Each Row Into A Dictionary And Return The List.
    return [{
        "book_id": r[0],
        "title": r[1],
        "isbn": r[2],
        "publisher": r[3],
        "added_at": r[4].isoformat() if r[4] else None
    } for r in rows]