# 📚 Library Management System

A **production‑ready** web application for managing library operations, built with **Flask** (Python) and **PostgreSQL**. It provides a seamless experience for both **students** (patrons) and **librarians** (admins).

- **Live Demo:** (not deployed yet)
- **GitHub:** [your-repo-url]

---

## ✨ Features

### 👨‍🎓 For Students
| Feature | Description |
|---------|-------------|
| **Secure Registration & Login** | Sign up with email/password; passwords are **hashed** using bcrypt. |
| **Profile Management** | Update personal details, change password, upload a profile photo. |
| **Book Search** | Search by title, author, or ISBN with case‑insensitive matching. |
| **Active Loans Summary** | View current checkouts with due dates, renewal counts, and fines. |
| **Checkout History** | See all past loans with fine details. |
| **Place Holds** | Reserve a book that is currently checked out. |
| **Reading Lists** | Create custom lists (e.g., “Favorites”) and add/remove books. |
| **Tags** | Add personal tags to books (e.g., “fiction”, “classic”). |
| **Purchase Suggestions** | Suggest new books for the library to acquire. |
| **Messages** | Receive system notifications (hold ready, overdue alerts, etc.). |
| **Search History** | View your recent search queries. |

### 👩‍🏫 For Librarians
| Feature | Description |
|---------|-------------|
| **Checkout Books** | Lend a copy to a student by entering user ID and copy barcode. |
| **Return Books** | Process returns with **automatic fine calculation** ($0.50/day overdue). |
| **Manage Holds** | View all pending hold requests and mark them as **fulfilled** (ready for pickup). |
| **Add New Books** | Insert new titles into the catalog (ISBN, publisher, location, etc.). |
| **Review Suggestions** | See all student purchase suggestions and approve/reject them. |

---

## 🧱 Technology Stack

| Layer          | Technology |
|----------------|------------|
| **Backend**    | Flask (Python 3.10+) |
| **Database**   | PostgreSQL (≥ 14) |
| **Authentication** | JWT (JSON Web Tokens) + bcrypt |
| **Database Driver** | psycopg2 (raw SQL) |
| **Frontend**   | Vanilla HTML + CSS + JavaScript (with a reusable API client) |
| **Testing**    | Python `unittest`‑style suite + Postman |
| **CORS**       | Flask-CORS enabled for cross‑origin requests |
| **Environment**| python‑dotenv for configuration |

---

## 🗄️ Database Schema

The system uses **12 tables** in a normalized (3NF) design, with proper foreign keys and indexes for performance.

| Table | Purpose |
|-------|---------|
| `users` | Stores student/librarian accounts (email, bcrypt hash, role). |
| `authors` | Author names (many‑to‑many with books). |
| `books` | Master book records (title, ISBN, publisher, etc.). |
| `book_authors` | Join table linking books to authors. |
| `copies` | Individual physical copies (barcode, status, shelf location). |
| `loans` | Checkout records (user, copy, dates, renewals, fines). |
| `holds` | Book reservation requests (active, fulfilled, cancelled). |
| `searches` | User search logs (query, timestamp). |
| `lists` | User‑created reading lists. |
| `list_items` | Books added to a list. |
| `tags` | User‑defined tags on books. |
| `suggestions` | Purchase suggestions submitted by students. |
| `messages` | System notifications sent to users. |

> 📄 An ER diagram can be generated using the schema file in `sql/schema.dbml` (for dbdiagram.io).

---

## 🔁 Complete User Flow (Step by Step)

### 1. Registration
- A new user visits the **Signup** page and enters:
  - Full name, email, password, role (student or librarian), and optional contact info.
- The backend **hashes** the password using **bcrypt** and stores the user in the `users` table.
- On success, the user is redirected to the **Login** page.

### 2. Login & Authentication
- The user enters email and password.
- The backend verifies credentials, compares the password hash, and issues a **JWT token** (valid for 24 hours).
- The token is stored on the client (localStorage) and sent in the `Authorization` header for all subsequent requests.

### 3. Student Dashboard
After login, a student can:
- **View/Edit Profile** – Update name, contact details, and change password.
- **See Active Loans** – List of books currently checked out with due dates and a **Renew** button (max 3 renewals).
- **Search Books** – by title, author, or ISBN.
- **Place Holds** – Reserve a book. The request is stored in the `holds` table with status `'active'`.
- **Manage Reading Lists** – Create lists and add/remove books.
- **Add Tags** – Categorise books with personal tags.
- **Submit Purchase Suggestions** – Suggest books for the library to buy.
- **View Messages** – Receive notifications (e.g., “Your hold is ready”).

### 4. Placing a Hold
- A student searches for a book and clicks **“Place Hold”**.
- The system checks for an existing active hold on the same book for this user and prevents duplicates.
- The hold is stored with status `'active'`.

### 5. Librarian – Fulfilling a Hold
- The librarian logs in and goes to **“Pending Holds”**.
- All active holds are displayed with user and book details.
- The librarian clicks **“Fulfill”**:
  - The hold status changes to `'fulfilled'`.
  - A system message is sent to the student: *“Your hold for 'Book Title' is now available for pickup.”*

### 6. Librarian – Checkout
- The librarian provides the student ID and copy barcode.
- The system verifies the copy is `'available'`, creates a loan record, and updates the copy status to `'checked out'`.
- The due date is set to 14 days from today.

### 7. Librarian – Return
- The librarian enters the loan ID and clicks **“Return”**.
- If overdue, a fine is calculated ($0.50 per day) and stored in the loan record.
- The copy status is set back to `'available'`.

### 8. Librarian – Add Book
- The librarian fills in book details (title, ISBN, publisher, location, etc.).
- A new record is inserted into `books`, and one available copy is created with a generated barcode.

### 9. Librarian – Manage Suggestions
- The librarian views all pending purchase suggestions.
- Each suggestion can be updated to `'reviewed'`, `'approved'`, or `'rejected'`.

---

## 📬 API Endpoints (Summary)

All endpoints return JSON. Full documentation is available in the code comments.

| Category | Method | Endpoint | Description |
|----------|--------|----------|-------------|
| Auth | POST | `/register` | Create a new user. |
| Auth | POST | `/login` | Login & get JWT token. |
| Profile | GET, PUT | `/api/users/me` | Get/update profile. |
| Profile | PUT | `/api/users/me/password` | Change password. |
| Loans | GET | `/api/users/me/summary` | Active loans. |
| Loans | GET | `/api/users/me/checkout-history` | Past loans. |
| Loans | GET | `/api/users/me/charges` | Unpaid fines. |
| Loans | POST, PUT | `/api/loans`, `/api/loans/<id>/return` | Checkout/return (librarian). |
| Loans | PUT | `/api/loans/<id>/renew` | Renew a loan. |
| Books | GET | `/api/books?q=...` | Search books. |
| Books | POST | `/api/books` | Add book (librarian). |
| Holds | POST, GET, PUT | `/api/holds`, `/api/holds/<id>/fulfill`, `/api/holds/<id>/cancel` | Place, fulfill, cancel holds. |
| Holds | GET | `/api/users/me/holds` | View user’s holds. |
| Lists | GET, POST, DELETE, PUT | `/api/users/me/lists`, `/api/lists/<id>/...` | CRUD for reading lists. |
| Tags | GET, POST, DELETE | `/api/users/me/tags`, `/api/tags`, `/api/tags/<id>` | Manage tags. |
| Suggestions | POST, GET, PUT | `/api/suggestions`, `/api/suggestions/<id>` | Submit and manage suggestions. |
| Messages | GET, PUT | `/api/users/me/messages`, `/api/users/me/messages/<id>/read` | View and mark messages. |

---

## 🛠️ Setup Instructions

### Prerequisites
- **Python 3.10+**
- **PostgreSQL** (≥ 14)
- `pip` and `conda` (optional)

### Step 1: Clone the Repository
```bash
git clone https://github.com/your-username/library-management-system.git
cd library-management-system