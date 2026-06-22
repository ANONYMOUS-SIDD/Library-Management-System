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


def search_books(query, limit=20):
    """
    Search For Books By Title, ISBN, Or Author Name.

    This Function Performs A Case-Insensitive Search Across Multiple Columns
    And Returns A List Of Books With Their Details, Including The Number Of
    Available Copies And A Comma-Separated List Of Authors.

    Parameters:
        query (str): The Search Term Entered By The User.
        limit (int): Maximum Number Of Results To Return (Default 20).

    Returns:
        list: A List Of Dictionaries, Each Representing A Book With The
              Following Keys: book_id, title, isbn, publisher,
              published_date, location, total_copies, available_copies,
              authors.
    """
    # Establish A Database Connection And Create A Cursor.
    conn = get_db_connection()
    cur = conn.cursor()

    # Prepare The Search Pattern For ILIKE (Case-Insensitive Partial Match).
    search_term = f"%{query}%"

    # Execute The Main Search Query.
    # This Query Selects Distinct Books To Avoid Duplicates When A Book Has
    # Multiple Authors.
    # It Uses A Subquery To Count The Number Of Available Copies For Each Book.
    # The STRING_AGG Function Concatenates All Author Names Into A Single
    # Comma-Separated String.
    # The Query Joins The books Table With book_authors And authors Tables To
    # Retrieve Author Names.
    # The Search Conditions Check If The Title, ISBN, Or Any Author Name
    # Matches The Search Term (Case-Insensitive).
    # The Results Are Grouped By book_id To Aggregate Author Names Correctly,
    # Ordered By Title Alphabetically, And Limited To The Specified Number.
    cur.execute("""
        SELECT DISTINCT
            b.book_id,
            b.title,
            b.isbn,
            b.publisher,
            b.published_date,
            b.location,
            b.total_copies,
            (SELECT COUNT(*) FROM copies c WHERE c.book_id = b.book_id AND c.status = 'available') AS available_copies,
            STRING_AGG(a.name, ', ') AS authors
        FROM books b
        LEFT JOIN book_authors ba ON b.book_id = ba.book_id
        LEFT JOIN authors a ON ba.author_id = a.author_id
        WHERE b.title ILIKE %s
           OR b.isbn ILIKE %s
           OR EXISTS (
                SELECT 1 FROM book_authors ba2 
                JOIN authors a2 ON ba2.author_id = a2.author_id 
                WHERE ba2.book_id = b.book_id AND a2.name ILIKE %s
              )
        GROUP BY b.book_id
        ORDER BY b.title
        LIMIT %s
    """, (search_term, search_term, search_term, limit))

    # Fetch All Rows Returned By The Query.
    rows = cur.fetchall()

    # Close The Cursor And Database Connection To Free Resources.
    cur.close()
    conn.close()

    # Transform Each Database Row Into A Dictionary For Easier JSON Serialization.
    result = []
    for row in rows:
        result.append({
            'book_id': row[0],
            'title': row[1],
            'isbn': row[2],
            'publisher': row[3],
            'published_date': row[4].isoformat() if row[4] else None,
            'location': row[5],
            'total_copies': row[6],
            'available_copies': row[7] or 0,
            'authors': row[8] or ''
        })

    # Return The List Of Book Dictionaries.
    return result