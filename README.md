# 🏠 Chore List App

A beautiful and functional CRUD (Create, Read, Update, Delete) application for managing your chore list. Built with Flask backend and a modern vanilla JavaScript frontend.

## Features

- ✅ **Create** new chores with title, description, and priority
- 📖 **Read** and view all your chores in a beautiful interface
- ✏️ **Update** existing chores with an easy-to-use edit modal
- 🗑️ **Delete** chores you no longer need
- ✓ Mark chores as completed/uncompleted
- 🎨 Priority levels (High, Medium, Low) with color-coded badges
- 📱 Responsive design that works on all devices
- 💾 SQLite database for persistent storage

## 🖥️ Run as Desktop App (Electron) ⭐ RECOMMENDED

The easiest way to use this app is as a desktop application!

### Prerequisites for Desktop App:

- **Node.js** (includes npm) - [Download here](https://nodejs.org/)
  - On Mac, you can also install with: `brew install node`
- **Python 3** (already required)

### Quick Start:

1. **Install Node.js if you haven't already:**
   - Download from: https://nodejs.org/ (LTS version recommended)
   - Or on Mac: `brew install node`

2. **Install dependencies:**
   ```bash
   cd chore-list-app
   
   # Install Python dependencies
   pip3 install -r requirements.txt
   
   # Install Node.js dependencies
   npm install
   ```

3. **Run the desktop app:**
   ```bash
   npm start
   ```

That's it! The app will open in its own window and your chores are saved locally.

### Build Standalone App:

Create a distributable app that doesn't require Python/Node.js installed:

```bash
# For Mac:
npm run package-mac

# For Windows:
npm run package-win

# For Linux:
npm run package-linux
```

The standalone app will be in the `dist/` folder. You can move it anywhere or share it with others!

---

## 🌐 Run in Browser (Web Version)

You can also run it as a traditional web app.

## Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

## Installation

1. **Navigate to the project directory:**
   ```bash
   cd chore-list-app
   ```

2. **Install the required dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

   Or install individually:
   ```bash
   pip install Flask flask-cors
   ```

## Running the Application

1. **Start the Flask server:**
   ```bash
   python app.py
   ```

2. **Open your web browser and navigate to:**
   ```
   http://localhost:5000
   ```

3. **Start managing your chores!**

## Usage

### Adding a Chore
1. Fill in the "Add New Chore" form at the top
2. Enter a title (required)
3. Optionally add a description
4. Select a priority level (Low, Medium, or High)
5. Click "Add Chore"

### Marking a Chore as Complete
- Click the checkbox next to any chore to mark it as complete
- Completed chores will appear with a strikethrough and faded appearance
- Click again to mark as incomplete

### Editing a Chore
1. Click the "Edit" button on any chore
2. Modify the details in the modal that appears
3. Click "Update Chore" to save changes

### Deleting a Chore
1. Click the "Delete" button on any chore
2. Confirm the deletion in the popup dialog

## Project Structure

```
chore-list-app/
│
├── app.py                 # Flask backend with API endpoints
├── requirements.txt       # Python dependencies
├── chores.db             # SQLite database (created automatically)
├── README.md             # This file
│
└── static/
    └── index.html        # Frontend HTML, CSS, and JavaScript
```

## API Endpoints

- `GET /api/chores` - Get all chores
- `GET /api/chores/<id>` - Get a specific chore
- `POST /api/chores` - Create a new chore
- `PUT /api/chores/<id>` - Update a chore
- `DELETE /api/chores/<id>` - Delete a chore

## Technologies Used

- **Backend:** Flask (Python)
- **Database:** SQLite
- **Frontend:** HTML5, CSS3, Vanilla JavaScript
- **Styling:** Custom CSS with gradient backgrounds and modern UI

## Features in Detail

### Priority System
- **High Priority:** Red badge - for urgent chores
- **Medium Priority:** Orange badge - for regular chores
- **Low Priority:** Green badge - for less urgent chores

### Responsive Design
The app is fully responsive and works great on:
- Desktop computers
- Tablets
- Mobile phones

### Database
- Uses SQLite for lightweight, file-based storage
- Automatically creates the database on first run
- Stores: title, description, completion status, priority, and timestamps

## 🚀 Deploy to Cloud (FREE)

This app is ready to deploy to **Render** for free! No credit card required.

### Steps to Deploy:

1. **Push your code to GitHub:**
   - Create a new repository on [GitHub](https://github.com)
   - Run these commands:
   ```bash
   git remote add origin https://github.com/YOUR-USERNAME/chore-list-app.git
   git branch -M main
   git push -u origin main
   ```

2. **Deploy on Render:**
   - Go to [render.com](https://render.com) and sign up (free)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Render will auto-detect the `render.yaml` configuration
   - Click "Create Web Service"
   - Wait 2-3 minutes for deployment

3. **Access your app:**
   - Render will give you a public URL like: `https://chore-list-app-xyz.onrender.com`
   - Share this URL with anyone!

### Important Notes:
- Free tier apps sleep after 15 minutes of inactivity
- First request after sleeping takes ~30 seconds to wake up
- Database is file-based (SQLite), so data persists on Render's disk
- For production use, consider upgrading to Render's paid tier or using PostgreSQL

## Troubleshooting

**Port already in use:**
If port 5000 is already in use, you can change it in `app.py` by modifying the last line:
```python
app.run(debug=True, host='0.0.0.0', port=5001)  # Change to any available port
```

**Database issues:**
If you encounter database issues, you can delete the `chores.db` file and restart the app. A new database will be created automatically.

## Future Enhancements

Potential features for future versions:
- User authentication
- Due dates and reminders
- Categories/tags for chores
- Search and filter functionality
- Dark mode
- Export/import chores

## License

This project is free to use and modify for personal or commercial purposes.

## Author

Built as a basic CRUD application demonstration.

---

Enjoy managing your chores! 🎉

