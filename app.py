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
    """Initialize the database with the chores and people tables."""
    try:
        conn = get_db_connection()
        
        # Create people table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS people (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create chores table with completed_by field
        conn.execute('''
            CREATE TABLE IF NOT EXISTS chores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                completed BOOLEAN NOT NULL DEFAULT 0,
                priority TEXT DEFAULT 'medium',
                completed_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (completed_by) REFERENCES people (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise

# Initialize database when the app starts (works with gunicorn)
initialize_database()

@app.route('/')
def index():
    """Serve the main page."""
    return send_from_directory('static', 'index.html')

@app.route('/api/chores', methods=['GET'])
def get_chores():
    """Get all chores."""
    conn = get_db_connection()
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
    
    conn = get_db_connection()
    cursor = conn.execute(
        'INSERT INTO chores (title, description, priority) VALUES (?, ?, ?)',
        (title, description, priority)
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
    
    # If marking as incomplete, clear the completed_by field
    if not completed:
        completed_by = None
    
    conn.execute(
        '''UPDATE chores 
           SET title = ?, description = ?, completed = ?, priority = ?, completed_by = ?, updated_at = CURRENT_TIMESTAMP
           WHERE id = ?''',
        (title, description, completed, priority, completed_by, chore_id)
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

# ============ PEOPLE ENDPOINTS ============

@app.route('/api/people', methods=['GET'])
def get_people():
    """Get all people."""
    conn = get_db_connection()
    people = conn.execute('SELECT * FROM people ORDER BY name ASC').fetchall()
    conn.close()
    
    return jsonify([dict(person) for person in people])

@app.route('/api/people', methods=['POST'])
def create_person():
    """Add a new person."""
    data = request.get_json()
    
    if not data or 'name' not in data:
        return jsonify({'error': 'Name is required'}), 400
    
    name = data['name'].strip()
    
    if not name:
        return jsonify({'error': 'Name cannot be empty'}), 400
    
    conn = get_db_connection()
    try:
        cursor = conn.execute('INSERT INTO people (name) VALUES (?)', (name,))
        conn.commit()
        person_id = cursor.lastrowid
        
        person = conn.execute('SELECT * FROM people WHERE id = ?', (person_id,)).fetchone()
        conn.close()
        
        return jsonify(dict(person)), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'Person with this name already exists'}), 400

@app.route('/api/people/<int:person_id>', methods=['DELETE'])
def delete_person(person_id):
    """Delete a person."""
    conn = get_db_connection()
    person = conn.execute('SELECT * FROM people WHERE id = ?', (person_id,)).fetchone()
    
    if person is None:
        conn.close()
        return jsonify({'error': 'Person not found'}), 404
    
    # Remove person from completed chores (set to NULL)
    conn.execute('UPDATE chores SET completed_by = NULL WHERE completed_by = ?', (person_id,))
    
    # Delete the person
    conn.execute('DELETE FROM people WHERE id = ?', (person_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Person deleted successfully'}), 200

@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    """Get leaderboard with points (completed chores count) for each person."""
    conn = get_db_connection()
    
    leaderboard = conn.execute('''
        SELECT 
            p.id,
            p.name,
            COUNT(c.id) as points
        FROM people p
        LEFT JOIN chores c ON p.id = c.completed_by AND c.completed = 1
        GROUP BY p.id, p.name
        ORDER BY points DESC, p.name ASC
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

