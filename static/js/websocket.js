// WebSocket client for real-time file updates
document.addEventListener('DOMContentLoaded', function() {
    // Check if SocketIO is available
    if (typeof io === 'undefined') {
        // Load Socket.IO client library if not already loaded
        const script = document.createElement('script');
        script.src = 'https://cdn.socket.io/4.6.1/socket.io.min.js';
        script.onload = initializeSocket;
        document.head.appendChild(script);
    } else {
        initializeSocket();
    }
    
    function initializeSocket() {
        // Connect to Socket.IO server with more resilient configuration
        const socket = io({
            transports: ['websocket', 'polling'], // Fallback to polling if websocket fails
            reconnection: true,
            reconnectionAttempts: 10,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000,
            timeout: 20000
        });
        
        // Store socket globally for other scripts to use
        window.socketClient = socket;
        
        // Socket connection handlers
        socket.on('connect', function() {
            console.log('Connected to WebSocket server');
            
            // Join the current workspace room
            const userId = localStorage.getItem('user_id') || 'default';
            socket.emit('join_workspace', {
                workspace_id: userId
            });
            
            // Update UI to show connected status
            updateConnectionStatus(true);
        });
        
        socket.on('disconnect', function() {
            console.log('Disconnected from WebSocket server');
            updateConnectionStatus(false);
        });
        
        socket.on('connect_error', function(error) {
            console.error('WebSocket connection error:', error);
            updateConnectionStatus(false);
            
            // Implementar reintentos manuales con backoff exponencial
            setTimeout(() => {
                console.log('Intentando reconectar al WebSocket...');
                socket.connect();
            }, 2000); // Reintento después de 2 segundos
        });
        
        // Manejador de error adicional
        socket.on('error', function(error) {
            console.error('Socket error:', error);
            // No desconectar inmediatamente, dejar que la reconexión automática funcione
        });
        
        // File change notifications
        socket.on('file_change', function(data) {
            console.log('File change notification:', data);
            
            // Update file explorer when a file changes
            if (typeof app !== 'undefined' && app.updateFileExplorer) {
                app.updateFileExplorer();
            }
            
            // Display notification to user
            notifyFileChange(data.type, data.file);
        });
        
        // Command execution notifications
        socket.on('command_executed', function(data) {
            console.log('Command executed notification:', data);
            
            // Update terminal output if needed
            if (typeof app !== 'undefined' && app.updateCommandOutput) {
                app.updateCommandOutput(data);
            }
        });
    }
    
    // Update UI to show WebSocket connection status
    function updateConnectionStatus(connected) {
        const statusIndicator = document.getElementById('status-indicator');
        if (statusIndicator) {
            if (connected) {
                statusIndicator.classList.remove('status-disconnected');
                statusIndicator.classList.add('status-connected');
                statusIndicator.title = 'Connected to server';
            } else {
                statusIndicator.classList.remove('status-connected');
                statusIndicator.classList.add('status-disconnected');
                statusIndicator.title = 'Disconnected from server';
            }
        }
    }
    
    // Display notification for file changes
    function notifyFileChange(type, file) {
        // Create a notification element
        const notification = document.createElement('div');
        notification.classList.add('notification', 'fade-in');
        
        // Set notification content based on change type
        let message = '';
        switch(type) {
            case 'create':
                message = `Archivo creado: ${file.path}`;
                notification.classList.add('notification-success');
                break;
            case 'update':
                message = `Archivo actualizado: ${file.path}`;
                notification.classList.add('notification-info');
                break;
            case 'delete':
                message = `Archivo eliminado: ${file.path}`;
                notification.classList.add('notification-warning');
                break;
            default:
                message = `Cambio en archivo: ${file.path}`;
                notification.classList.add('notification-info');
        }
        
        notification.textContent = message;
        
        // Add notification to the document
        const notificationContainer = document.getElementById('notification-container');
        if (!notificationContainer) {
            // Create notification container if it doesn't exist
            const container = document.createElement('div');
            container.id = 'notification-container';
            container.style.position = 'fixed';
            container.style.top = '20px';
            container.style.right = '20px';
            container.style.zIndex = '1000';
            document.body.appendChild(container);
            container.appendChild(notification);
        } else {
            notificationContainer.appendChild(notification);
        }
        
        // Remove notification after delay
        setTimeout(() => {
            notification.classList.add('fade-out');
            setTimeout(() => {
                notification.remove();
            }, 500);
        }, 3000);
    }
});