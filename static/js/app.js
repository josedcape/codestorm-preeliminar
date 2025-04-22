// Codestorm-Assistant main JavaScript file

document.addEventListener('DOMContentLoaded', function() {
    // Initialize app
    window.app = {
        currentDirectory: '/',
        commandHistory: [],
        historyIndex: -1,
        userId: null,
        workspace: null,
        
        // Function to add file action buttons - temporary fix for compatibility
        addFileActionButtons: function() {
            if (window.fileActions && typeof window.fileActions.addFileActionButtons === 'function') {
                window.fileActions.addFileActionButtons();
            }
        },
        
        // DOM elements
        elements: {
            instructionInput: document.getElementById('instruction-input'),
            executeBtn: document.getElementById('execute-btn'),
            commandDisplay: document.getElementById('command-display'),
            outputDisplay: document.getElementById('output-display'),
            fileExplorer: document.getElementById('file-explorer'),
            directoryPath: document.getElementById('directory-path'),
            statusIndicator: document.getElementById('status-indicator'),
            clearBtn: document.getElementById('clear-btn'),
            refreshBtn: document.getElementById('refresh-btn'),
            previousBtn: document.getElementById('previous-btn'),
            nextBtn: document.getElementById('next-btn'),
            workspaceInfo: document.getElementById('workspace-info')
        },
        
        init: function() {
            this.initSession();
            this.bindEvents();
            this.checkServerStatus();
        },
        
        initSession: function() {
            // Get session info or initialize a new one
            fetch('/api/session')
                .then(response => response.json())
                .then(data => {
                    this.userId = data.user_id;
                    this.workspace = data.workspace;
                    
                    if (this.elements.workspaceInfo) {
                        this.elements.workspaceInfo.textContent = `Workspace: ${this.workspace}`;
                    }
                    
                    // Update file explorer after session initialization
                    this.updateFileExplorer();
                })
                .catch(error => {
                    console.error('Error initializing session:', error);
                });
        },
        
        bindEvents: function() {
            // Execute button
            this.elements.executeBtn.addEventListener('click', () => this.processInstruction());
            
            // Clear button
            this.elements.clearBtn.addEventListener('click', () => this.clearTerminal());
            
            // Refresh button
            this.elements.refreshBtn.addEventListener('click', () => this.updateFileExplorer());
            
            // Command history navigation
            this.elements.previousBtn.addEventListener('click', () => this.navigateHistory(-1));
            this.elements.nextBtn.addEventListener('click', () => this.navigateHistory(1));
            
            // Enter key in textarea
            this.elements.instructionInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                    e.preventDefault();
                    this.processInstruction();
                }
            });
        },
        
        checkServerStatus: function() {
            fetch('/api/process_instructions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ instruction: 'echo "Hello"' })
            })
            .then(response => {
                if (response.ok) {
                    this.elements.statusIndicator.classList.remove('status-disconnected');
                    this.elements.statusIndicator.classList.add('status-connected');
                    this.elements.statusIndicator.title = 'Connected to server';
                } else {
                    throw new Error('Server error');
                }
            })
            .catch(error => {
                this.elements.statusIndicator.classList.remove('status-connected');
                this.elements.statusIndicator.classList.add('status-disconnected');
                this.elements.statusIndicator.title = 'Disconnected from server';
                console.error('Server status check failed:', error);
            });
        },
        
        processInstruction: function() {
            const instruction = this.elements.instructionInput.value.trim();
            if (!instruction) return;
            
            // Add loading indicator
            this.elements.executeBtn.classList.add('loading');
            
            // Save to history
            this.commandHistory.push(instruction);
            this.historyIndex = this.commandHistory.length;
            
            // Cache para respuestas comunes (mejora velocidad)
            const cachedCommands = {
                'hola': "echo '¡Hola! ¿En qué puedo ayudarte hoy?'",
                'mostrar archivos': 'ls -la',
                'listar': 'ls -la',
                'archivos': 'ls -la',
                'fecha': 'date',
                'hora': 'date +%H:%M:%S',
                'ayuda': "echo 'Puedo convertir tus instrucciones en comandos de terminal'"
            };
            
            // Intenta usar caché local primero antes de llamar al servidor
            const lowerInstruction = instruction.toLowerCase();
            for (const [key, cmd] of Object.entries(cachedCommands)) {
                if (lowerInstruction.includes(key)) {
                    // Mostrar el comando generado
                    this.elements.commandDisplay.textContent = cmd;
                    
                    // Ejecutar directamente sin llamar al servidor
                    this.executeCommandDirectly(cmd, instruction);
                    return; // Termina la función aquí si encuentra coincidencia
                }
            }
            
            // Get the selected model (default to OpenAI)
            const modelSelect = document.getElementById('model-select');
            const selectedModel = modelSelect ? modelSelect.value : 'openai';
            
            // Process the instruction through the Flask backend
            // Mostrar indicador de progreso
            this.elements.executeBtn.disabled = true;
            this.elements.executeBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Procesando...';
            
            // Procesar la instrucción
            fetch('/api/process_instructions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    instruction: instruction,
                    model: selectedModel
                })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Error del servidor: ${response.status} ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.error) {
                    this.displayError(data.error);
                    return null;
                }
                
                const command = data.command;
                this.elements.commandDisplay.textContent = command;
                
                // Mostrar un mensaje de éxito
                if (window.fileActions && typeof window.fileActions.showNotification === 'function') {
                    window.fileActions.showNotification('Comando generado correctamente', 'success');
                }
                
                // Execute the command
                return fetch('/api/execute_command', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ 
                        command: command,
                        instruction: instruction,
                        model: selectedModel
                    })
                });
            })
            .then(response => {
                if (!response || !response.ok) {
                    throw new Error(`Error del servidor: ${response ? response.status + ' ' + response.statusText : 'No hay respuesta'}`);
                }
                return response.json();
            })
            .then(data => {
                if (!data) return;
                
                if (data.error) {
                    this.displayError(data.error);
                    return;
                }
                
                // Display command output
                let output = '';
                if (data.stdout) output += data.stdout;
                if (data.stderr) output += '\n' + data.stderr;
                
                this.elements.outputDisplay.textContent = output;
                
                // Update file explorer after command execution
                this.updateFileExplorer();
            })
            .catch(error => {
                console.error('Error:', error);
                this.displayError('Failed to process instruction: ' + error.message);
            })
            .finally(() => {
                // Remove loading indicator
                this.elements.executeBtn.disabled = false;
                this.elements.executeBtn.innerHTML = 'Ejecutar';
            });
        },
        
        displayError: function(errorMessage) {
            const errorDiv = document.createElement('div');
            errorDiv.classList.add('alert', 'alert-danger', 'mt-2');
            errorDiv.textContent = errorMessage;
            
            this.elements.outputDisplay.textContent = '';
            this.elements.outputDisplay.appendChild(errorDiv);
        },
        
        clearTerminal: function() {
            this.elements.commandDisplay.textContent = '';
            this.elements.outputDisplay.textContent = '';
            this.elements.instructionInput.value = '';
        },
        
        updateFileExplorer: function() {
            // Sanitize current directory
            let directory = this.currentDirectory;
            
            // Make sure directory is not undefined and has a value
            if (!directory || directory === undefined) {
                directory = '/';
                this.currentDirectory = '/';
            }
            
            // Display loading indicator
            this.elements.fileExplorer.innerHTML = '<div class="loading-spinner"></div>';
            
            fetch('/api/list_files', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ directory: directory })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Error del servidor: ${response.status} ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.error) {
                    this.displayFileExplorerError(data.error);
                    return;
                }
                
                // Update current directory display
                if (data.current_dir) {
                    this.currentDirectory = data.current_dir;
                }
                
                this.elements.directoryPath.textContent = this.currentDirectory;
                this.renderFileExplorer(data.files || []);
                
                // Add Create File and Create Folder buttons if available
                if (window.fileActions && typeof window.fileActions.addFileActionButtons === 'function') {
                    window.fileActions.addFileActionButtons();
                }
            })
            .catch(error => {
                console.error('Error fetching files:', error);
                this.displayFileExplorerError('Failed to fetch files: ' + error.message);
            });
        },
        
        renderFileExplorer: function(files) {
            const fileExplorer = this.elements.fileExplorer;
            fileExplorer.innerHTML = '';
            
            // Add parent directory navigation if not in root
            if (this.currentDirectory !== '.') {
                const parentItem = this.createFileItem('..', 'directory');
                parentItem.addEventListener('click', () => {
                    this.navigateToDirectory('..');
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
                
                const fileItem = this.createFileItem(file.name, file.type);
                
                // Add click handler
                fileItem.addEventListener('click', () => {
                    if (file.type === 'directory') {
                        this.navigateToDirectory(file.name);
                    } else {
                        // Open file in editor
                        const filePath = this.currentDirectory === '/' 
                            ? file.name 
                            : `${this.currentDirectory.replace(/^\//, '')}/${file.name}`;
                        window.location.href = `/edit/${filePath}`;
                    }
                });
                
                fileExplorer.appendChild(fileItem);
            });
        },
        
        createFileItem: function(name, type) {
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
        },
        
        navigateToDirectory: function(dirName) {
            let newPath;
            
            if (dirName === '..') {
                // Navigate to parent directory
                const parts = this.currentDirectory.split('/').filter(p => p);
                parts.pop();
                newPath = parts.length ? '/' + parts.join('/') : '/';
            } else if (dirName.startsWith('/')) {
                // Absolute path
                newPath = dirName;
            } else {
                // Relative path
                newPath = this.currentDirectory === '/' 
                    ? '/' + dirName 
                    : `${this.currentDirectory}/${dirName}`;
            }
            
            // Normalize path for consistency
            if (!newPath.startsWith('/')) {
                newPath = '/' + newPath;
            }
            
            // Remove any double slashes
            newPath = newPath.replace(/\/\//g, '/');
            
            this.currentDirectory = newPath;
            this.updateFileExplorer();
        },
        
        displayFileExplorerError: function(errorMessage) {
            this.elements.fileExplorer.innerHTML = '';
            
            const errorDiv = document.createElement('div');
            errorDiv.classList.add('alert', 'alert-danger');
            errorDiv.textContent = errorMessage;
            
            this.elements.fileExplorer.appendChild(errorDiv);
        },
        
        createNewFile: function() {
            const fileName = prompt('Nombre del archivo:');
            if (!fileName || fileName.trim() === '') return;
            
            const path = this.currentDirectory === '/' 
                ? fileName 
                : `${this.currentDirectory.replace(/^\//, '')}/${fileName}`;
                
            fetch('/api/create_file', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    file_path: path,
                    content: ''
                })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Error del servidor: ${response.status} ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.error) {
                    this.displayFileExplorerError(data.error);
                    return;
                }
                
                // Redirect to edit the new file
                window.location.href = `/edit/${path}`;
            })
            .catch(error => {
                console.error('Error creating file:', error);
                this.displayFileExplorerError('Error creating file: ' + error.message);
            });
        },
        
        createNewFolder: function() {
            const folderName = prompt('Nombre de la carpeta:');
            if (!folderName || folderName.trim() === '') return;
            
            const path = this.currentDirectory === '/' 
                ? folderName 
                : `${this.currentDirectory.replace(/^\//, '')}/${folderName}`;
                
            fetch('/api/create_file', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    file_path: `${path}/.keep`,
                    content: ''
                })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Error del servidor: ${response.status} ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.error) {
                    this.displayFileExplorerError(data.error);
                    return;
                }
                
                // Refresh file explorer
                this.updateFileExplorer();
            })
            .catch(error => {
                console.error('Error creating folder:', error);
                this.displayFileExplorerError('Error creating folder: ' + error.message);
            });
        },
        
        // Función para ejecutar comandos directamente desde el caché
        executeCommandDirectly: function(command, instruction) {
            // Mostrar indicador de carga
            this.elements.executeBtn.disabled = true;
            this.elements.executeBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Procesando...';
            
            // Ejecutar el comando directamente (desde caché)
            fetch('/api/execute_command', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    command: command,
                    instruction: instruction,
                    model: 'cache' // Indicamos que usamos caché local
                })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Error del servidor: ${response.status} ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.error) {
                    this.displayError(data.error);
                    return;
                }
                
                // Mostrar salida del comando
                let output = '';
                if (data.stdout) output += data.stdout;
                if (data.stderr) output += '\n' + data.stderr;
                
                this.elements.outputDisplay.textContent = output;
                
                // Actualizar explorador de archivos
                this.updateFileExplorer();
                
                // Notificar éxito
                if (window.fileActions && typeof window.fileActions.showNotification === 'function') {
                    window.fileActions.showNotification('Comando ejecutado correctamente', 'success');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                this.displayError('Error ejecutando comando: ' + error.message);
            })
            .finally(() => {
                // Quitar indicador de carga
                this.elements.executeBtn.disabled = false;
                this.elements.executeBtn.innerHTML = 'Ejecutar';
            });
        },
        
        navigateHistory: function(direction) {
            if (this.commandHistory.length === 0) return;
            
            this.historyIndex += direction;
            
            // Ensure index stays within bounds
            if (this.historyIndex < 0) this.historyIndex = 0;
            if (this.historyIndex >= this.commandHistory.length) {
                this.historyIndex = this.commandHistory.length - 1;
            }
            
            // Set the input value to the command at the current index
            this.elements.instructionInput.value = this.commandHistory[this.historyIndex];
        }
    };
    
    // Initialize the app
    app.init();
});
