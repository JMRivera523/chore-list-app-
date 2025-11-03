const { app, BrowserWindow } = require('electron');
const { spawn } = require('child_process');
const path = require('path');

let flaskProcess = null;
let mainWindow = null;

function startFlaskServer() {
  return new Promise((resolve, reject) => {
    // Start Flask server
    flaskProcess = spawn('python3', ['app.py'], {
      cwd: __dirname,
      env: { ...process.env, FLASK_ENV: 'production' }
    });

    flaskProcess.stdout.on('data', (data) => {
      console.log(`Flask: ${data}`);
      // Wait for Flask to be ready
      if (data.toString().includes('Running on')) {
        setTimeout(resolve, 1000); // Give it a second to fully start
      }
    });

    flaskProcess.stderr.on('data', (data) => {
      console.error(`Flask Error: ${data}`);
    });

    flaskProcess.on('error', (error) => {
      console.error(`Failed to start Flask: ${error}`);
      reject(error);
    });

    // Fallback: resolve after 3 seconds even if we don't see the message
    setTimeout(resolve, 3000);
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    icon: path.join(__dirname, 'assets/icon.png'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
    title: 'Chore List App',
    backgroundColor: '#667eea'
  });

  // Load the Flask app
  mainWindow.loadURL('http://localhost:5000');

  // Open DevTools in development (optional)
  // mainWindow.webContents.openDevTools();

  mainWindow.on('closed', function () {
    mainWindow = null;
  });

  // Handle navigation errors
  mainWindow.webContents.on('did-fail-load', () => {
    console.log('Failed to load, retrying...');
    setTimeout(() => {
      mainWindow.loadURL('http://localhost:5000');
    }, 1000);
  });
}

app.on('ready', async () => {
  try {
    console.log('Starting Flask server...');
    await startFlaskServer();
    console.log('Creating window...');
    createWindow();
  } catch (error) {
    console.error('Failed to start application:', error);
    app.quit();
  }
});

app.on('window-all-closed', function () {
  // Kill Flask process when app closes
  if (flaskProcess) {
    flaskProcess.kill();
  }
  app.quit();
});

app.on('activate', function () {
  if (mainWindow === null) {
    createWindow();
  }
});

// Cleanup on quit
app.on('quit', () => {
  if (flaskProcess) {
    flaskProcess.kill();
  }
});

