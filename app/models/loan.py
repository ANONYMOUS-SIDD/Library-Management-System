"""
Loan Management Module For The Library Management System.

This Module Handles All Operations Related To Book Loans, Including
Creating New Loans, Returning Books, Renewing Loans, And Retrieving
Active Loans For A User.
"""

import psycopg2
from datetime import datetime, timedelta
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


def get_active_loans(user_id):
    """
    Retrieve All Currently Active Loans For A Specific User.

    This Function Fetches All Loans That Have Not Been Returned
    (return_date IS NULL) For The Given User. It Includes Book Details,
    Author Information, Copy Barcode, Shelf Location, And Fine Amounts.

    Parameters:
        user_id (int): The ID Of The User Whose Active Loans Are To Be Retrieved.

    Returns:
        list: A List Of Dictionaries, Each Containing Loan Details Such As
              Loan ID, Book Title, Author, Checkout Date, Due Date,
              Renewal Count, Fine Amount, Barcode, And Shelf Location.
    """
    # Establish A Database Connection And Create A Cursor.
    conn = get_db_connection()
    cur = conn.cursor()

    # Execute The Query To Fetch Active Loans For The User.
    # This Query Joins Multiple Tables:
    #   - loans: The Main Loan Record.
    #   - copies: To Get Copy Details (Barcode, Shelf Location).
    #   - books: To Get Book Title.
    #   - book_authors And authors: To Retrieve Author Name(s).
    # The Query Filters For The Given User ID And Only Loans With
    # return_date IS NULL (Active Loans). Results Are Ordered By
    # Due Date In Ascending Order (Soonest Due Date First).
    cur.execute("""
        SELECT 
            l.loan_id,
            b.title,
            a.name AS author,
            l.checkout_date,
            l.due_date,
            l.renewal_count,
            l.fine_amount,
            c.barcode,
            c.shelf_location
        FROM loans l
        JOIN copies c ON l.copy_id = c.copy_id
        JOIN books b ON c.book_id = b.book_id
        LEFT JOIN book_authors ba ON b.book_id = ba.book_id
        LEFT JOIN authors a ON ba.author_id = a.author_id
        WHERE l.user_id = %s AND l.return_date IS NULL
        ORDER BY l.due_date ASC
    """, (user_id,))

    # Fetch All Rows Returned By The Query.
    loans = cur.fetchall()

    # Close The Cursor And Database Connection To Free Resources.
    cur.close()
    conn.close()

    # Transform Each Row Into A Dictionary For Easier JSON Serialization.
    result = []
    for row in loans:
        result.append({
            'loan_id': row[0],
            'title': row[1],
            'author': row[2] or 'Unknown',  # If No Author, Default To 'Unknown'.
            'checkout_date': row[3].isoformat() if row[3] else None,
            'due_date': row[4].isoformat() if row[4] else None,
            'renewal_count': row[5],
            'fine_amount': float(row[6]) if row[6] else 0.0,
            'barcode': row[7],
            'shelf_location': row[8]
        })

    # Return The List Of Active Loans.
    return result


def create_loan(user_id, copy_id, due_date_days=14):
    """
    Create A New Loan (Checkout) For A User.

    This Function Checks Out A Copy To A User By Inserting A New Loan
    Record And Updating The Copy Status To 'checked out'. It Uses Row
    Level Locking (FOR UPDATE) To Prevent Race Conditions During Checkout.

    Parameters:
        user_id (int): The ID Of The User Borrowing The Book.
        copy_id (int): The ID Of The Copy Being Borrowed.
        due_date_days (int): Number Of Days From Today For The Due Date
                             (Default 14 Days).

    Returns:
        int: The ID Of The Newly Created Loan.

    Raises:
        ValueError: If The Copy Does Not Exist Or Is Not Available.
    """
    # Establish A Database Connection And Create A Cursor.
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Lock The Copy Row To Prevent Concurrent Checkouts.
        # The FOR UPDATE Clause Ensures Other Transactions Cannot Modify
        # This Row Until The Current Transaction Is Committed.
        cur.execute("SELECT status FROM copies WHERE copy_id = %s FOR UPDATE", (copy_id,))
        row = cur.fetchone()

        # Check If The Copy Exists.
        if not row:
            raise ValueError("Copy not found")

        # Verify That The Copy Is Available For Checkout.
        if row[0] != 'available':
            raise ValueError("Copy is not available")

        # Calculate The Due Date By Adding The Specified Number Of Days.
        due_date = datetime.now() + timedelta(days=due_date_days)

        # Insert A New Loan Record With The Current Date As Checkout Date.
        # The checkout_date Is Set To CURRENT_DATE (Today's Date).
        # The renewal_count Is Set To 0 For A New Loan.
        cur.execute("""
            INSERT INTO loans (user_id, copy_id, checkout_date, due_date, renewal_count)
            VALUES (%s, %s, CURRENT_DATE, %s, 0)
            RETURNING loan_id
        """, (user_id, copy_id, due_date))

        # Retrieve The Newly Generated Loan ID.
        loan_id = cur.fetchone()[0]

        # Update The Copy Status To 'checked out'.
        cur.execute("UPDATE copies SET status = 'checked out' WHERE copy_id = %s", (copy_id,))

        # Commit The Transaction To Save All Changes.
        conn.commit()

        # Return The ID Of The Created Loan.
        return loan_id

    except Exception as e:
        # Rollback The Transaction In Case Of Any Error.
        conn.rollback()
        # Re-Raise The Exception So The Caller Can Handle It.
        raise e

    finally:
        # Ensure The Cursor And Connection Are Closed To Free Resources.
        cur.close()
        conn.close()


def return_loan(loan_id):
    """
    Process The Return Of A Loan.

    This Function Marks A Loan As Returned By Setting The return_date
    To Today's Date. It Calculates Any Late Fines Based On The Due Date
    And Updates The Copy Status Back To 'available'.

    Parameters:
        loan_id (int): The ID Of The Loan Being Returned.

    Returns:
        float: The Fine Amount Calculated (0.0 If No Fine).

    Raises:
        ValueError: If The Loan Does Not Exist Or Is Already Returned.
    """
    # Establish A Database Connection And Create A Cursor.
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Retrieve Loan Details Including Copy ID, Due Date, And Existing Fine.
        # The Query Only Returns Loans That Are Not Yet Returned.
        cur.execute("""
            SELECT copy_id, due_date, fine_amount
            FROM loans
            WHERE loan_id = %s AND return_date IS NULL
        """, (loan_id,))

        loan = cur.fetchone()

        # Check If The Loan Exists And Is Not Already Returned.
        if not loan:
            raise ValueError("Loan not found or already returned")

        # Extract The Retrieved Values.
        copy_id, due_date, current_fine = loan

        # Calculate Fine For Overdue Returns.
        # The Fine Is Calculated At $0.50 Per Day Overdue.
        # If The Return Date Is On Or Before The Due Date, No Fine Is Applied.
        today = datetime.now().date()
        fine = 0.0
        if today > due_date:
            days_overdue = (today - due_date).days
            fine = days_overdue * 0.50  # $0.50 Per Day Overdue.

        # Update The Loan Record With Return Date And Fine Amount.
        cur.execute("""
            UPDATE loans
            SET return_date = CURRENT_DATE, fine_amount = %s
            WHERE loan_id = %s
        """, (fine, loan_id))

        # Update The Copy Status Back To 'available'.
        cur.execute("UPDATE copies SET status = 'available' WHERE copy_id = %s", (copy_id,))

        # Commit The Transaction To Save All Changes.
        conn.commit()

        # Return The Calculated Fine Amount.
        return fine

    except Exception as e:
        # Rollback The Transaction In Case Of Any Error.
        conn.rollback()
        # Re-Raise The Exception So The Caller Can Handle It.
        raise e

    finally:
        # Ensure The Cursor And Connection Are Closed To Free Resources.
        cur.close()
        conn.close()


def renew_loan(loan_id, user_id):
    """
    Renew An Active Loan For A User.

    This Function Extends The Due Date Of A Loan By 14 Days If The
    Loan Is Eligible For Renewal. Renewal Is Allowed Only If:
        1. The Loan Belongs To The Specified User.
        2. The Loan Is Currently Active (Not Returned).
        3. The Renewal Count Is Less Than 3.
        4. There Are No Active Holds On The Book.

    Parameters:
        loan_id (int): The ID Of The Loan To Be Renewed.
        user_id (int): The ID Of The User Requesting The Renewal.

    Returns:
        date: The New Due Date After Renewal.

    Raises:
        ValueError: If The Loan Is Not Found, Already Returned,
                    Does Not Belong To The User, Maximum Renewals Exceeded,
                    Or The Book Has Active Holds.
    """
    # Establish A Database Connection And Create A Cursor.
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Retrieve Loan Details For The Specified Loan ID And User ID.
        # Only Active Loans (return_date IS NULL) Are Considered.
        cur.execute("""
            SELECT due_date, renewal_count, copy_id
            FROM loans
            WHERE loan_id = %s AND user_id = %s AND return_date IS NULL
        """, (loan_id, user_id))

        loan = cur.fetchone()

        # Check If The Loan Exists, Is Active, And Belongs To The User.
        if not loan:
            raise ValueError("Loan not found, already returned, or not yours")

        # Extract The Retrieved Values.
        due_date, renewal_count, copy_id = loan

        # Enforce The Maximum Renewal Limit (3 Renewals Allowed).
        if renewal_count >= 3:
            raise ValueError("Maximum renewals reached")

        # Check For Active Holds On The Book.
        # If There Are Active Holds, The Loan Cannot Be Renewed.
        cur.execute("""
            SELECT hold_id
            FROM holds
            WHERE book_id = (SELECT book_id FROM copies WHERE copy_id = %s)
              AND status = 'active'
        """, (copy_id,))

        if cur.fetchone():
            raise ValueError("Cannot renew: book has active holds")

        # Calculate The New Due Date By Adding 14 Days To The Current Due Date.
        new_due_date = due_date + timedelta(days=14)

        # Update The Loan With The New Due Date And Increment The Renewal Count.
        cur.execute("""
            UPDATE loans
            SET due_date = %s, renewal_count = renewal_count + 1
            WHERE loan_id = %s
            RETURNING loan_id
        """, (new_due_date, loan_id))

        # Commit The Transaction To Save The Changes.
        conn.commit()

        # Return The New Due Date.
        return new_due_date

    finally:
        # Ensure The Cursor And Connection Are Closed To Free Resources.
        cur.close()
        conn.close()