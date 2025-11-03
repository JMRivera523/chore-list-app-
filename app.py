from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
from datetime import datetime, timedelta
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
                assigned_to_all BOOLEAN NOT NULL DEFAULT 1,
                completed_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (completed_by) REFERENCES users (id)
            )
        ''')
        
        # Create chore assignments table (for user-specific assignments)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS chore_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chore_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                completed BOOLEAN NOT NULL DEFAULT 0,
                completed_at TIMESTAMP,
                FOREIGN KEY (chore_id) REFERENCES chores (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Create completion history table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS completion_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chore_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                week_start_date TEXT NOT NULL,
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
        
        # Initialize last reset week (Monday of current week)
        today = datetime.now().date()
        # Get Monday of this week (weekday 0 = Monday)
        days_since_monday = today.weekday()
        monday = today - timedelta(days=days_since_monday)
        conn.execute('''
            INSERT OR IGNORE INTO settings (key, value) VALUES ('last_reset_week', ?)
        ''', (monday.isoformat(),))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise

# Initialize database when the app starts (works with gunicorn)
initialize_database()

def check_and_reset_weekly():
    """Check if it's a new week (Monday) and reset recurring chores if needed."""
    try:
        conn = get_db_connection()
        
        # Get last reset week (Monday)
        result = conn.execute("SELECT value FROM settings WHERE key = 'last_reset_week'").fetchone()
        last_reset_week = result['value'] if result else None
        
        # Get current week's Monday
        today = datetime.now().date()
        days_since_monday = today.weekday()
        this_monday = today - timedelta(days=days_since_monday)
        this_monday_str = this_monday.isoformat()
        
        # If it's a new week (past Sunday night), reset
        if last_reset_week != this_monday_str:
            print(f"New week detected! Resetting for week starting: {this_monday_str}")
            
            # Save completion history for all completed chores from last week
            completed_chores = conn.execute('''
                SELECT id, completed_by FROM chores 
                WHERE completed = 1 AND completed_by IS NOT NULL
            ''').fetchall()
            
            for chore in completed_chores:
                conn.execute('''
                    INSERT INTO completion_history (chore_id, user_id, completed_at, week_start_date)
                    VALUES (?, ?, datetime('now'), ?)
                ''', (chore['id'], chore['completed_by'], last_reset_week or this_monday_str))
            
            # Save assigned chore completions
            assigned_completions = conn.execute('''
                SELECT chore_id, user_id FROM chore_assignments 
                WHERE completed = 1
            ''').fetchall()
            
            for assignment in assigned_completions:
                conn.execute('''
                    INSERT INTO completion_history (chore_id, user_id, completed_at, week_start_date)
                    VALUES (?, ?, datetime('now'), ?)
                ''', (assignment['chore_id'], assignment['user_id'], last_reset_week or this_monday_str))
            
            # Reset recurring chores
            conn.execute('''
                UPDATE chores 
                SET completed = 0, completed_by = NULL, updated_at = CURRENT_TIMESTAMP
                WHERE is_recurring = 1
            ''')
            
            # Reset assigned chore completions
            conn.execute('''
                UPDATE chore_assignments 
                SET completed = 0, completed_at = NULL
            ''')
            
            # Update last reset week
            conn.execute("UPDATE settings SET value = ? WHERE key = 'last_reset_week'", (this_monday_str,))
            
            conn.commit()
            print(f"Reset {len(completed_chores)} chores and {len(assigned_completions)} assignments for new week")
        
        conn.close()
    except Exception as e:
        print(f"Error in check_and_reset_weekly: {e}")

@app.route('/')
def index():
    """Serve the main page."""
    return send_from_directory('static', 'index.html')

@app.route('/api/chores', methods=['GET'])
def get_chores():
    """Get chores with assignments."""
    # Check and reset weekly if it's a new week
    check_and_reset_weekly()
    
    user_id = request.args.get('user_id', type=int)
    is_admin = request.args.get('is_admin', 'false').lower() == 'true'
    
    conn = get_db_connection()
    
    if is_admin:
        # Admins see all chores
        chores = conn.execute('SELECT * FROM chores ORDER BY created_at DESC').fetchall()
    elif user_id:
        # Regular users: incomplete chores (for all) + chores completed by this user
        chores = conn.execute('''
            SELECT * FROM chores 
            WHERE completed = 0 OR completed_by = ?
            ORDER BY created_at DESC
        ''', (user_id,)).fetchall()
    else:
        chores = conn.execute('SELECT * FROM chores ORDER BY created_at DESC').fetchall()
    
    # Add assignment info to each chore
    chores_list = []
    for chore in chores:
        chore_dict = dict(chore)
        
        # Get assignments for this chore
        assignments = conn.execute('''
            SELECT ca.*, u.name as user_name 
            FROM chore_assignments ca
            JOIN users u ON ca.user_id = u.id
            WHERE ca.chore_id = ?
        ''', (chore['id'],)).fetchall()
        
        chore_dict['assignments'] = [dict(a) for a in assignments]
        chores_list.append(chore_dict)
    
    conn.close()
    
    return jsonify(chores_list)

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
    """Create a new chore with optional user assignments."""
    data = request.get_json()
    
    if not data or 'title' not in data:
        return jsonify({'error': 'Title is required'}), 400
    
    title = data['title']
    description = data.get('description', '')
    priority = data.get('priority', 'medium')
    is_recurring = data.get('is_recurring', True)
    assigned_to_all = data.get('assigned_to_all', True)
    assigned_users = data.get('assigned_users', [])  # List of user IDs
    
    conn = get_db_connection()
    cursor = conn.execute(
        'INSERT INTO chores (title, description, priority, is_recurring, assigned_to_all) VALUES (?, ?, ?, ?, ?)',
        (title, description, priority, 1 if is_recurring else 0, 1 if assigned_to_all else 0)
    )
    conn.commit()
    chore_id = cursor.lastrowid
    
    # If assigned to specific users, create assignments
    if not assigned_to_all and assigned_users:
        for user_id in assigned_users:
            conn.execute(
                'INSERT INTO chore_assignments (chore_id, user_id) VALUES (?, ?)',
                (chore_id, user_id)
            )
        conn.commit()
    
    # Fetch the newly created chore with assignments
    chore = conn.execute('SELECT * FROM chores WHERE id = ?', (chore_id,)).fetchone()
    assignments = conn.execute('''
        SELECT ca.*, u.name as user_name 
        FROM chore_assignments ca
        JOIN users u ON ca.user_id = u.id
        WHERE ca.chore_id = ?
    ''', (chore_id,)).fetchall()
    
    conn.close()
    
    chore_dict = dict(chore)
    chore_dict['assignments'] = [dict(a) for a in assignments]
    
    return jsonify(chore_dict), 201

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

@app.route('/api/chores/assignment/<int:assignment_id>/complete', methods=['PUT'])
def complete_assignment():
    """Mark a chore assignment as complete."""
    assignment_id = request.view_args['assignment_id']
    data = request.get_json()
    completed = data.get('completed', True)
    
    conn = get_db_connection()
    conn.execute('''
        UPDATE chore_assignments 
        SET completed = ?, completed_at = ?
        WHERE id = ?
    ''', (1 if completed else 0, datetime.now().isoformat() if completed else None, assignment_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    """Get leaderboard with points (completed chores count) for each user this week."""
    conn = get_db_connection()
    
    # Count completed general chores + completed assignments
    leaderboard = conn.execute('''
        SELECT 
            u.id,
            u.name,
            u.role,
            (
                SELECT COUNT(*) FROM chores c 
                WHERE c.completed_by = u.id AND c.completed = 1
            ) + (
                SELECT COUNT(*) FROM chore_assignments ca 
                WHERE ca.user_id = u.id AND ca.completed = 1
            ) as points
        FROM users u
        ORDER BY points DESC, u.name ASC
    ''').fetchall()
    
    conn.close()
    
    return jsonify([dict(entry) for entry in leaderboard])

@app.route('/api/users/<int:user_id>/history', methods=['GET'])
def get_user_history(user_id):
    """Get completion history for a user (for leaderboard details)."""
    conn = get_db_connection()
    
    # Get completed chores this week
    completed_chores = conn.execute('''
        SELECT c.title, c.completed_by, 'chore' as type
        FROM chores c
        WHERE c.completed_by = ? AND c.completed = 1
    ''', (user_id,)).fetchall()
    
    # Get completed assignments this week
    completed_assignments = conn.execute('''
        SELECT c.title, ca.user_id, 'assignment' as type
        FROM chore_assignments ca
        JOIN chores c ON ca.chore_id = c.id
        WHERE ca.user_id = ? AND ca.completed = 1
    ''', (user_id,)).fetchall()
    
    conn.close()
    
    all_completions = [dict(row) for row in completed_chores] + [dict(row) for row in completed_assignments]
    
    return jsonify(all_completions)

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

