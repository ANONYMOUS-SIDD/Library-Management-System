import psycopg2
from datetime import datetime
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


def place_hold(user_id, book_id):
    """
    Place A Hold On A Specific Book For A Given User.

    This Function Inserts A New Hold Record With Status 'active' After
    Verifying That The User Does Not Already Have An Active Or Fulfilled
    Hold On The Same Book.

    Parameters:
        user_id (int): The ID Of The User Placing The Hold.
        book_id (int): The ID Of The Book To Be Reserved.

    Returns:
        int: The ID Of The Newly Created Hold Record.

    Raises:
        ValueError: If The User Already Has An Active Or Fulfilled Hold
                    On The Specified Book.
    """
    # Establish A Database Connection And Create A Cursor.
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Check If The User Already Has An Active Or Fulfilled Hold On This Book.
        # This Prevents Duplicate Holds On The Same Book By The Same User.
        cur.execute("""
            SELECT hold_id
            FROM holds
            WHERE user_id = %s AND book_id = %s AND status IN ('active', 'fulfilled')
        """, (user_id, book_id))

        if cur.fetchone():
            raise ValueError("You already have an active hold on this book")

        # Insert A New Hold Record With Status 'active' And The Current Timestamp.
        # The RETURNING Clause Returns The Generated hold_id.
        cur.execute("""
            INSERT INTO holds (user_id, book_id, request_date, status)
            VALUES (%s, %s, CURRENT_TIMESTAMP, 'active')
            RETURNING hold_id
        """, (user_id, book_id))

        # Retrieve The Newly Created Hold ID.
        hold_id = cur.fetchone()[0]

        # Commit The Transaction To Save The Changes.
        conn.commit()

        # Return The ID Of The Placed Hold.
        return hold_id

    except Exception as e:
        # Rollback The Transaction In Case Of Any Error.
        conn.rollback()
        # Re-Raise The Exception So The Caller Can Handle It.
        raise e

    finally:
        # Ensure The Cursor And Connection Are Closed To Free Resources.
        cur.close()
        conn.close()


def get_user_holds(user_id):
    """
    Retrieve All Holds (Active, Fulfilled, Or Cancelled) For A Specific User.

    This Function Fetches Hold Records Along With The Associated Book Title
    And Orders Them By Request Date In Descending Order (Most Recent First).

    Parameters:
        user_id (int): The ID Of The User Whose Holds Are To Be Retrieved.

    Returns:
        list: A List Of Dictionaries, Each Containing The Hold ID, Book ID,
              Book Title, Request Date (ISO Format), And Status.
    """
    # Establish A Database Connection And Create A Cursor.
    conn = get_db_connection()
    cur = conn.cursor()

    # Execute The Query To Fetch The User's Holds.
    # This Query Joins The holds Table With The books Table To Retrieve
    # The Book Title. It Filters By The Given User ID And Orders By
    # Request Date Descending.
    cur.execute("""
        SELECT h.hold_id, h.book_id, b.title, h.request_date, h.status
        FROM holds h
        JOIN books b ON h.book_id = b.book_id
        WHERE h.user_id = %s
        ORDER BY h.request_date DESC
    """, (user_id,))

    # Fetch All Rows Returned By The Query.
    rows = cur.fetchall()

    # Close The Cursor And Database Connection To Free Resources.
    cur.close()
    conn.close()

    # Transform Each Row Into A Dictionary And Return The List.
    return [{
        'hold_id': r[0],
        'book_id': r[1],
        'book_title': r[2],
        'request_date': r[3].isoformat() if r[3] else None,
        'status': r[4]
    } for r in rows]


def get_all_pending_holds():
    """
    Retrieve All Active Holds Across All Users (Librarian View).

    This Function Fetches All Holds With Status 'active', Along With The
    User Name And Book Title, Ordered By Request Date Ascending (Oldest
    First). It Is Typically Used By Librarians To View All Pending
    Hold Requests.

    Returns:
        list: A List Of Dictionaries, Each Containing The Hold ID, User ID,
              User Name, Book ID, Book Title, And Request Date (ISO Format).
    """
    # Establish A Database Connection And Create A Cursor.
    conn = get_db_connection()
    cur = conn.cursor()

    # Execute The Query To Fetch All Pending Holds.
    # This Query Joins The holds Table With The users And books Tables To
    # Retrieve The User Name And Book Title. It Filters For Status 'active'
    # And Orders By Request Date Ascending (Oldest First).
    cur.execute("""
        SELECT h.hold_id, h.user_id, u.name AS user_name, h.book_id, b.title, h.request_date
        FROM holds h
        JOIN users u ON h.user_id = u.user_id
        JOIN books b ON h.book_id = b.book_id
        WHERE h.status = 'active'
        ORDER BY h.request_date ASC
    """)

    # Fetch All Rows Returned By The Query.
    rows = cur.fetchall()

    # Close The Cursor And Database Connection To Free Resources.
    cur.close()
    conn.close()

    # Transform Each Row Into A Dictionary And Return The List.
    return [{
        'hold_id': r[0],
        'user_id': r[1],
        'user_name': r[2],
        'book_id': r[3],
        'book_title': r[4],
        'request_date': r[5].isoformat() if r[5] else None
    } for r in rows]


def fulfill_hold(hold_id):
    """
    Mark A Hold As Fulfilled (Ready For Pickup).

    This Function Updates The Status Of A Hold From 'active' To 'fulfilled'.
    It Can Only Be Performed On Holds That Are Currently Active.

    Parameters:
        hold_id (int): The ID Of The Hold To Be Fulfilled.

    Raises:
        ValueError: If The Hold Does Not Exist Or Is Not In 'active' Status.
    """
    # Establish A Database Connection And Create A Cursor.
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Update The Hold Status To 'fulfilled' Only If It Is Currently 'active'.
        # The RETURNING Clause Is Used To Check If Any Row Was Updated.
        cur.execute("""
            UPDATE holds
            SET status = 'fulfilled'
            WHERE hold_id = %s AND status = 'active'
            RETURNING hold_id
        """, (hold_id,))

        # If No Row Was Updated, Raise An Error.
        if cur.rowcount == 0:
            raise ValueError("Hold not found or not active")

        # Commit The Transaction To Save The Changes.
        conn.commit()

    except Exception as e:
        # Rollback The Transaction In Case Of Any Error.
        conn.rollback()
        # Re-Raise The Exception So The Caller Can Handle It.
        raise e

    finally:
        # Ensure The Cursor And Connection Are Closed To Free Resources.
        cur.close()
        conn.close()


def cancel_hold(hold_id):
    """
    Cancel A Hold (Set Status To 'cancelled').

    This Function Updates The Status Of A Hold To 'cancelled'. It Can Be
    Applied To Holds That Are Either 'active' Or 'fulfilled'.

    Parameters:
        hold_id (int): The ID Of The Hold To Be Cancelled.

    Raises:
        ValueError: If The Hold Does Not Exist Or Is Already Cancelled.
    """
    # Establish A Database Connection And Create A Cursor.
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Update The Hold Status To 'cancelled' Only If It Is Currently
        # 'active' Or 'fulfilled'. The RETURNING Clause Checks For Success.
        cur.execute("""
            UPDATE holds
            SET status = 'cancelled'
            WHERE hold_id = %s AND status IN ('active', 'fulfilled')
            RETURNING hold_id
        """, (hold_id,))

        # If No Row Was Updated, Raise An Error.
        if cur.rowcount == 0:
            raise ValueError("Hold not found or already cancelled")

        # Commit The Transaction To Save The Changes.
        conn.commit()

    except Exception as e:
        # Rollback The Transaction In Case Of Any Error.
        conn.rollback()
        # Re-Raise The Exception So The Caller Can Handle It.
        raise e

    finally:
        # Ensure The Cursor And Connection Are Closed To Free Resources.
        cur.close()
        conn.close()