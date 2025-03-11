#!/usr/bin/env python
"""
Database Migration Script
========================

This script performs a migration to add new columns to the TwitterAccount model.
It adds username, display_name, and profile_image_url columns to store Twitter profile information.
"""

import sqlite3
import logging
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Path to SQLite database
DB_PATH = Path('oauth3.db')

def check_columns(conn, table_name, expected_columns):
    """Check if columns exist in a table"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_columns = {row[1] for row in cursor.fetchall()}
    
    missing_columns = [col for col in expected_columns if col not in existing_columns]
    return missing_columns

def add_columns(conn, table_name, columns):
    """Add columns to a table"""
    cursor = conn.cursor()
    for column, column_type in columns.items():
        try:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column} {column_type}")
            logger.info(f"Added column '{column}' to table '{table_name}'")
        except sqlite3.Error as e:
            logger.error(f"Error adding column '{column}': {e}")
            raise

def main():
    # Confirm with the user
    if len(sys.argv) <= 1 or sys.argv[1] != "--confirm":
        print("This script will migrate the database to add new columns.")
        print("Run with --confirm to proceed.")
        return
    
    if not DB_PATH.exists():
        logger.error(f"Database file not found: {DB_PATH}")
        return

    logger.info(f"Connecting to database: {DB_PATH}")
    
    try:
        with sqlite3.connect(str(DB_PATH)) as conn:
            # Check if twitter_accounts table exists
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='twitter_accounts'")
            
            if not cursor.fetchone():
                logger.error("Table 'twitter_accounts' does not exist")
                return
            
            # Check which columns we need to add
            missing_columns = check_columns(
                conn, 
                'twitter_accounts', 
                ['username', 'display_name', 'profile_image_url']
            )
            
            if not missing_columns:
                logger.info("All required columns already exist. No migration needed.")
                return
                
            logger.info(f"Missing columns: {missing_columns}")
            
            # Add missing columns
            columns_to_add = {
                'username': 'TEXT',
                'display_name': 'TEXT',
                'profile_image_url': 'TEXT'
            }
            
            # Filter to only include missing columns
            columns_to_add = {k: v for k, v in columns_to_add.items() if k in missing_columns}
            
            add_columns(conn, 'twitter_accounts', columns_to_add)
            
            logger.info("Migration completed successfully")
            
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
    
if __name__ == "__main__":
    main()