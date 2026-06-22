"""
Flask Application Factory For The Library Management System.

This Module Initializes And Configures The Flask Application, Registers
All API Routes, And Sets Up Cross-Origin Resource Sharing (CORS) To
Allow Communication With Frontend Clients.
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
import bcrypt
import jwt
import datetime
from .config.config import Config
from .models.user import create_user, get_user_by_email, update_user_profile, change_user_password
from .models.loan import get_active_loans, create_loan, return_loan, renew_loan
from .models.book import search_books
from .models.hold import place_hold, get_user_holds, get_all_pending_holds, fulfill_hold, cancel_hold
from .models.search import add_search, get_search_history
from .models.list import create_list, get_user_lists, delete_list, rename_list, add_list_item, remove_list_item, get_list_items
from .models.tag import add_tag, get_user_tags, delete_tag
from .models.suggestion import create_suggestion, get_user_suggestions, get_all_suggestions, update_suggestion_status
from .models.message import send_message, get_user_messages, mark_message_read
from .utils.auth import get_user_from_token


def create_app():
    """
    Application Factory That Creates And Configures The Flask App Instance.

    This Function Sets Up The Flask Application, Enables CORS With
    Appropriate Settings, And Registers All API Endpoints For The
    Library Management System.

    Returns:
        Flask: The Configured Flask Application Instance.
    """
    app = Flask(__name__)

    # Enable CORS To Allow Requests From Any Origin With Specified Headers.
    # This Permits Frontend Applications To Interact With The API Securely.
    CORS(
        app,
        origins="*",
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    )

    # --------------------------------------------------------------
    # Health Check And Diagnostic Routes
    # --------------------------------------------------------------

    @app.route('/')
    def hello():
        """
        Root Endpoint To Verify That The API Is Running.

        Returns:
            str: A Simple Welcome Message.
        """
        return "Hello, Library Management System!"

    @app.route('/ping')
    def ping():
        """
        Ping Endpoint For Connectivity Testing.

        Returns:
            str: A Simple Pong Response.
        """
        return "pong"

    @app.route('/test-db')
    def test_db():
        """
        Database Connection Test Endpoint.

        Attempts To Connect To The PostgreSQL Database And Execute A
        Simple Query. Returns A Success Or Error Message.

        Returns:
            JSON: Status Message Indicating Database Connectivity.
        """
        try:
            conn = psycopg2.connect(
                host=Config.DB_HOST,
                port=Config.DB_PORT,
                database=Config.DB_NAME,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD
            )
            cur = conn.cursor()
            cur.execute('SELECT 1')
            cur.close()
            conn.close()
            return jsonify({"status": "Database connection successful!"})
        except Exception as e:
            return jsonify({"status": "Connection failed", "error": str(e)}), 500

    # --------------------------------------------------------------
    # Authentication Routes (Public)
    # --------------------------------------------------------------

    @app.route('/register', methods=['POST'])
    def register():
        """
        Register A New User.

        Accepts User Registration Data (Name, Email, Password, Role, Contact Info),
        Hashes The Password, And Creates A New User Record In The Database.

        Expected JSON Body:
            - name (str): Full Name Of The User.
            - email (str): Unique Email Address.
            - password (str): Plain-Text Password.
            - role (str, optional): 'student' Or 'librarian' (Default 'student').
            - contact_info (str, optional): Additional Contact Details.

        Returns:
            JSON: Success Message And User ID Or Error Message.
            Status Codes: 201 Created, 400 Bad Request, 409 Conflict.
        """
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')
        role = data.get('role', 'student')
        contact_info = data.get('contact_info')

        # Validate Required Fields.
        if not name or not email or not password:
            return jsonify({"error": "Name, email, and password are required"}), 400

        # Validate Role.
        if role not in ('student', 'librarian'):
            return jsonify({"error": "Role must be 'student' or 'librarian'"}), 400

        # Attempt To Create The User.
        user_id = create_user(name, email, password, role, contact_info)
        if user_id is None:
            return jsonify({"error": "Email already registered"}), 409

        return jsonify({"message": "User created successfully", "user_id": user_id}), 201

    @app.route('/login', methods=['POST'])
    def login():
        """
        Authenticate A User And Return A JWT Token.

        Verifies The Provided Email And Password, And If Valid, Generates
        A JSON Web Token (JWT) With A 24-Hour Expiration.

        Expected JSON Body:
            - email (str): User's Email Address.
            - password (str): User's Plain-Text Password.

        Returns:
            JSON: Login Success Message With Token And User Info,
                  Or Error Message.
            Status Codes: 200 OK, 400 Bad Request, 401 Unauthorized.
        """
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        # Validate Required Fields.
        if not email or not password:
            return jsonify({"error": "Email and password required"}), 400

        # Retrieve User From Database By Email.
        user = get_user_by_email(email)
        if not user:
            return jsonify({"error": "Invalid credentials"}), 401

        # Unpack The User Tuple.
        user_id, name, email, password_hash, role, photo_path, contact_info = user

        # Verify The Password Using Bcrypt.
        if not bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
            return jsonify({"error": "Invalid credentials"}), 401

        # Generate JWT Token With User Details And Expiration.
        payload = {
            'user_id': user_id,
            'email': email,
            'role': role,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }
        token = jwt.encode(payload, Config.JWT_SECRET, algorithm='HS256')

        # Return Token And User Info.
        return jsonify({
            "message": "Login successful",
            "token": token,
            "user": {"id": user_id, "name": name, "email": email, "role": role}
        }), 200

    # --------------------------------------------------------------
    # User Profile Routes (Authenticated)
    # --------------------------------------------------------------

    @app.route('/api/users/me', methods=['GET'])
    def get_profile():
        """
        Retrieve The Profile Of The Authenticated User.

        Requires A Valid JWT Token In The Authorization Header.

        Returns:
            JSON: User Profile Details (ID, Name, Email, Role, Photo, Contact Info).
            Status Codes: 200 OK, 401 Unauthorized, 404 Not Found.
        """
        # Extract And Decode The Token.
        user, err, code = get_user_from_token()
        if err:
            return jsonify(err), code

        # Fetch The Full User Profile From The Database.
        conn = psycopg2.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            database=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD
        )
        cur = conn.cursor()
        cur.execute("""
            SELECT user_id, name, email, role, photo_path, contact_info
            FROM users
            WHERE user_id = %s
        """, (user['user_id'],))
        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            return jsonify({"error": "User not found"}), 404

        return jsonify({
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "role": row[3],
            "photo_path": row[4],
            "contact_info": row[5]
        }), 200

    @app.route('/api/users/me', methods=['PUT'])
    def update_profile():
        """
        Update The Profile Of The Authenticated User.

        Allows Updating Name, Contact Information, And Photo Path.
        Requires A Valid JWT Token.

        Expected JSON Body (At Least One Field):
            - name (str, optional): New Name.
            - contact_info (str, optional): New Contact Details.
            - photo_path (str, optional): New Photo File Path.

        Returns:
            JSON: Success Message Or Error.
            Status Codes: 200 OK, 401 Unauthorized.
        """
        user, err, code = get_user_from_token()
        if err:
            return jsonify(err), code

        data = request.get_json()
        name = data.get('name')
        contact_info = data.get('contact_info')
        photo_path = data.get('photo_path')

        # Update The User Profile In The Database.
        update_user_profile(user['user_id'], name, contact_info, photo_path)

        return jsonify({"message": "Profile updated"}), 200

    @app.route('/api/users/me/password', methods=['PUT'])
    def change_password():
        """
        Change The Password Of The Authenticated User.

        Requires The Old Password For Verification And A New Password.
        Requires A Valid JWT Token.

        Expected JSON Body:
            - old_password (str): Current Password.
            - new_password (str): Desired New Password.

        Returns:
            JSON: Success Or Error Message.
            Status Codes: 200 OK, 400 Bad Request, 401 Unauthorized.
        """
        user, err, code = get_user_from_token()
        if err:
            return jsonify(err), code

        data = request.get_json()
        old_password = data.get('old_password')
        new_password = data.get('new_password')

        # Validate Required Fields.
        if not old_password or not new_password:
            return jsonify({"error": "Old and new password required"}), 400

        # Retrieve The Current Password Hash From The Database.
        conn = psycopg2.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            database=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD
        )
        cur = conn.cursor()
        cur.execute("SELECT password_hash FROM users WHERE user_id = %s", (user['user_id'],))
        row = cur.fetchone()
        cur.close()
        conn.close()

        # Verify The Old Password.
        if not row or not bcrypt.checkpw(old_password.encode('utf-8'), row[0].encode('utf-8')):
            return jsonify({"error": "Invalid old password"}), 401

        # Update The Password.
        change_user_password(user['user_id'], new_password)

        return jsonify({"message": "Password changed"}), 200

    # --------------------------------------------------------------
    # User Summary And History Routes (Authenticated)
    # --------------------------------------------------------------

    @app.route('/api/users/me/summary')
    def summary():
        """
        Get A Summary Of The Authenticated User's Active Loans.

        Retrieves All Loans That Have Not Been Returned, Including
        Book Details, Due Dates, And Fines. Requires A Valid JWT Token.

        Returns:
            JSON: List Of Active Loans And Total Count.
            Status Codes: 200 OK, 401 Unauthorized.
        """
        user, err, code = get_user_from_token()
        if err:
            return jsonify(err), code

        loans = get_active_loans(user['user_id'])
        return jsonify({"active_loans": loans, "total_active": len(loans)}), 200

    @app.route('/api/users/me/checkout-history')
    def checkout_history():
        """
        Retrieve The Checkout History (Returned Loans) For The Authenticated User.

        Lists All Loans That Have Been Returned, Including Fine Amounts.
        Requires A Valid JWT Token.

        Returns:
            JSON: List Of Returned Loans.
            Status Codes: 200 OK, 401 Unauthorized.
        """
        user, err, code = get_user_from_token()
        if err:
            return jsonify(err), code

        conn = psycopg2.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            database=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD
        )
        cur = conn.cursor()
        cur.execute("""
            SELECT l.loan_id, b.title, a.name AS author,
                   l.checkout_date, l.due_date, l.return_date, l.fine_amount
            FROM loans l
            JOIN copies c ON l.copy_id = c.copy_id
            JOIN books b ON c.book_id = b.book_id
            LEFT JOIN book_authors ba ON b.book_id = ba.book_id
            LEFT JOIN authors a ON ba.author_id = a.author_id
            WHERE l.user_id = %s AND l.return_date IS NOT NULL
            ORDER BY l.return_date DESC
        """, (user['user_id'],))
        rows = cur.fetchall()
        cur.close()
        conn.close()

        history = [{
            "loan_id": r[0],
            "title": r[1],
            "author": r[2] or "Unknown",
            "checkout_date": r[3].isoformat() if r[3] else None,
            "due_date": r[4].isoformat() if r[4] else None,
            "return_date": r[5].isoformat() if r[5] else None,
            "fine": float(r[6]) if r[6] else 0.0
        } for r in rows]

        return jsonify({"checkout_history": history}), 200

    # --------------------------------------------------------------
    # Fines And Payments Routes (Authenticated)
    # --------------------------------------------------------------

    @app.route('/api/users/me/charges')
    def get_charges():
        """
        Retrieve Outstanding Fines For The Authenticated User.

        Lists All Unpaid Fines With Loan Details. Requires A Valid JWT Token.

        Returns:
            JSON: List Of Charges And Total Amount.
            Status Codes: 200 OK, 401 Unauthorized.
        """
        user, err, code = get_user_from_token()
        if err:
            return jsonify(err), code

        conn = psycopg2.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            database=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD
        )
        cur = conn.cursor()
        cur.execute("""
            SELECT loan_id, title, fine_amount, due_date, return_date
            FROM loans l
            JOIN copies c ON l.copy_id = c.copy_id
            JOIN books b ON c.book_id = b.book_id
            WHERE l.user_id = %s AND l.fine_amount > 0 AND l.fine_paid = false
        """, (user['user_id'],))
        rows = cur.fetchall()
        cur.close()
        conn.close()

        charges = [{
            "loan_id": r[0],
            "title": r[1],
            "fine": float(r[2]),
            "due_date": r[3].isoformat() if r[3] else None,
            "return_date": r[4].isoformat() if r[4] else None
        } for r in rows]

        total = sum(c["fine"] for c in charges)
        return jsonify({"charges": charges, "total": total}), 200

    @app.route('/api/users/me/payfine', methods=['POST'])
    def pay_fine():
        """
        Pay A Specific Fine For The Authenticated User.

        Marks The Specified Loan's Fine As Paid. Requires A Valid JWT Token.

        Expected JSON Body:
            - loan_id (int): ID Of The Loan For Which The Fine Is Being Paid.

        Returns:
            JSON: Success Message Or Error.
            Status Codes: 200 OK, 400 Bad Request, 401 Unauthorized, 404 Not Found.
        """
        user, err, code = get_user_from_token()
        if err:
            return jsonify(err), code

        data = request.get_json()
        loan_id = data.get('loan_id')
        if not loan_id:
            return jsonify({"error": "loan_id required"}), 400

        conn = psycopg2.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            database=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD
        )
        cur = conn.cursor()
        cur.execute("""
            UPDATE loans
            SET fine_paid = true
            WHERE loan_id = %s AND user_id = %s
            RETURNING loan_id
        """, (loan_id, user['user_id']))
        updated = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if not updated:
            return jsonify({"error": "Loan not found or not yours"}), 404

        return jsonify({"message": "Fine paid"}), 200

    # --------------------------------------------------------------
    # Loan Renewal Route (Authenticated)
    # --------------------------------------------------------------

    @app.route('/api/loans/<int:loan_id>/renew', methods=['PUT'])
    def renew_loan_route(loan_id):
        """
        Renew An Active Loan For The Authenticated User.

        Extends The Due Date By 14 Days If The Loan Is Eligible (Not Returned,
        Belongs To The User, Within Renewal Limit, No Active Holds).
        Requires A Valid JWT Token.

        Returns:
            JSON: Success Message With New Due Date Or Error.
            Status Codes: 200 OK, 400 Bad Request, 401 Unauthorized.
        """
        user, err, code = get_user_from_token()
        if err:
            return jsonify(err), code

        try:
            new_due = renew_loan(loan_id, user['user_id'])
            return jsonify({"message": "Loan renewed", "new_due_date": new_due.isoformat()}), 200
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    # --------------------------------------------------------------
    # Book Search Route (Public)
    # --------------------------------------------------------------

    @app.route('/api/books')
    def books_search():
        """
        Search For Books By Title, ISBN, Or Author Name.

        This Endpoint Is Public And Does Not Require Authentication.
        Supports Pagination Via The 'limit' Query Parameter.

        Query Parameters:
            - q (str): Search Term (Required).
            - limit (int, optional): Maximum Results To Return (Default 20).

        Returns:
            JSON: List Of Books Matching The Search.
            Status Codes: 200 OK, 400 Bad Request.
        """
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({"error": "Missing search query parameter 'q'"}), 400

        limit = request.args.get('limit', 20, type=int)
        results = search_books(query, limit)

        return jsonify({"query": query, "count": len(results), "books": results}), 200

    # --------------------------------------------------------------
    # Checkout And Return Routes (Librarian Only)
    # --------------------------------------------------------------

    @app.route('/api/loans', methods=['POST'])
    def checkout():
        """
        Perform A Book Checkout (Librarian Only).

        Requires The User To Be Logged In As A Librarian. Creates A New Loan
        For The Specified User And Copy.

        Expected JSON Body:
            - user_id (int): ID Of The User Borrowing The Book.
            - copy_id (int): ID Of The Copy Being Checked Out.

        Returns:
            JSON: Success Message With Loan ID Or Error.
            Status Codes: 201 Created, 400 Bad Request, 401 Unauthorized, 403 Forbidden.
        """
        user, err, code = get_user_from_token()
        if err:
            return jsonify(err), code

        # Verify That The Authenticated User Is A Librarian.
        if user.get('role') != 'librarian':
            return jsonify({"error": "Only librarians can checkout"}), 403

        data = request.get_json()
        user_id = data.get('user_id')
        copy_id = data.get('copy_id')

        # Validate Required Fields.
        if not user_id or not copy_id:
            return jsonify({"error": "user_id and copy_id required"}), 400

        try:
            loan_id = create_loan(user_id, copy_id)
            return jsonify({"message": "Checkout successful", "loan_id": loan_id}), 201
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    @app.route('/api/loans/<int:loan_id>/return', methods=['PUT'])
    def return_book(loan_id):
        """
        Process A Book Return (Librarian Only).

        Marks The Loan As Returned, Calculates Any Overdue Fine, And
        Updates The Copy Status To 'available'. Requires Librarian Role.

        Returns:
            JSON: Success Message With Fine Amount Or Error.
            Status Codes: 200 OK, 400 Bad Request, 401 Unauthorized, 403 Forbidden.
        """
        user, err, code = get_user_from_token()
        if err:
            return jsonify(err), code

        if user.get('role') != 'librarian':
            return jsonify({"error": "Only librarians can return"}), 403

        try:
            fine = return_loan(loan_id)
            return jsonify({
                "message": "Return successful",
                "loan_id": loan_id,
                "fine_amount": fine
            }), 200
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    # --------------------------------------------------------------
    # Holds Management Routes
    # --------------------------------------------------------------

    @app.route('/api/holds', methods=['POST'])
    def place_hold_route():
        """
        Place A Hold On A Book (Authenticated Student/Librarian).

        Allows Any Authenticated User To Reserve A Book. Prevents Duplicate
        Active Holds On The Same Book By The Same User.

        Expected JSON Body:
            - book_id (int): ID Of The Book To Place On Hold.

        Returns:
            JSON: Success Message With Hold ID Or Error.
            Status Codes: 201 Created, 400 Bad Request, 401 Unauthorized.
        """
        user, err, code = get_user_from_token()
        if err:
            return jsonify(err), code

        data = request.get_json()
        book_id = data.get('book_id')
        if not book_id:
            return jsonify({"error": "book_id required"}), 400

        try:
            hold_id = place_hold(user['user_id'], book_id)
            return jsonify({"message": "Hold placed", "hold_id": hold_id}), 201
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    @app.route('/api/users/me/holds')
    def user_holds():
        """
        Retrieve All Holds For The Authenticated User.

        Returns All Holds (Active, Fulfilled, Cancelled) Belonging To The User.

        Returns:
            JSON: List Of Holds With Details.
            Status Codes: 200 OK, 401 Unauthorized.
        """
        user, err, code = get_user_from_token()
        if err:
            return jsonify(err), code

        holds = get_user_holds(user['user_id'])
        return jsonify({"holds": holds}), 200

    @app.route('/api/holds', methods=['GET'])
    def pending_holds():
        """
        Retrieve All Active Holds (Librarian Only).

        Lists All Pending Holds From All Users, Including User And Book Details.
        Requires Librarian Role.

        Returns:
            JSON: List Of Pending Holds.
            Status Codes: 200 OK, 401 Unauthorized, 403 Forbidden.
        """
        user, err, code = get_user_from_token()
        if err:
            return jsonify(err), code

        if user.get('role') != 'librarian':
            return jsonify({"error": "Only librarians can view all holds"}), 403

        holds = get_all_pending_holds()
        return jsonify({"pending_holds": holds}), 200

    @app.route('/api/holds/<int:hold_id>/fulfill', methods=['PUT'])
    def fulfill_hold_route(hold_id):
        """
        Fulfill A Hold (Librarian Only).

        Marks The Hold As 'fulfilled' (Ready For Pickup) And Sends A
        Notification Message To The User. Requires Librarian Role.

        Returns:
            JSON: Success Message Or Error.
            Status Codes: 200 OK, 400 Bad Request, 401 Unauthorized, 403 Forbidden.
        """
        user, err, code = get_user_from_token()
        if err:
            return jsonify(err), code

        if user.get('role') != 'librarian':
            return jsonify({"error": "Only librarians can fulfill holds"}), 403

        try:
            fulfill_hold(hold_id)

            # Retrieve User ID And Book ID Associated With This Hold.
            conn = psycopg2.connect(
                host=Config.DB_HOST,
                port=Config.DB_PORT,
                database=Config.DB_NAME,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD
            )
            cur = conn.cursor()
            cur.execute("SELECT user_id, book_id FROM holds WHERE hold_id = %s", (hold_id,))
            row = cur.fetchone()
            cur.close()
            conn.close()

            if row:
                user_id, book_id = row

                # Fetch The Book Title To Include In The Notification.
                conn = psycopg2.connect(
                    host=Config.DB_HOST,
                    port=Config.DB_PORT,
                    database=Config.DB_NAME,
                    user=Config.DB_USER,
                    password=Config.DB_PASSWORD
                )
                cur = conn.cursor()
                cur.execute("SELECT title FROM books WHERE book_id = %s", (book_id,))
                title = cur.fetchone()[0]
                cur.close()
                conn.close()

                # Send A Notification Message To The User.
                send_message(
                    user_id,
                    "System",
                    "Hold Ready",
                    f"Your hold for '{title}' is now available for pickup."
                )

            return jsonify({"message": "Hold fulfilled"}), 200

        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    @app.route('/api/holds/<int:hold_id>/cancel', methods=['PUT'])
    def cancel_hold_route(hold_id):
        """
        Cancel A Hold (Student Or Librarian).

        Allows The Owner Of The Hold Or A Librarian To Cancel It.
        Changes The Status To 'cancelled'.

        Returns:
            JSON: Success Message Or Error.
            Status Codes: 200 OK, 400 Bad Request, 401 Unauthorized, 403 Forbidden.
        """
        user, err, code = get_user_from_token()
        if err:
            return jsonify(err), code

        # If Not A Librarian, Verify Ownership Of The Hold.
        if user.get('role') != 'librarian':
            conn = psycopg2.connect(
                host=Config.DB_HOST,
                port=Config.DB_PORT,
                database=Config.DB_NAME,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD
            )
            cur = conn.cursor()
            cur.execute("SELECT user_id FROM holds WHERE hold_id = %s", (hold_id,))
            row = cur.fetchone()
            cur.close()
            conn.close()

            if not row or row[0] != user['user_id']:
                return jsonify({"error": "You can only cancel your own holds"}), 403

        try:
            cancel_hold(hold_id)
            return jsonify({"message": "Hold cancelled"}), 200
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    # --------------------------------------------------------------
    # Search History Routes (Authenticated)
    # --------------------------------------------------------------

    @app.route('/api/users/me/search-history', methods=['GET'])
    def get_search_history_route():
        """
        Retrieve The Authenticated User's Search History.

        Returns A List Of Recent Search Queries With Timestamps.

        Returns:
            JSON: List Of Search History Entries.
            Status Codes: 200 OK, 401 Unauthorized.
        """
        user, err, code = get_user_from_token()
        if err:
            return jsonify(err), code

        history = get_search_history(user['user_id'])
        return jsonify({"search_history": history}), 200

    @app.route('/api/users/me/search-history', methods=['POST'])
    def add_search_route():
        """
        Record A New Search Query For The Authenticated User.

        Expected JSON Body:
            - query (str): The Search Term Entered By The User.

        Returns:
            JSON: Success Message.
            Status Codes: 201 Created, 400 Bad Request, 401 Unauthorized.
        """
        user, err, code = get_user_from_token()
        if err:
            return jsonify(err), code

        data = request.get_json()
        query = data.get('query')
        if not query:
            return jsonify({"error": "query required"}), 400

        add_search(user['user_id'], query)
        return jsonify({"message": "Search recorded"}), 201

    # --------------------------------------------------------------
    # Reading Lists Routes (Authenticated)
    # --------------------------------------------------------------

    @app.route('/api/users/me/lists', methods=['GET'])
    def get_lists():
        """
        Retrieve All Reading Lists For The Authenticated User.

        Returns A List Of The User's Custom Reading Lists.

        Returns:
            JSON: List Of Reading Lists.
            Status Codes: 200 OK, 401 Unauthorized.
        """
        user, err, code = get_user_from_token()
        if err:
            return jsonify(err), code

        lists = get_user_lists(user['user_id'])
        return jsonify({"lists": lists}), 200

    @app.route('/api/users/me/lists', methods=['POST'])
    def create_list_route():
        """
        Create A New Reading List For The Authenticated User.

        Expected JSON Body:
            - list_name (str): Name Of The New List.

        Returns:
            JSON: Success Message With List ID.
            Status Codes: 201 Created, 400 Bad Request, 401 Unauthorized.
        """
        user, err, code = get_user_from_token()
        if err:
            return jsonify(err), code

        data = request.get_json()
        list_name = data.get('list_name')
        if not list_name:
            return jsonify({"error": "list_name required"}), 400

        list_id = create_list(user['user_id'], list_name)
        return jsonify({"message": "List created", "list_id": list_id}), 201

    @app.route('/api/lists/<int:list_id>', methods=['DELETE'])
    def delete_list_route(list_id):
        """
        Delete A Reading List (Owner Only).

        Deletes The Specified List Only If It Belongs To The Authenticated User.

        Returns:
            JSON: Success Message Or Error.
            Status Codes: 200 OK, 404 Not Found, 401 Unauthorized.
        """
        user, err, code = get_user_from_token()
        if err:
            return jsonify(err), code

        deleted = delete_list(list_id, user['user_id'])
        if not deleted:
            return jsonify({"error": "List not found or not yours"}), 404

        return jsonify({"message": "List deleted"}), 200

    @app.route('/api/lists/<int:list_id>', methods=['PUT'])
    def rename_list_route(list_id):
        """
        Rename A Reading List (Owner Only).

        Updates The Name Of The Specified List If It Belongs To The User.

        Expected JSON Body:
            - list_name (str): New Name For The List.

        Returns:
            JSON: Success Message Or Error.
            Status Codes: 200 OK, 400 Bad Request, 404 Not Found, 401 Unauthorized.
        """
        user, err, code = get_user_from_token()
        if err:
            return jsonify(err), code

        data = request.get_json()
        new_name = data.get('list_name')
        if not new_name:
            return jsonify({"error": "list_name required"}), 400

        updated = rename_list(list_id, user['user_id'], new_name)
        if not updated:
            return jsonify({"error": "List not found or not yours"}), 404

        return jsonify({"message": "List renamed"}), 200

    @app.route('/api/lists/<int:list_id>/items', methods=['POST'])
    def add_list_item_route(list_id):
        """
        Add A Book To A Reading List (Owner Only).

        Adds The Specified Book To The Given List If The List Belongs To The User.

        Expected JSON Body:
            - book_id (int): ID Of The Book To Add.

        Returns:
            JSON: Success Message Or Error.
            Status Codes: 201 Created, 400 Bad Request, 401 Unauthorized.
        """
        user, err, code = get_user_from_token()
        if err:
            return jsonify(err), code

        data = request.get_json()
        book_id = data.get('book_id')
        if not book_id:
            return jsonify({"error": "book_id required"}), 400

        success = add_list_item(list_id, user['user_id'], book_id)
        if not success:
            return jsonify({"error": "List not found, not yours, or book already in list"}), 400

        return jsonify({"message": "Book added to list"}), 201

    @app.route('/api/lists/<int:list_id>/items/<int:book_id>', methods=['DELETE'])
    def remove_list_item_route(list_id, book_id):
        """
        Remove A Book From A Reading List (Owner Only).

        Removes The Specified Book From The Given List If The List Belongs To The User.

        Returns:
            JSON: Success Message Or Error.
            Status Codes: 200 OK, 404 Not Found, 401 Unauthorized.
        """
        user, err, code = get_user_from_token()
        if err:
            return jsonify(err), code

        removed = remove_list_item(list_id, user['user_id'], book_id)
        if not removed:
            return jsonify({"error": "Item not found"}), 404

        return jsonify({"message": "Book removed from list"}), 200

    @app.route('/api/lists/<int:list_id>/items', methods=['GET'])
    def get_list_items_route(list_id):
        """
        Retrieve All Books In A Reading List (Owner Only).

        Returns The List Of Books With Details For The Specified List If It Belongs To The User.

        Returns:
            JSON: List Of Books In The List.
            Status Codes: 200 OK, 401 Unauthorized.
        """
        user, err, code = get_user_from_token()
        if err:
            return jsonify(err), code

        items = get_list_items(list_id, user['user_id'])
        return jsonify({"items": items}), 200

    # --------------------------------------------------------------
    # Tags Routes (Authenticated)
    # --------------------------------------------------------------

    @app.route('/api/users/me/tags', methods=['GET'])
    def get_tags():
        """
        Retrieve All Tags Created By The Authenticated User.

        Returns A List Of Tags With Associated Book Information.

        Returns:
            JSON: List Of Tags.
            Status Codes: 200 OK, 401 Unauthorized.
        """
        user, err, code = get_user_from_token()
        if err:
            return jsonify(err), code

        tags = get_user_tags(user['user_id'])
        return jsonify({"tags": tags}), 200

    @app.route('/api/tags', methods=['POST'])
    def add_tag_route():
        """
        Add A Tag To A Book (Authenticated User).

        Creates A New Tag For The Specified Book. Prevents Duplicate Tags
        For The Same User And Book Combination.

        Expected JSON Body:
            - book_id (int): ID Of The Book To Tag.
            - tag (str): The Tag Text.

        Returns:
            JSON: Success Message With Tag ID Or Error.
            Status Codes: 201 Created, 400 Bad Request, 409 Conflict, 401 Unauthorized.
        """
        user, err, code = get_user_from_token()
        if err:
            return jsonify(err), code

        data = request.get_json()
        book_id = data.get('book_id')
        tag_text = data.get('tag')

        if not book_id or not tag_text:
            return jsonify({"error": "book_id and tag required"}), 400

        tag_id = add_tag(user['user_id'], book_id, tag_text)
        if tag_id is None:
            return jsonify({"error": "Tag already exists for this book"}), 409

        return jsonify({"message": "Tag added", "tag_id": tag_id}), 201

    @app.route('/api/tags/<int:tag_id>', methods=['DELETE'])
    def delete_tag_route(tag_id):
        """
        Delete A Tag (Owner Only).

        Removes The Specified Tag If It Belongs To The Authenticated User.

        Returns:
            JSON: Success Message Or Error.
            Status Codes: 200 OK, 404 Not Found, 401 Unauthorized.
        """
        user, err, code = get_user_from_token()
        if err:
            return jsonify(err), code

        deleted = delete_tag(tag_id, user['user_id'])
        if not deleted:
            return jsonify({"error": "Tag not found or not yours"}), 404

        return jsonify({"message": "Tag deleted"}), 200

    # --------------------------------------------------------------
    # Purchase Suggestions Routes
    # --------------------------------------------------------------

    @app.route('/api/suggestions', methods=['POST'])
    def create_suggestion_route():
        """
        Submit A Purchase Suggestion (Authenticated User).

        Allows Any Authenticated User To Suggest A Book For The Library To Purchase.
        The Status Is Initially Set To 'pending'.

        Expected JSON Body:
            - title (str): Title Of The Suggested Book.
            - author (str, optional): Author Of The Book.
            - notes (str, optional): Additional Comments.

        Returns:
            JSON: Success Message With Suggestion ID.
            Status Codes: 201 Created, 400 Bad Request, 401 Unauthorized.
        """
        user, err, code = get_user_from_token()
        if err:
            return jsonify(err), code

        data = request.get_json()
        title = data.get('title')
        author = data.get('author')
        notes = data.get('notes')

        if not title:
            return jsonify({"error": "title required"}), 400

        sug_id = create_suggestion(user['user_id'], title, author, notes)
        return jsonify({"message": "Suggestion submitted", "suggestion_id": sug_id}), 201

    @app.route('/api/users/me/suggestions', methods=['GET'])
    def get_my_suggestions():
        """
        Retrieve Suggestions Submitted By The Authenticated User.

        Returns All Suggestions Created By The User With Their Status.

        Returns:
            JSON: List Of User's Suggestions.
            Status Codes: 200 OK, 401 Unauthorized.
        """
        user, err, code = get_user_from_token()
        if err:
            return jsonify(err), code

        sugs = get_user_suggestions(user['user_id'])
        return jsonify({"suggestions": sugs}), 200

    @app.route('/api/suggestions', methods=['GET'])
    def get_all_suggestions_route():
        """
        Retrieve All Purchase Suggestions (Librarian Only).

        Lists All Suggestions From All Users Along With Submitter Names.
        Requires Librarian Role.

        Returns:
            JSON: List Of All Suggestions.
            Status Codes: 200 OK, 401 Unauthorized, 403 Forbidden.
        """
        user, err, code = get_user_from_token()
        if err:
            return jsonify(err), code

        if user.get('role') != 'librarian':
            return jsonify({"error": "Only librarians can view all suggestions"}), 403

        sugs = get_all_suggestions()
        return jsonify({"suggestions": sugs}), 200

    @app.route('/api/suggestions/<int:suggestion_id>', methods=['PUT'])
    def update_suggestion_route(suggestion_id):
        """
        Update The Status Of A Purchase Suggestion (Librarian Only).

        Allows A Librarian To Change The Status To 'pending', 'reviewed',
        'approved', Or 'rejected'.

        Expected JSON Body:
            - status (str): New Status.

        Returns:
            JSON: Success Message Or Error.
            Status Codes: 200 OK, 400 Bad Request, 404 Not Found, 401 Unauthorized,
                          403 Forbidden.
        """
        user, err, code = get_user_from_token()
        if err:
            return jsonify(err), code

        if user.get('role') != 'librarian':
            return jsonify({"error": "Only librarians can update suggestions"}), 403

        data = request.get_json()
        status = data.get('status')
        if status not in ('pending', 'reviewed', 'approved', 'rejected'):
            return jsonify({"error": "Invalid status"}), 400

        updated = update_suggestion_status(suggestion_id, status, user['user_id'])
        if not updated:
            return jsonify({"error": "Suggestion not found"}), 404

        return jsonify({"message": "Suggestion updated"}), 200

    # --------------------------------------------------------------
    # Messages Routes (Authenticated)
    # --------------------------------------------------------------

    @app.route('/api/users/me/messages', methods=['GET'])
    def get_messages():
        """
        Retrieve Messages For The Authenticated User.

        Returns All Messages (Or Only Unread Ones If 'unread' Query Parameter Is Set).

        Query Parameters:
            - unread (bool, optional): If 'true', Returns Only Unread Messages.

        Returns:
            JSON: List Of Messages.
            Status Codes: 200 OK, 401 Unauthorized.
        """
        user, err, code = get_user_from_token()
        if err:
            return jsonify(err), code

        unread_only = request.args.get('unread', 'false').lower() == 'true'
        msgs = get_user_messages(user['user_id'], unread_only)
        return jsonify({"messages": msgs}), 200

    @app.route('/api/users/me/messages/<int:message_id>/read', methods=['PUT'])
    def mark_read(message_id):
        """
        Mark A Specific Message As Read (Owner Only).

        Updates The is_read Flag To True For The Specified Message If It Belongs To The User.

        Returns:
            JSON: Success Message Or Error.
            Status Codes: 200 OK, 404 Not Found, 401 Unauthorized.
        """
        user, err, code = get_user_from_token()
        if err:
            return jsonify(err), code

        marked = mark_message_read(message_id, user['user_id'])
        if not marked:
            return jsonify({"error": "Message not found or not yours"}), 404

        return jsonify({"message": "Marked as read"}), 200

    # --------------------------------------------------------------
    # Book Management (Librarian Only)
    # --------------------------------------------------------------

    @app.route('/api/books', methods=['POST'])
    def add_book():
        """
        Add A New Book To The Catalog (Librarian Only).

        Inserts A New Book Record And Creates An Initial Available Copy.
        Requires Librarian Role.

        Expected JSON Body:
            - title (str): Title Of The Book (Required).
            - isbn (str, optional): International Standard Book Number.
            - call_number (str, optional): Library Call Number.
            - publisher (str, optional): Publisher Name.
            - published_date (date, optional): Publication Date (YYYY-MM-DD).
            - location (str, optional): Shelf Location.
            - total_copies (int, optional): Total Copies (Default 1).
            - summary (str, optional): Book Summary.

        Returns:
            JSON: Success Message With Book ID Or Error.
            Status Codes: 201 Created, 400 Bad Request, 401 Unauthorized, 403 Forbidden.
        """
        user, err, code = get_user_from_token()
        if err:
            return jsonify(err), code

        if user.get('role') != 'librarian':
            return jsonify({"error": "Only librarians can add books"}), 403

        data = request.get_json()
        title = data.get('title')
        isbn = data.get('isbn')
        call_number = data.get('call_number')
        publisher = data.get('publisher')
        published_date = data.get('published_date')
        location = data.get('location')
        total_copies = data.get('total_copies', 1)
        summary = data.get('summary')

        # Validate Required Field.
        if not title:
            return jsonify({"error": "Title is required"}), 400

        conn = psycopg2.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            database=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD
        )
        cur = conn.cursor()

        try:
            # Insert The New Book Record.
            cur.execute("""
                INSERT INTO books (title, isbn, call_number, publisher,
                                   published_date, location, total_copies, summary)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING book_id
            """, (title, isbn, call_number, publisher, published_date,
                  location, total_copies, summary))

            book_id = cur.fetchone()[0]
            conn.commit()

            # Create An Initial Copy For The Book.
            cur.execute("""
                INSERT INTO copies (book_id, barcode, status, shelf_location)
                VALUES (%s, %s, 'available', %s)
            """, (book_id, f"B{book_id:04d}", location))
            conn.commit()

            return jsonify({"message": "Book added", "book_id": book_id}), 201

        except Exception as e:
            conn.rollback()
            return jsonify({"error": str(e)}), 400

        finally:
            cur.close()
            conn.close()

    # Return The Configured Flask Application.
    return app