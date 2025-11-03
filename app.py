from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
from datetime import datetime
import os

app = Flask(__name__, static_folder='static')
CORS(app)

DATABASE = 'chores.db'

# Initialize database on startup (important for gunicorn/production)
def initialize_database():
    """Initialize the database on app startup."""
    if not os.path.exists(DATABASE):
        print(f"Database {DATABASE} not found. Creating...")
    init_db()
    print(f"Database initialized: {DATABASE}")

def get_db_connection():
    """Create a database connection."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with users and chores tables."""
    try:
        conn = get_db_connection()
        
        # Create users table with roles
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                role TEXT NOT NULL CHECK(role IN ('admin', 'standard')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Seed default users if table is empty
        count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        if count == 0:
            # Add admins
            conn.execute("INSERT INTO users (name, role) VALUES ('Jordan', 'admin')")
            conn.execute("INSERT INTO users (name, role) VALUES ('Sarah', 'admin')")
            # Add standard users
            conn.execute("INSERT INTO users (name, role) VALUES ('Mason', 'standard')")
            conn.execute("INSERT INTO users (name, role) VALUES ('Liam', 'standard')")
            conn.execute("INSERT INTO users (name, role) VALUES ('Addison', 'standard')")
            print("Seeded default users: Jordan, Sarah (admins), Mason, Liam, Addison (standard)")
        
        # Create chores table with completed_by and recurring fields
        conn.execute('''
            CREATE TABLE IF NOT EXISTS chores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                completed BOOLEAN NOT NULL DEFAULT 0,
                priority TEXT DEFAULT 'medium',
                is_recurring BOOLEAN NOT NULL DEFAULT 1,
                completed_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (completed_by) REFERENCES users (id)
            )
        ''')
        
        # Create completion history table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS completion_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chore_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chore_id) REFERENCES chores (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Create settings table for tracking last reset
        conn.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')
        
        # Initialize last reset date
        today = datetime.now().date().isoformat()
        conn.execute('''
            INSERT OR IGNORE INTO settings (key, value) VALUES ('last_reset_date', ?)
        ''', (today,))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise

# Initialize database when the app starts (works with gunicorn)
initialize_database()

def check_and_reset_daily_chores():
    """Check if it's a new day and reset recurring chores if needed."""
    try:
        conn = get_db_connection()
        
        # Get last reset date
        result = conn.execute("SELECT value FROM settings WHERE key = 'last_reset_date'").fetchone()
        last_reset_date = result['value'] if result else None
        today = datetime.now().date().isoformat()
        
        # If it's a new day, reset recurring chores
        if last_reset_date != today:
            print(f"New day detected! Resetting recurring chores. Last reset: {last_reset_date}, Today: {today}")
            
            # Get all completed recurring chores
            completed_recurring = conn.execute('''
                SELECT id, completed_by FROM chores 
                WHERE completed = 1 AND is_recurring = 1 AND completed_by IS NOT NULL
            ''').fetchall()
            
            # Save completion history before resetting
            for chore in completed_recurring:
                conn.execute('''
                    INSERT INTO completion_history (chore_id, user_id, completed_at)
                    VALUES (?, ?, datetime('now', '-1 day'))
                ''', (chore['id'], chore['completed_by']))
            
            # Reset recurring chores
            conn.execute('''
                UPDATE chores 
                SET completed = 0, completed_by = NULL, updated_at = CURRENT_TIMESTAMP
                WHERE is_recurring = 1
            ''')
            
            # Update last reset date
            conn.execute("UPDATE settings SET value = ? WHERE key = 'last_reset_date'", (today,))
            
            conn.commit()
            print(f"Reset {len(completed_recurring)} recurring chores")
        
        conn.close()
    except Exception as e:
        print(f"Error in check_and_reset_daily_chores: {e}")

@app.route('/')
def index():
    """Serve the main page."""
    return send_from_directory('static', 'index.html')

@app.route('/api/chores', methods=['GET'])
def get_chores():
    """Get chores filtered by user - completed chores only show to the person who completed them."""
    # Check and reset daily chores if it's a new day
    check_and_reset_daily_chores()
    
    user_id = request.args.get('user_id', type=int)
    
    conn = get_db_connection()
    
    if user_id:
        # Get incomplete chores (visible to all) + chores completed by this user
        chores = conn.execute('''
            SELECT * FROM chores 
            WHERE completed = 0 OR completed_by = ?
            ORDER BY created_at DESC
        ''', (user_id,)).fetchall()
    else:
        # No user specified, return all chores
        chores = conn.execute('SELECT * FROM chores ORDER BY created_at DESC').fetchall()
    
    conn.close()
    
    return jsonify([dict(chore) for chore in chores])

@app.route('/api/chores/<int:chore_id>', methods=['GET'])
def get_chore(chore_id):
    """Get a specific chore by ID."""
    conn = get_db_connection()
    chore = conn.execute('SELECT * FROM chores WHERE id = ?', (chore_id,)).fetchone()
    conn.close()
    
    if chore is None:
        return jsonify({'error': 'Chore not found'}), 404
    
    return jsonify(dict(chore))

@app.route('/api/chores', methods=['POST'])
def create_chore():
    """Create a new chore."""
    data = request.get_json()
    
    if not data or 'title' not in data:
        return jsonify({'error': 'Title is required'}), 400
    
    title = data['title']
    description = data.get('description', '')
    priority = data.get('priority', 'medium')
    is_recurring = data.get('is_recurring', True)  # Default to recurring
    
    conn = get_db_connection()
    cursor = conn.execute(
        'INSERT INTO chores (title, description, priority, is_recurring) VALUES (?, ?, ?, ?)',
        (title, description, priority, 1 if is_recurring else 0)
    )
    conn.commit()
    chore_id = cursor.lastrowid
    
    # Fetch the newly created chore
    chore = conn.execute('SELECT * FROM chores WHERE id = ?', (chore_id,)).fetchone()
    conn.close()
    
    return jsonify(dict(chore)), 201

@app.route('/api/chores/<int:chore_id>', methods=['PUT'])
def update_chore(chore_id):
    """Update an existing chore."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    conn = get_db_connection()
    chore = conn.execute('SELECT * FROM chores WHERE id = ?', (chore_id,)).fetchone()
    
    if chore is None:
        conn.close()
        return jsonify({'error': 'Chore not found'}), 404
    
    title = data.get('title', chore['title'])
    description = data.get('description', chore['description'])
    completed = data.get('completed', chore['completed'])
    priority = data.get('priority', chore['priority'])
    completed_by = data.get('completed_by', chore['completed_by'])
    is_recurring = data.get('is_recurring', chore['is_recurring'])
    
    # If marking as incomplete, clear the completed_by field
    if not completed:
        completed_by = None
    
    conn.execute(
        '''UPDATE chores 
           SET title = ?, description = ?, completed = ?, priority = ?, completed_by = ?, is_recurring = ?, updated_at = CURRENT_TIMESTAMP
           WHERE id = ?''',
        (title, description, completed, priority, completed_by, 1 if is_recurring else 0, chore_id)
    )
    conn.commit()
    
    # Fetch the updated chore
    updated_chore = conn.execute('SELECT * FROM chores WHERE id = ?', (chore_id,)).fetchone()
    conn.close()
    
    return jsonify(dict(updated_chore))

@app.route('/api/chores/<int:chore_id>', methods=['DELETE'])
def delete_chore(chore_id):
    """Delete a chore."""
    conn = get_db_connection()
    chore = conn.execute('SELECT * FROM chores WHERE id = ?', (chore_id,)).fetchone()
    
    if chore is None:
        conn.close()
        return jsonify({'error': 'Chore not found'}), 404
    
    conn.execute('DELETE FROM chores WHERE id = ?', (chore_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Chore deleted successfully'}), 200

# ============ USER ENDPOINTS ============

@app.route('/api/users', methods=['GET'])
def get_users():
    """Get all users."""
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users ORDER BY name ASC').fetchall()
    conn.close()
    
    return jsonify([dict(user) for user in users])

@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    """Get leaderboard with points (completed chores count) for each user."""
    conn = get_db_connection()
    
    leaderboard = conn.execute('''
        SELECT 
            u.id,
            u.name,
            u.role,
            COUNT(c.id) as points
        FROM users u
        LEFT JOIN chores c ON u.id = c.completed_by AND c.completed = 1
        GROUP BY u.id, u.name, u.role
        ORDER BY points DESC, u.name ASC
    ''').fetchall()
    
    conn.close()
    
    return jsonify([dict(entry) for entry in leaderboard])

if __name__ == '__main__':
    init_db()
    # Check if running in Electron or standalone
    is_electron = os.environ.get('FLASK_ENV') == 'production'
    debug_mode = not is_electron
    
    # Use PORT environment variable for cloud deployment (Render, Heroku, etc.)
    port = int(os.environ.get('PORT', 5000))
    
    if not is_electron:
        print("Starting Chore List App...")
        print(f"Visit http://localhost:{port} in your browser")
    else:
        print(f"Running on http://localhost:{port}")
    
    app.run(debug=debug_mode, host='0.0.0.0', port=port)

