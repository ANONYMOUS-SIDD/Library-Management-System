// JavaScript Client For The Library Management System API
//
// This File Provides A Clean, Reusable Client For Interacting
// With The Library Management System Backend.
//
// It Mirrors The Functionality Of The Python connection.py File,
// Allowing Frontend Applications To Easily Call All API Endpoints
// Without Writing Raw Fetch Calls.
//
// Usage Example:
//   import { signin, search_books } from './connection.js';
//   const [user, status] = await signin('user@example.com', 'password');
//   if (status === 200) {
//     const [books] = await search_books('Harry');
//     console.log(books);
//   }

// Base URL For All API Requests. Change This To Match Your
// Backend Server Address (e.g., 'https://api.example.com').
const API_BASE = 'http://localhost:5000';


// Main Client Class That Handles Authentication, Session
// Management, And All API Calls.
class LMSConnection {
    /**
     * Create A New API Client Instance.
     *
     * @param {string} baseUrl - The Base URL Of The API Server.
     * @param {number} timeout - Request Timeout In Milliseconds (Unused Currently).
     */
    constructor(baseUrl = API_BASE, timeout = 10000) {
        this.baseUrl = baseUrl.replace(/\/+$/, '');  // Remove Trailing Slashes.
        this.timeout = timeout;
        this.token = null;   // JWT Token Stored After Successful Login.
        this.user = null;    // User Object Returned From Login.
    }


    // Internal Request Method
    // Handles All HTTP Requests With Proper Headers, Authentication,
    // Query Parameter Serialization, And Response Parsing.

    /**
     * Send An HTTP Request To The API.
     *
     * @param {string} method - HTTP Method (GET, POST, PUT, DELETE).
     * @param {string} endpoint - API Endpoint (e.g., '/login').
     * @param {object|null} data - Request Payload For POST/PUT Or Query Params For GET.
     * @param {boolean} auth - Whether To Include The JWT Token In The Headers.
     * @returns {Promise<Array>} - A Tuple [responseData, statusCode].
     */
    async _request(method, endpoint, data = null, auth = true) {
        // Build The Full URL.
        let url = this.baseUrl + endpoint;

        // Prepare Headers.
        const headers = { 'Content-Type': 'application/json' };
        if (auth && this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        // Prepare Fetch Options.
        const options = { method, headers };

        // Handle Query Parameters For GET Requests.
        if (method === 'GET' && data) {
            const params = new URLSearchParams(data).toString();
            url += (url.includes('?') ? '&' : '?') + params;
        } else if (data) {
            // For Non-GET Requests, Send Data As JSON Body.
            options.body = JSON.stringify(data);
        }

        try {
            // Execute The Fetch Request.
            const response = await fetch(url, options);

            // Read The Response As Text To Handle Non-JSON Responses Gracefully.
            const text = await response.text();

            // Attempt To Parse JSON; Fallback To A Raw Object If Parsing Fails.
            let json;
            try {
                json = JSON.parse(text);
            } catch (e) {
                json = { raw: text };
            }

            // Return The Parsed Data And The HTTP Status Code.
            return [json, response.status];
        } catch (error) {
            // Handle Network Errors Or Other Exceptions.
            return [{ error: error.message }, 500];
        }
    }


    // Authentication Methods

    /**
     * Register A New User.
     *
     * @param {string} name - Full Name Of The User.
     * @param {string} email - Unique Email Address.
     * @param {string} password - Plain-Text Password (Will Be Hashed On Server).
     * @param {string} role - 'student' Or 'librarian' (Default 'student').
     * @param {string|null} contact_info - Optional Contact Details.
     * @returns {Promise<Array>} - Tuple [responseData, statusCode].
     */
    async register(name, email, password, role = 'student', contact_info = null) {
        const data = { name, email, password, role };
        if (contact_info) data.contact_info = contact_info;
        return this._request('POST', '/register', data, false);
    }

    /**
     * Log In A User And Store The JWT Token.
     *
     * @param {string} email - User's Email.
     * @param {string} password - User's Password.
     * @returns {Promise<Array>} - Tuple [responseData, statusCode].
     */
    async login(email, password) {
        const [result, status] = await this._request('POST', '/login', { email, password }, false);
        if (status === 200) {
            this.token = result.token;
            this.user = result.user;
        }
        return [result, status];
    }


    // User Profile Methods

    /**
     * Get The Profile Of The Currently Authenticated User.
     *
     * @returns {Promise<Array>} - Tuple [profileData, statusCode].
     */
    async get_profile() {
        return this._request('GET', '/api/users/me', null, true);
    }

    /**
     * Update The Profile Of The Authenticated User.
     *
     * @param {string|null} name - New Name (Optional).
     * @param {string|null} contact_info - New Contact Information (Optional).
     * @param {string|null} photo_path - New Photo File Path (Optional).
     * @returns {Promise<Array>} - Tuple [responseData, statusCode].
     */
    async update_profile(name = null, contact_info = null, photo_path = null) {
        const data = {};
        if (name !== null) data.name = name;
        if (contact_info !== null) data.contact_info = contact_info;
        if (photo_path !== null) data.photo_path = photo_path;
        return this._request('PUT', '/api/users/me', data, true);
    }

    /**
     * Change The Password Of The Authenticated User.
     *
     * @param {string} old_password - Current Password.
     * @param {string} new_password - Desired New Password.
     * @returns {Promise<Array>} - Tuple [responseData, statusCode].
     */
    async change_password(old_password, new_password) {
        return this._request('PUT', '/api/users/me/password', { old_password, new_password }, true);
    }


    // Loans And Checkout Methods

    /**
     * Get Active Loans (Checkouts) For The Authenticated User.
     *
     * @returns {Promise<Array>} - Tuple [summaryData, statusCode].
     */
    async get_summary() {
        return this._request('GET', '/api/users/me/summary', null, true);
    }

    /**
     * Get Checkout History (Returned Loans) For The User.
     *
     * @returns {Promise<Array>} - Tuple [historyData, statusCode].
     */
    async get_checkout_history() {
        return this._request('GET', '/api/users/me/checkout-history', null, true);
    }

    /**
     * Get Outstanding Fines For The Authenticated User.
     *
     * @returns {Promise<Array>} - Tuple [chargesData, statusCode].
     */
    async get_charges() {
        return this._request('GET', '/api/users/me/charges', null, true);
    }

    /**
     * Pay A Specific Fine.
     *
     * @param {number} loan_id - ID Of The Loan For Which The Fine Is Being Paid.
     * @returns {Promise<Array>} - Tuple [responseData, statusCode].
     */
    async pay_fine(loan_id) {
        return this._request('POST', '/api/users/me/payfine', { loan_id }, true);
    }

    /**
     * Renew An Active Loan.
     *
     * @param {number} loan_id - ID Of The Loan To Renew.
     * @returns {Promise<Array>} - Tuple [responseData, statusCode].
     */
    async renew_loan(loan_id) {
        return this._request('PUT', `/api/loans/${loan_id}/renew`, null, true);
    }

    /**
     * Perform A Checkout (Librarian Only).
     *
     * @param {number} user_id - ID Of The User Borrowing The Book.
     * @param {number} copy_id - ID Of The Copy Being Checked Out.
     * @returns {Promise<Array>} - Tuple [responseData, statusCode].
     */
    async checkout(user_id, copy_id) {
        return this._request('POST', '/api/loans', { user_id, copy_id }, true);
    }

    /**
     * Process A Return (Librarian Only).
     *
     * @param {number} loan_id - ID Of The Loan Being Returned.
     * @returns {Promise<Array>} - Tuple [responseData, statusCode].
     */
    async return_book(loan_id) {
        return this._request('PUT', `/api/loans/${loan_id}/return`, null, true);
    }


    // Book Methods

    /**
     * Search For Books By Title, ISBN, Or Author.
     *
     * @param {string} query - Search Term.
     * @param {number} limit - Maximum Number Of Results (Default 20).
     * @returns {Promise<Array>} - Tuple [searchResults, statusCode].
     */
    async search_books(query, limit = 20) {
        return this._request('GET', '/api/books', { q: query, limit }, false);
    }

    /**
     * Add A New Book To The Catalog (Librarian Only).
     *
     * @param {string} title - Book Title.
     * @param {string|null} isbn - ISBN (Optional).
     * @param {string|null} call_number - Call Number (Optional).
     * @param {string|null} publisher - Publisher Name (Optional).
     * @param {string|null} published_date - Publication Date (YYYY-MM-DD) (Optional).
     * @param {string|null} location - Shelf Location (Optional).
     * @param {number} total_copies - Total Copies (Default 1).
     * @param {string|null} summary - Book Summary (Optional).
     * @returns {Promise<Array>} - Tuple [responseData, statusCode].
     */
    async add_book(title, isbn = null, call_number = null, publisher = null,
                   published_date = null, location = null, total_copies = 1, summary = null) {
        const data = { title, isbn, call_number, publisher, published_date, location, total_copies, summary };
        // Remove null values so they are not sent in the request.
        Object.keys(data).forEach(key => data[key] === null && delete data[key]);
        return this._request('POST', '/api/books', data, true);
    }


    // Hold Methods

    /**
     * Place A Hold On A Book.
     *
     * @param {number} book_id - ID Of The Book To Reserve.
     * @returns {Promise<Array>} - Tuple [responseData, statusCode].
     */
    async place_hold(book_id) {
        return this._request('POST', '/api/holds', { book_id }, true);
    }

    /**
     * Get Holds For The Authenticated User.
     *
     * @returns {Promise<Array>} - Tuple [holdsData, statusCode].
     */
    async get_my_holds() {
        return this._request('GET', '/api/users/me/holds', null, true);
    }

    /**
     * Get All Pending Holds (Librarian Only).
     *
     * @returns {Promise<Array>} - Tuple [holdsData, statusCode].
     */
    async get_all_holds() {
        return this._request('GET', '/api/holds', null, true);
    }

    /**
     * Fulfill A Hold (Librarian Only).
     *
     * @param {number} hold_id - ID Of The Hold To Fulfill.
     * @returns {Promise<Array>} - Tuple [responseData, statusCode].
     */
    async fulfill_hold(hold_id) {
        return this._request('PUT', `/api/holds/${hold_id}/fulfill`, null, true);
    }

    /**
     * Cancel A Hold.
     *
     * @param {number} hold_id - ID Of The Hold To Cancel.
     * @returns {Promise<Array>} - Tuple [responseData, statusCode].
     */
    async cancel_hold(hold_id) {
        return this._request('PUT', `/api/holds/${hold_id}/cancel`, null, true);
    }


    // Search History Methods

    /**
     * Get Search History For The Authenticated User.
     *
     * @returns {Promise<Array>} - Tuple [historyData, statusCode].
     */
    async get_search_history() {
        return this._request('GET', '/api/users/me/search-history', null, true);
    }

    /**
     * Record A Search Query.
     *
     * @param {string} query - The Search Term.
     * @returns {Promise<Array>} - Tuple [responseData, statusCode].
     */
    async add_search(query) {
        return this._request('POST', '/api/users/me/search-history', { query }, true);
    }


    // Reading Lists Methods

    /**
     * Get All Lists For The Authenticated User.
     *
     * @returns {Promise<Array>} - Tuple [listsData, statusCode].
     */
    async get_lists() {
        return this._request('GET', '/api/users/me/lists', null, true);
    }

    /**
     * Create A New Reading List.
     *
     * @param {string} list_name - Name Of The List.
     * @returns {Promise<Array>} - Tuple [responseData, statusCode].
     */
    async create_list(list_name) {
        return this._request('POST', '/api/users/me/lists', { list_name }, true);
    }

    /**
     * Delete A Reading List (Owner Only).
     *
     * @param {number} list_id - ID Of The List To Delete.
     * @returns {Promise<Array>} - Tuple [responseData, statusCode].
     */
    async delete_list(list_id) {
        return this._request('DELETE', `/api/lists/${list_id}`, null, true);
    }

    /**
     * Rename A Reading List (Owner Only).
     *
     * @param {number} list_id - ID Of The List To Rename.
     * @param {string} new_name - New Name For The List.
     * @returns {Promise<Array>} - Tuple [responseData, statusCode].
     */
    async rename_list(list_id, new_name) {
        return this._request('PUT', `/api/lists/${list_id}`, { list_name: new_name }, true);
    }

    /**
     * Add A Book To A Reading List.
     *
     * @param {number} list_id - ID Of The List.
     * @param {number} book_id - ID Of The Book To Add.
     * @returns {Promise<Array>} - Tuple [responseData, statusCode].
     */
    async add_list_item(list_id, book_id) {
        return this._request('POST', `/api/lists/${list_id}/items`, { book_id }, true);
    }

    /**
     * Remove A Book From A Reading List.
     *
     * @param {number} list_id - ID Of The List.
     * @param {number} book_id - ID Of The Book To Remove.
     * @returns {Promise<Array>} - Tuple [responseData, statusCode].
     */
    async remove_list_item(list_id, book_id) {
        return this._request('DELETE', `/api/lists/${list_id}/items/${book_id}`, null, true);
    }

    /**
     * Get All Books In A Reading List.
     *
     * @param {number} list_id - ID Of The List.
     * @returns {Promise<Array>} - Tuple [itemsData, statusCode].
     */
    async get_list_items(list_id) {
        return this._request('GET', `/api/lists/${list_id}/items`, null, true);
    }


    // Tags Methods

    /**
     * Get All Tags Created By The Authenticated User.
     *
     * @returns {Promise<Array>} - Tuple [tagsData, statusCode].
     */
    async get_tags() {
        return this._request('GET', '/api/users/me/tags', null, true);
    }

    /**
     * Add A Tag To A Book.
     *
     * @param {number} book_id - ID Of The Book.
     * @param {string} tag_text - The Tag Text.
     * @returns {Promise<Array>} - Tuple [responseData, statusCode].
     */
    async add_tag(book_id, tag_text) {
        return this._request('POST', '/api/tags', { book_id, tag: tag_text }, true);
    }

    /**
     * Delete A Tag (Owner Only).
     *
     * @param {number} tag_id - ID Of The Tag To Delete.
     * @returns {Promise<Array>} - Tuple [responseData, statusCode].
     */
    async delete_tag(tag_id) {
        return this._request('DELETE', `/api/tags/${tag_id}`, null, true);
    }


    // Purchase Suggestions Methods

    /**
     * Submit A Purchase Suggestion.
     *
     * @param {string} title - Suggested Book Title.
     * @param {string|null} author - Author (Optional).
     * @param {string|null} notes - Additional Notes (Optional).
     * @returns {Promise<Array>} - Tuple [responseData, statusCode].
     */
    async create_suggestion(title, author = null, notes = null) {
        const data = { title };
        if (author) data.author = author;
        if (notes) data.notes = notes;
        return this._request('POST', '/api/suggestions', data, true);
    }

    /**
     * Get Suggestions Submitted By The Authenticated User.
     *
     * @returns {Promise<Array>} - Tuple [suggestionsData, statusCode].
     */
    async get_my_suggestions() {
        return this._request('GET', '/api/users/me/suggestions', null, true);
    }

    /**
     * Get All Suggestions (Librarian Only).
     *
     * @returns {Promise<Array>} - Tuple [suggestionsData, statusCode].
     */
    async get_all_suggestions() {
        return this._request('GET', '/api/suggestions', null, true);
    }

    /**
     * Update The Status Of A Suggestion (Librarian Only).
     *
     * @param {number} suggestion_id - ID Of The Suggestion.
     * @param {string} status - New Status ('pending', 'reviewed', 'approved', 'rejected').
     * @returns {Promise<Array>} - Tuple [responseData, statusCode].
     */
    async update_suggestion(suggestion_id, status) {
        return this._request('PUT', `/api/suggestions/${suggestion_id}`, { status }, true);
    }


    // Messages Methods

    /**
     * Get Messages For The Authenticated User.
     *
     * @param {boolean} unread_only - If True, Return Only Unread Messages.
     * @returns {Promise<Array>} - Tuple [messagesData, statusCode].
     */
    async get_messages(unread_only = false) {
        const params = unread_only ? { unread: 'true' } : {};
        return this._request('GET', '/api/users/me/messages', params, true);
    }

    /**
     * Mark A Message As Read.
     *
     * @param {number} message_id - ID Of The Message.
     * @returns {Promise<Array>} - Tuple [responseData, statusCode].
     */
    async mark_message_read(message_id) {
        return this._request('PUT', `/api/users/me/messages/${message_id}/read`, null, true);
    }
}


// Global Default Instance And Convenience Functions
// These Match The Python version For Easy Migration.

const _default_client = new LMSConnection();

export function signin(email, password) {
    return _default_client.login(email, password);
}

export function signup(name, email, password, role = 'student', contact_info = null) {
    return _default_client.register(name, email, password, role, contact_info);
}

export function profile() {
    return _default_client.get_profile();
}

export function update_profile(name = null, contact_info = null, photo_path = null) {
    return _default_client.update_profile(name, contact_info, photo_path);
}

export function search_books(query, limit = 20) {
    return _default_client.search_books(query, limit);
}

export function place_hold(book_id) {
    return _default_client.place_hold(book_id);
}

export function get_my_holds() {
    return _default_client.get_my_holds();
}

export function cancel_hold(hold_id) {
    return _default_client.cancel_hold(hold_id);
}

export function get_summary() {
    return _default_client.get_summary();
}

export function checkout(user_id, copy_id) {
    return _default_client.checkout(user_id, copy_id);
}

export function return_book(loan_id) {
    return _default_client.return_book(loan_id);
}

export function add_book(title, options = {}) {
    return _default_client.add_book(title, options.isbn, options.call_number, options.publisher,
                                    options.published_date, options.location, options.total_copies, options.summary);
}

export function get_all_holds() {
    return _default_client.get_all_holds();
}

export function fulfill_hold(hold_id) {
    return _default_client.fulfill_hold(hold_id);
}

export function get_my_suggestions() {
    return _default_client.get_my_suggestions();
}

export function get_all_suggestions() {
    return _default_client.get_all_suggestions();
}

export function update_suggestion(suggestion_id, status) {
    return _default_client.update_suggestion(suggestion_id, status);
}

export function get_messages(unread_only = false) {
    return _default_client.get_messages(unread_only);
}

export function mark_message_read(message_id) {
    return _default_client.mark_message_read(message_id);
}

// Export The Class And The Default Instance As Well.
export default _default_client;