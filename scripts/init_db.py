"""
Database Initialization Script For The Library Management System.

This Script Connects To The PostgreSQL Database And Executes SQL Files
To Set Up The Database Schema And (Optionally) Load Sample Data.

It Is Intended To Be Run Once During Initial Deployment Or When The
Database Schema Needs To Be Reset.
"""

import sys
import os
import psycopg2

# Add The Project Root Directory To The Python Path To Allow Imports
# From The Application's Modules (e.g., app.config.config).
# This Ensures That The Script Can Find The Config Class Even When
# Run From The Project Root Directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.config import Config


def get_db_connection():
    """
    Establish And Return A New Connection To The PostgreSQL Database
    Using The Settings Defined In The Config Class.

    Returns:
        psycopg2.connection: A Database Connection Object.
    """
    return psycopg2.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        database=Config.DB_NAME,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD
    )


def run_sql_file(file_path):
    """
    Execute An SQL File Against The Database.

    This Function Opens The Specified SQL File, Reads Its Entire Content,
    And Executes It As A Single SQL Statement (Or Batch Of Statements) Using
    The Database Connection.

    Parameters:
        file_path (str): The Path To The SQL File To Execute.

    Raises:
        Exception: If The SQL Execution Fails Or The File Cannot Be Read.
    """
    # Establish A Database Connection And Create A Cursor.
    conn = get_db_connection()
    cur = conn.cursor()

    # Read The Entire SQL File Content.
    with open(file_path, 'r') as f:
        sql = f.read()

    # Execute The SQL Statements. Note: This Assumes The SQL File Contains
    # Valid SQL Commands And Does Not Include Multiple Statements That
    # Require Separate Execution (psycopg2's execute() Can Handle Multiple
    # Statements If They Are Properly Separated).
    cur.execute(sql)

    # Commit The Transaction To Persist The Changes.
    conn.commit()

    # Close The Cursor And The Database Connection To Free Resources.
    cur.close()
    conn.close()


if __name__ == '__main__':
    # Run The Main Schema File To Create All Tables And Indexes.
    # This Is The Core Database Structure Required For The System To Operate.
    run_sql_file('sql/schema.sql')

    # Optionally, Uncomment The Following Line To Load Sample Data For Testing.
    # This File Contains Predefined Authors, Books, Copies, And Loans That
    # Can Be Used To Populate The Database With Initial Content.
    # run_sql_file('sql/sample_data.sql')

    # Print A Success Message To Indicate That The Schema Has Been Updated.
    print("Database schema updated successfully.")