// Renderer process script for Electron
document.addEventListener('DOMContentLoaded', () => {
    // DOM elements
    const instructionInput = document.getElementById('instruction-input');
    const executeBtn = document.getElementById('execute-btn');
    const commandDisplay = document.getElementById('command-display');
    const outputDisplay = document.getElementById('output-display');
    const fileExplorer = document.getElementById('file-explorer');
    const refreshBtn = document.getElementById('refresh-btn');
    
    // Current working directory
    let currentDirectory = '.';
    
    // Command history
    let commandHistory = [];
    let historyIndex = -1;
    
    // Initialize
    init();
    
    // Function to initialize the application
    function init() {
        // Load initial file list
        updateFileExplorer();
        
        // Set up event listeners
        setupEventListeners();
        
        // Set up file change listener
        window.electronAPI.onFileChange((data) => {
            console.log('File change detected:', data);
            updateFileExplorer();
        });
    }
    
    // Set up event listeners
    function setupEventListeners() {
        // Execute button click
        executeBtn.addEventListener('click', processInstruction);
        
        // Enter key in input (with ctrl or cmd)
        instructionInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                processInstruction();
            }
        });
        
        // Refresh button click
        refreshBtn.addEventListener('click', updateFileExplorer);
        
        // Setup other event listeners...
    }
    
    // Process instruction and execute command
    async function processInstruction() {
        const instruction = instructionInput.value.trim();
        if (!instruction) return;
        
        // Add loading indicator
        executeBtn.classList.add('loading');
        
        try {
            // First, get the terminal command from the Flask API
            const commandResponse = await fetch('http://localhost:5000/api/process_instructions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ instruction })
            });
            
            const commandData = await commandResponse.json();
            if (commandData.error) {
                displayError(commandData.error);
                return;
            }
            
            const command = commandData.command;
            commandDisplay.textContent = command;
            
            // Add to command history
            commandHistory.push(instruction);
            historyIndex = commandHistory.length;
            
            // Execute the command using Electron's IPC
            const result = await window.electronAPI.executeCommand(command);
            
            // Display the output
            let output = '';
            if (result.stdout) output += result.stdout;
            if (result.stderr) output += '\n' + result.stderr;
            
            outputDisplay.textContent = output;
            
            // Update file explorer after command execution
            updateFileExplorer();
            
        } catch (error) {
            console.error('Error:', error);
            displayError('Failed to process instruction: ' + error.message);
        } finally {
            // Remove loading indicator
            executeBtn.classList.remove('loading');
        }
    }
    
    // Update file explorer
    async function updateFileExplorer() {
        try {
            const response = await fetch('http://localhost:5000/api/list_files', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ directory: currentDirectory })
            });
            
            const data = await response.json();
            if (data.error) {
                displayFileExplorerError(data.error);
                return;
            }
            
            // Update directory path display
            document.getElementById('directory-path').textContent = currentDirectory;
            
            // Render file list
            renderFileExplorer(data.files);
            
        } catch (error) {
            console.error('Error fetching files:', error);
            displayFileExplorerError('Failed to fetch files: ' + error.message);
        }
    }
    
    // Render file explorer with the file list
    function renderFileExplorer(files) {
        fileExplorer.innerHTML = '';
        
        // Add parent directory navigation if not in root
        if (currentDirectory !== '.') {
            const parentItem = createFileItem('..', 'directory');
            parentItem.addEventListener('click', () => {
                navigateToDirectory('..');
            });
            fileExplorer.appendChild(parentItem);
        }
        
        // Sort files - directories first, then alphabetically
        files.sort((a, b) => {
            if (a.type !== b.type) {
                return a.type === 'directory' ? -1 : 1;
            }
            return a.name.localeCompare(b.name);
        });
        
        // Add file items
        files.forEach(file => {
            if (file.name === '.' || file.name === '..') return;
            
            const fileItem = createFileItem(file.name, file.type);
            
            // Add click handler
            fileItem.addEventListener('click', () => {
                if (file.type === 'directory') {
                    navigateToDirectory(file.name);
                } else {
                    // For files, set up a cat command
                    instructionInput.value = `cat "${currentDirectory}/${file.name}"`;
                    processInstruction();
                }
            });
            
            fileExplorer.appendChild(fileItem);
        });
    }
    
    // Create a file item element
    function createFileItem(name, type) {
        const item = document.createElement('div');
        item.classList.add('file-item', 'd-flex', 'align-items-center');
        
        const icon = document.createElement('i');
        icon.classList.add('file-icon');
        
        if (type === 'directory') {
            icon.classList.add('bi', 'bi-folder-fill');
            item.classList.add('directory');
        } else {
            icon.classList.add('bi', 'bi-file-text');
            item.classList.add('file');
        }
        
        const nameSpan = document.createElement('span');
        nameSpan.textContent = name;
        
        item.appendChild(icon);
        item.appendChild(nameSpan);
        
        return item;
    }
    
    // Navigate to a directory
    function navigateToDirectory(dirName) {
        let newPath;
        
        if (dirName === '..') {
            // Navigate to parent directory
            const parts = currentDirectory.split('/');
            parts.pop();
            newPath = parts.join('/') || '.';
        } else if (dirName.startsWith('/')) {
            // Absolute path
            newPath = dirName;
        } else {
            // Relative path
            newPath = currentDirectory === '.' 
                ? dirName 
                : `${currentDirectory}/${dirName}`;
        }
        
        currentDirectory = newPath;
        updateFileExplorer();
    }
    
    // Display an error message in the output area
    function displayError(errorMessage) {
        const errorDiv = document.createElement('div');
        errorDiv.classList.add('alert', 'alert-danger', 'mt-2');
        errorDiv.textContent = errorMessage;
        
        outputDisplay.textContent = '';
        outputDisplay.appendChild(errorDiv);
    }
    
    // Display a file explorer error
    function displayFileExplorerError(errorMessage) {
        fileExplorer.innerHTML = '';
        
        const errorDiv = document.createElement('div');
        errorDiv.classList.add('alert', 'alert-danger');
        errorDiv.textContent = errorMessage;
        
        fileExplorer.appendChild(errorDiv);
    }
});
