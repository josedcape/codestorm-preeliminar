// Electron main process
const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { exec } = require('child_process');
const chokidar = require('chokidar');

// Keep a global reference of the window object to prevent garbage collection
let mainWindow;
let flaskProcess;
let fileWatcher;

// Function to create the main application window
function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js')
        },
        icon: path.join(__dirname, 'assets/icon.png')
    });

    // Load the initial HTML file
    mainWindow.loadFile(path.join(__dirname, 'index.html'));

    // Open DevTools in development mode
    // mainWindow.webContents.openDevTools();

    // Handle window close
    mainWindow.on('closed', () => {
        mainWindow = null;
        
        // Stop file watcher
        if (fileWatcher) {
            fileWatcher.close();
        }
    });
}

// Start the Flask server when Electron app is ready
function startFlaskServer() {
    const flaskCommand = 'python main.py';
    
    flaskProcess = exec(flaskCommand, (error, stdout, stderr) => {
        if (error) {
            console.error(`Flask server error: ${error}`);
            return;
        }
        console.log(`Flask stdout: ${stdout}`);
        console.error(`Flask stderr: ${stderr}`);
    });

    // Wait for the Flask server to start
    setTimeout(() => {
        mainWindow.loadURL('http://localhost:5000');
    }, 2000);
}

// Start file watcher to monitor file system changes
function startFileWatcher() {
    const watchPath = '.';
    fileWatcher = chokidar.watch(watchPath, {
        ignored: /(^|[\/\\])\..|(node_modules)/,
        persistent: true,
        ignoreInitial: true
    });

    fileWatcher
        .on('add', path => {
            if (mainWindow) {
                mainWindow.webContents.send('file-change', { type: 'add', path });
            }
        })
        .on('change', path => {
            if (mainWindow) {
                mainWindow.webContents.send('file-change', { type: 'change', path });
            }
        })
        .on('unlink', path => {
            if (mainWindow) {
                mainWindow.webContents.send('file-change', { type: 'delete', path });
            }
        })
        .on('addDir', path => {
            if (mainWindow) {
                mainWindow.webContents.send('file-change', { type: 'addDir', path });
            }
        })
        .on('unlinkDir', path => {
            if (mainWindow) {
                mainWindow.webContents.send('file-change', { type: 'unlinkDir', path });
            }
        });
}

// Initialize app when ready
app.whenReady().then(() => {
    createWindow();
    startFlaskServer();
    startFileWatcher();

    // On macOS, re-create window when dock icon is clicked
    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

// IPC handlers for terminal commands
ipcMain.handle('execute-command', async (event, command) => {
    return new Promise((resolve, reject) => {
        exec(command, { maxBuffer: 1024 * 1024 }, (error, stdout, stderr) => {
            resolve({
                stdout,
                stderr: error ? error.message : stderr,
                exitCode: error ? error.code : 0
            });
        });
    });
});

// Quit when all windows are closed, except on macOS
app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
    
    // Kill the Flask server process
    if (flaskProcess) {
        flaskProcess.kill();
    }
    
    // Close file watcher
    if (fileWatcher) {
        fileWatcher.close();
    }
});
