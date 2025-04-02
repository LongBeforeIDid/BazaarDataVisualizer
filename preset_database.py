import sqlite3
import os
import sys

def get_resource_path(relative_path):
    """Get the absolute path to a resource, whether running as a script or as a PyInstaller bundle."""
    if hasattr(sys, '_MEIPASS'):
        # If running as a PyInstaller bundle, use the temporary folder
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)  # Use script's directory

def initialize_database():
    # Skip database initialization to prevent creating a new file
    print("Database initialization skipped in read-only mode.")

def insert_preset(name, damage, mult, base_cooldown, low_cap, high_cap, max_cdr):
    db_path = get_resource_path("presets.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Insert a new preset
    cursor.execute("""
        INSERT INTO presets (name, damage, mult, base_cooldown, low_cap, high_cap, max_cdr)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name, damage, mult, base_cooldown, low_cap, high_cap, max_cdr))

    conn.commit()
    conn.close()

def fetch_all_presets():
    db_path = get_resource_path("presets.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Fetch all presets
    cursor.execute("SELECT * FROM presets")
    presets = cursor.fetchall()

    conn.close()
    return presets
