-- Library Management System - Complete Database Schema
--
-- This File Defines The Entire Database Structure For The
-- Library Management System. It Includes All Tables, Constraints,
-- And Indexes Required For The Application To Function.
--
-- The Schema Is Normalized To Third Normal Form (3NF) And
-- Includes Proper Foreign Key Relationships With CASCADE Deletes
-- Where Appropriate To Maintain Data Integrity.
--
-- To Execute This File:
--   1. Connect To PostgreSQL: sudo -u postgres psql
--   2. Create The Database (If Not Exists): CREATE DATABASE lms;
--   3. Switch To The Database: \c lms;
--   4. Run The Schema: \i sql/schema.sql


-- 1. Users Table
-- Stores All User Accounts In The System.
-- Each User Can Be Either A Student (Patron) Or A Librarian (Admin).
-- Passwords Are Stored As bcrypt Hashes For Security.
-- The Email Field Must Be Unique To Prevent Duplicate Accounts.

CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    -- Unique Identifier For Each User. Auto-Generated.

    name VARCHAR(100) NOT NULL,
    -- Full Name Of The User. This Field Cannot Be Empty.

    email VARCHAR(255) UNIQUE NOT NULL,
    -- Email Address Used For Login And Communication.
    -- Must Be Unique Across All Users.

    password_hash TEXT NOT NULL,
    -- Bcrypt Hashed Password. The Plain-Text Password Is Never Stored.
    -- The TEXT Type Is Used Because The Hash Length Is Variable.

    role VARCHAR(20) NOT NULL CHECK (role IN ('student', 'librarian')),
    -- User Role Determines Permissions:
    --   'student'   - Can Search, Borrow, Place Holds, Manage Profile.
    --   'librarian' - Has Administrative Privileges For Checkout,
    --                 Return, Inventory Management, And User Management.

    photo_path TEXT,
    -- File Path Or URL To The User's Profile Photo.
    -- Can Be NULL If No Photo Is Uploaded.

    contact_info TEXT,
    -- Additional Contact Details Such As Address, Phone Number, Etc.
    -- Stored As Free-Form Text For Flexibility.

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    -- Timestamp When The User Account Was Created.
    -- Automatically Set To The Current Date And Time.
);


-- 2. Authors Table
-- Stores Author Information.
-- Authors Are Stored Separately From Books To Support
-- Many-To-Many Relationships (A Book Can Have Multiple Authors).

CREATE TABLE IF NOT EXISTS authors (
    author_id SERIAL PRIMARY KEY,
    -- Unique Identifier For Each Author. Auto-Generated.

    name VARCHAR(255) NOT NULL
    -- Full Name Of The Author. This Field Cannot Be Empty.
);


-- 3. Books Table
-- Stores Bibliographic Information For Each Book Title.
-- This Table Represents The Master Record For A Book,
-- Independent Of Physical Copies.

CREATE TABLE IF NOT EXISTS books (
    book_id SERIAL PRIMARY KEY,
    -- Unique Identifier For Each Book Title. Auto-Generated.

    title VARCHAR(500) NOT NULL,
    -- Full Title Of The Book. This Field Cannot Be Empty.
    -- The Length Is Set To 500 Characters To Accommodate Long Titles.

    isbn VARCHAR(20) UNIQUE,
    -- International Standard Book Number (ISBN).
    -- Must Be Unique If Provided. Can Be NULL For Older Books.

    call_number VARCHAR(50),
    -- Library Call Number Used For Shelving (e.g., Dewey Decimal).
    -- Helps Staff Locate The Physical Copy.

    publisher VARCHAR(255),
    -- Name Of The Publisher Who Published The Book.

    published_date DATE,
    -- Publication Date Of The Book.

    location VARCHAR(100),
    -- General Location Of The Book Within The Library.
    -- For Example: "Main Library - Fiction" Or "Reference Section".

    total_copies INTEGER DEFAULT 1,
    -- Total Number Of Physical Copies Available For This Title.
    -- This Is A Denormalized Field For Quick Display.
    -- The Actual Copy Count Is Managed In The "copies" Table.

    summary TEXT,
    -- Brief Description Or Summary Of The Book's Content.

    cover_image_path TEXT
    -- File Path Or URL To The Book's Cover Image.
    -- Can Be NULL If No Cover Is Available.
);


-- 4. Book-Authors Join Table
-- Implements A Many-To-Many Relationship Between Books And Authors.
-- A Book Can Have Multiple Authors, And An Author Can Write
-- Multiple Books.

CREATE TABLE IF NOT EXISTS book_authors (
    book_id INTEGER REFERENCES books(book_id) ON DELETE CASCADE,
    -- Foreign Key To The books Table.
    -- ON DELETE CASCADE: If A Book Is Deleted, All Its Author
    -- Associations Are Automatically Removed.

    author_id INTEGER REFERENCES authors(author_id) ON DELETE CASCADE,
    -- Foreign Key To The authors Table.
    -- ON DELETE CASCADE: If An Author Is Deleted, All Their Book
    -- Associations Are Automatically Removed.

    PRIMARY KEY (book_id, author_id)
    -- Composite Primary Key Ensures That Each Combination Of
    -- Book And Author Is Unique.
);


-- 5. Copies Table
-- Represents Individual Physical Copies Of A Book.
-- Each Copy Has A Unique Barcode And Can Have Different
-- Statuses (Available, Checked Out, Lost, Damaged).

CREATE TABLE IF NOT EXISTS copies (
    copy_id SERIAL PRIMARY KEY,
    -- Unique Identifier For Each Physical Copy. Auto-Generated.

    book_id INTEGER NOT NULL REFERENCES books(book_id) ON DELETE CASCADE,
    -- Foreign Key To The books Table.
    -- Links This Copy To Its Master Book Record.
    -- ON DELETE CASCADE: If The Book Is Deleted, All Its Copies
    -- Are Automatically Removed.

    barcode VARCHAR(50) UNIQUE NOT NULL,
    -- Unique Barcode Or Identifier For This Physical Copy.
    -- Used For Checkout, Return, And Inventory Tracking.

    status VARCHAR(20) DEFAULT 'available'
        CHECK (status IN ('available', 'checked out', 'lost', 'damaged')),
    -- Current Status Of The Copy:
    --   'available'   - Ready For Checkout.
    --   'checked out' - Currently Borrowed By A User.
    --   'lost'        - Lost Or Missing.
    --   'damaged'     - Damaged And Cannot Be Borrowed.

    shelf_location VARCHAR(50)
    -- Specific Shelf Location Within The Library.
    -- Helps Staff Find The Copy Quickly.
);


-- 6. Loans Table
-- Tracks All Checkouts And Returns.
-- Each Record Represents A Single Borrowing Event.
-- Returned Loans Are Retained For Historical Reporting.

CREATE TABLE IF NOT EXISTS loans (
    loan_id SERIAL PRIMARY KEY,
    -- Unique Identifier For Each Loan Transaction. Auto-Generated.

    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    -- Foreign Key To The users Table.
    -- Identifies Which User Borrowed The Copy.
    -- ON DELETE CASCADE: If The User Is Deleted, Their Loan History
    -- Is Automatically Removed.

    copy_id INTEGER NOT NULL REFERENCES copies(copy_id) ON DELETE CASCADE,
    -- Foreign Key To The copies Table.
    -- Identifies Which Physical Copy Was Borrowed.
    -- ON DELETE CASCADE: If A Copy Is Deleted, Its Loan Records
    -- Are Automatically Removed.

    checkout_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Date And Time When The Loan Was Created.
    -- Automatically Set To The Current Timestamp.

    due_date DATE NOT NULL,
    -- Date By Which The Copy Should Be Returned.
    -- Calculated As checkout_date + Loan Period (e.g., 14 Days).

    return_date DATE,
    -- Date When The Copy Was Actually Returned.
    -- NULL If The Loan Is Still Active.

    renewal_count INTEGER DEFAULT 0,
    -- Number Of Times The Loan Has Been Renewed.
    -- Used To Enforce The Maximum Renewal Limit (e.g., 3).

    fine_amount DECIMAL(10,2) DEFAULT 0.00,
    -- Any Fine Accrued For This Loan.
    -- Calculated When The Loan Is Returned If Overdue.

    fine_paid BOOLEAN DEFAULT FALSE
    -- Indicates Whether The Fine Has Been Paid.
    -- FALSE Means The Fine Is Outstanding.
);


-- 7. Holds Table
-- Manages Book Reservations Made By Users.
-- A Hold Allows A User To Reserve A Book When It Becomes Available.
-- Statuses Track The Lifecycle Of A Hold Request.

CREATE TABLE IF NOT EXISTS holds (
    hold_id SERIAL PRIMARY KEY,
    -- Unique Identifier For Each Hold Request. Auto-Generated.

    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    -- Foreign Key To The users Table.
    -- Identifies Which User Placed The Hold.

    book_id INTEGER NOT NULL REFERENCES books(book_id) ON DELETE CASCADE,
    -- Foreign Key To The books Table.
    -- Identifies The Book The User Wants To Reserve.

    request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Date And Time When The Hold Was Placed.
    -- Automatically Set To The Current Timestamp.

    status VARCHAR(20) DEFAULT 'active'
        CHECK (status IN ('active', 'fulfilled', 'cancelled')),
    -- Current Status Of The Hold:
    --   'active'    - Hold Is Pending.
    --   'fulfilled' - Hold Has Been Fulfilled (Book Is Ready).
    --   'cancelled' - Hold Was Cancelled By The User Or Librarian.

    fulfilled_loan_id INTEGER REFERENCES loans(loan_id) ON DELETE SET NULL
    -- Optional Reference To The Loan That Fulfilled This Hold.
    -- Set To NULL If The Hold Has Not Been Fulfilled Or If The
    -- Referenced Loan Is Deleted.
);


-- 8. Search History Table
-- Logs Search Queries Made By Users.
-- Used To Populate The "Search History" Feature On The User
-- Account Page.

CREATE TABLE IF NOT EXISTS searches (
    search_id SERIAL PRIMARY KEY,
    -- Unique Identifier For Each Search Log Entry. Auto-Generated.

    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    -- Foreign Key To The users Table.
    -- Identifies Which User Performed The Search.
    -- ON DELETE CASCADE: If The User Is Deleted, Their Search
    -- History Is Automatically Removed.

    query_text TEXT NOT NULL,
    -- The Full Search Query Entered By The User.

    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    -- Date And Time When The Search Was Performed.
    -- Automatically Set To The Current Timestamp.
);


-- 9. Reading Lists
-- Allows Users To Create Custom Collections Of Books.
-- A User Can Have Multiple Lists, And Each List Can Contain
-- Multiple Books.

-- 9a. Lists Table
CREATE TABLE IF NOT EXISTS lists (
    list_id SERIAL PRIMARY KEY,
    -- Unique Identifier For Each Reading List. Auto-Generated.

    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    -- Foreign Key To The users Table.
    -- Identifies The Owner Of The List.
    -- ON DELETE CASCADE: If The User Is Deleted, Their Lists Are
    -- Automatically Removed.

    list_name VARCHAR(255) NOT NULL,
    -- Name Of The List (e.g., "Favorites", "To Read", "Research").
    -- This Field Cannot Be Empty.

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    -- Date And Time When The List Was Created.
    -- Automatically Set To The Current Timestamp.
);

-- 9b. List Items Table
CREATE TABLE IF NOT EXISTS list_items (
    list_item_id SERIAL PRIMARY KEY,
    -- Unique Identifier For Each List-Book Association. Auto-Generated.

    list_id INTEGER NOT NULL REFERENCES lists(list_id) ON DELETE CASCADE,
    -- Foreign Key To The lists Table.
    -- Links This Item To A Specific List.
    -- ON DELETE CASCADE: If The List Is Deleted, All Its Items
    -- Are Automatically Removed.

    book_id INTEGER NOT NULL REFERENCES books(book_id) ON DELETE CASCADE,
    -- Foreign Key To The books Table.
    -- Identifies The Book In This List.
    -- ON DELETE CASCADE: If The Book Is Deleted, Its List Entries
    -- Are Automatically Removed.

    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Date And Time When The Book Was Added To The List.
    -- Automatically Set To The Current Timestamp.

    UNIQUE (list_id, book_id)
    -- Ensures That A Book Cannot Be Added To The Same List More
    -- Than Once.
);


-- 10. Tags Table
-- Allows Users To Tag Books With Custom Labels.
-- Each User Can Have Multiple Tags On Different Books.
-- The Combination Of User, Book, And Tag Is Unique.

CREATE TABLE IF NOT EXISTS tags (
    tag_id SERIAL PRIMARY KEY,
    -- Unique Identifier For Each Tag. Auto-Generated.

    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    -- Foreign Key To The users Table.
    -- Identifies The User Who Created The Tag.
    -- ON DELETE CASCADE: If The User Is Deleted, Their Tags Are
    -- Automatically Removed.

    book_id INTEGER NOT NULL REFERENCES books(book_id) ON DELETE CASCADE,
    -- Foreign Key To The books Table.
    -- Identifies The Book Being Tagged.
    -- ON DELETE CASCADE: If The Book Is Deleted, Its Tags Are
    -- Automatically Removed.

    tag_text VARCHAR(100) NOT NULL,
    -- The Tag Text (e.g., "fiction", "classic", "to-read").
    -- This Field Cannot Be Empty.

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Date And Time When The Tag Was Created.
    -- Automatically Set To The Current Timestamp.

    UNIQUE (user_id, book_id, tag_text)
    -- Ensures That A User Cannot Add The Same Tag To The Same
    -- Book More Than Once.
);


-- 11. Purchase Suggestions Table
-- Allows Users To Suggest Books For The Library To Purchase.
-- Librarians Can Review Suggestions And Update Their Status.

CREATE TABLE IF NOT EXISTS suggestions (
    suggestion_id SERIAL PRIMARY KEY,
    -- Unique Identifier For Each Suggestion. Auto-Generated.

    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    -- Foreign Key To The users Table.
    -- Identifies The User Who Submitted The Suggestion.
    -- ON DELETE CASCADE: If The User Is Deleted, Their Suggestions
    -- Are Automatically Removed.

    title VARCHAR(500) NOT NULL,
    -- Title Of The Suggested Book. This Field Cannot Be Empty.

    author VARCHAR(255),
    -- Author Of The Suggested Book (Optional).

    notes TEXT,
    -- Additional Comments Or Reasons For The Suggestion (Optional).

    status VARCHAR(20) DEFAULT 'pending'
        CHECK (status IN ('pending', 'reviewed', 'approved', 'rejected')),
    -- Current Status Of The Suggestion:
    --   'pending'   - Awaiting Review By A Librarian.
    --   'reviewed'  - Has Been Reviewed But Not Decided.
    --   'approved'  - Approved For Purchase.
    --   'rejected'  - Not Approved.

    submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Date And Time When The Suggestion Was Submitted.
    -- Automatically Set To The Current Timestamp.

    reviewed_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL
    -- Foreign Key To The users Table.
    -- Identifies The Librarian Who Reviewed The Suggestion.
    -- Set To NULL If The Suggestion Has Not Been Reviewed Or If
    -- The Reviewer Is Deleted.
);


-- 12. Messages Table
-- Stores System Notifications And Messages Sent To Users.
-- Used For Alerts Such As "Hold Ready", "Overdue Reminder",
-- And Other Communications.

CREATE TABLE IF NOT EXISTS messages (
    message_id SERIAL PRIMARY KEY,
    -- Unique Identifier For Each Message. Auto-Generated.

    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    -- Foreign Key To The users Table.
    -- Identifies The Recipient Of The Message.
    -- ON DELETE CASCADE: If The User Is Deleted, Their Messages
    -- Are Automatically Removed.

    sender VARCHAR(100),
    -- Sender Of The Message (e.g., 'System' Or A Librarian's Name).
    -- Can Be NULL If The Sender Is Unknown.

    subject VARCHAR(255) NOT NULL,
    -- Subject Line Of The Message. This Field Cannot Be Empty.

    body TEXT NOT NULL,
    -- Full Content Of The Message. This Field Cannot Be Empty.

    sent_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Date And Time When The Message Was Sent.
    -- Automatically Set To The Current Timestamp.

    is_read BOOLEAN DEFAULT FALSE
    -- Indicates Whether The User Has Read The Message.
    -- FALSE Means The Message Is Unread.
);


-- Indexes For Performance
-- Indexes Are Created On Columns That Are Frequently Used In
-- WHERE Clauses, JOIN Conditions, Or ORDER BY Statements.
-- They Significantly Improve Query Performance At The Cost Of
-- Slightly Slower Write Operations.
-- All Indexes Are Created With IF NOT EXISTS To Prevent Errors
-- If They Already Exist.

-- Users: Email Is Used For Login Lookups.
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Books: Title, ISBN, And Call Number Are Used In Search Queries.
CREATE INDEX IF NOT EXISTS idx_books_title ON books(title);
CREATE INDEX IF NOT EXISTS idx_books_isbn ON books(isbn);
CREATE INDEX IF NOT EXISTS idx_books_call_number ON books(call_number);

-- Loans: User ID And Copy ID Are Used In JOINs And Filtering.
CREATE INDEX IF NOT EXISTS idx_loans_user_id ON loans(user_id);
CREATE INDEX IF NOT EXISTS idx_loans_copy_id ON loans(copy_id);
CREATE INDEX IF NOT EXISTS idx_loans_due_date ON loans(due_date) WHERE return_date IS NULL;
-- Partial Index: Only Indexes Active Loans (return_date IS NULL) For Faster Queries.

-- Holds: User ID, Book ID, And Status Are Used For Filtering.
CREATE INDEX IF NOT EXISTS idx_holds_user_id ON holds(user_id);
CREATE INDEX IF NOT EXISTS idx_holds_book_id ON holds(book_id);
CREATE INDEX IF NOT EXISTS idx_holds_status ON holds(status);

-- Searches: User ID And Query Text Are Used For History Retrieval.
CREATE INDEX IF NOT EXISTS idx_searches_user_id ON searches(user_id);
CREATE INDEX IF NOT EXISTS idx_searches_query ON searches(query_text);

-- List Items: List ID Is Used To Fetch All Books In A List.
CREATE INDEX IF NOT EXISTS idx_list_items_list_id ON list_items(list_id);

-- Tags: User ID Is Used To Retrieve All Tags Created By A User.
CREATE INDEX IF NOT EXISTS idx_tags_user_id ON tags(user_id);

-- Messages: User ID Is Used To Fetch All Messages For A User.
CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id);


-- Instructions For Executing This Schema
-- 1. Connect To PostgreSQL As The Postgres User:
--    sudo -u postgres psql
-- 2. Create The Database (If Not Already Created):
--    CREATE DATABASE lms;
-- 3. Connect To The Newly Created Database:
--    \c lms;
-- 4. Execute The Schema File:
--    \i sql/schema.sql
-- 5. Verify That All Tables Were Created Successfully:
--    \dt
-- 6. Exit PostgreSQL:
--    \q