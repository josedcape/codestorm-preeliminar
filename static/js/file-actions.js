/**
 * File Actions - Gestión de archivos optimizada
 * Incluye operaciones CRUD y caché para mejor rendimiento
 */

(function() {
    // Caché de archivos para mejorar rendimiento entre navegaciones
    const fileCache = {
        directories: {},
        settings: {
            enabled: true,
            ttl: 300000 // Time to live: 5 minutos en milisegundos
        },
        set: function(path, data) {
            if (!this.settings.enabled) return;
            
            this.directories[path] = {
                data: data,
                timestamp: Date.now()
            };
            
            // Guardar en sessionStorage para persistencia entre recargas
            try {
                sessionStorage.setItem('fileCache', JSON.stringify(this.directories));
            } catch (e) {
                console.warn('No se pudo guardar la caché en sessionStorage:', e);
            }
        },
        get: function(path) {
            if (!this.settings.enabled) return null;
            
            const cached = this.directories[path];
            if (!cached) return null;
            
            // Verificar si la caché expiró
            if (Date.now() - cached.timestamp > this.settings.ttl) {
                delete this.directories[path];
                return null;
            }
            
            return cached.data;
        },
        clear: function() {
            this.directories = {};
            try {
                sessionStorage.removeItem('fileCache');
            } catch (e) {
                console.warn('No se pudo limpiar la caché en sessionStorage:', e);
            }
        },
        init: function() {
            // Cargar caché desde sessionStorage
            try {
                const storedCache = sessionStorage.getItem('fileCache');
                if (storedCache) {
                    this.directories = JSON.parse(storedCache);
                }
            } catch (e) {
                console.warn('Error al cargar caché desde sessionStorage:', e);
            }
        }
    };
    
    // Inicializar caché
    fileCache.init();
    
    // Módulo principal de acciones de archivos
    const fileActions = {
        // Crear un nuevo archivo
        createNewFile: function() {
            // Obtener la ruta actual
            const currentDirectory = document.getElementById('directory-path').textContent || '/';
            
            // Preguntar por el nombre del archivo
            const fileName = prompt('Ingrese el nombre del nuevo archivo:');
            if (!fileName) return; // Cancelado
            
            // Construir ruta completa
            const filePath = currentDirectory === '/' ? fileName : `${currentDirectory}/${fileName}`;
            
            // Validaciones básicas
            if (fileName.trim() === '') {
                this.showNotification('El nombre del archivo no puede estar vacío', 'danger');
                return;
            }
            
            // Crear archivo en el servidor
            fetch('/api/create_file', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    file_path: filePath,
                    content: '',
                    is_directory: false
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
                    this.showNotification(data.error, 'danger');
                    return;
                }
                
                this.showNotification('Archivo creado exitosamente', 'success');
                
                // Invalidar caché para esta ruta
                fileCache.clear();
                
                // Redirigir al editor
                window.location.href = `/edit/${filePath}`;
            })
            .catch(error => {
                console.error('Error al crear archivo:', error);
                this.showNotification('Error al crear archivo: ' + error.message, 'danger');
            });
        },
        
        // Crear una nueva carpeta
        createNewFolder: function() {
            // Obtener la ruta actual
            const currentDirectory = document.getElementById('directory-path').textContent || '/';
            
            // Preguntar por el nombre de la carpeta
            const folderName = prompt('Ingrese el nombre de la nueva carpeta:');
            if (!folderName) return; // Cancelado
            
            // Validaciones básicas
            if (folderName.trim() === '') {
                this.showNotification('El nombre de la carpeta no puede estar vacío', 'danger');
                return;
            }
            
            // Construir ruta completa
            const folderPath = currentDirectory === '/' ? folderName : `${currentDirectory}/${folderName}`;
            
            // Crear carpeta en el servidor
            fetch('/api/create_file', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    file_path: folderPath,
                    is_directory: true
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
                    this.showNotification(data.error, 'danger');
                    return;
                }
                
                this.showNotification('Carpeta creada exitosamente', 'success');
                
                // Invalidar caché para esta ruta
                fileCache.clear();
                
                // Recargar el explorador de archivos
                this.refreshFileExplorer();
            })
            .catch(error => {
                console.error('Error al crear carpeta:', error);
                this.showNotification('Error al crear carpeta: ' + error.message, 'danger');
            });
        },
        
        // Eliminar un archivo o carpeta
        deleteFileOrFolder: function(filePath) {
            if (!filePath) return;
            
            // Confirmar eliminación
            if (!confirm('¿Está seguro de que desea eliminar este elemento? Esta acción no se puede deshacer.')) {
                return;
            }
            
            // Eliminar en el servidor
            fetch('/api/delete_file', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ file_path: filePath })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Error del servidor: ${response.status} ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.error) {
                    this.showNotification(data.error, 'danger');
                    return;
                }
                
                this.showNotification(data.message || 'Elemento eliminado exitosamente', 'success');
                
                // Invalidar caché para todas las rutas
                fileCache.clear();
                
                // Recargar el explorador de archivos
                this.refreshFileExplorer();
            })
            .catch(error => {
                console.error('Error al eliminar:', error);
                this.showNotification('Error al eliminar: ' + error.message, 'danger');
            });
        },
        
        // Actualizar el explorador de archivos sin recargar la página
        refreshFileExplorer: function() {
            console.log("Actualizando explorador de archivos...");
            
            // Obtener elementos del DOM
            const fileExplorerContent = document.getElementById('file-explorer-content');
            const directoryPath = document.getElementById('directory-path');
            const currentDirectory = directoryPath.textContent || '/';
            
            // Mostrar indicador de carga
            fileExplorerContent.innerHTML = `
                <div class="p-4 text-center text-muted">
                    <div class="spinner-border" role="status">
                        <span class="visually-hidden">Cargando...</span>
                    </div>
                    <p class="mt-2">Cargando archivos...</p>
                </div>
            `;
            
            // Limpiar caché para esta ruta específica
            try {
                const cachedData = fileCache.get(currentDirectory);
                if (cachedData) {
                    // Si hay caché, actualizar la interfaz inmediatamente
                    this.renderFileList(cachedData.files, cachedData.current_dir);
                    this.updateBreadcrumb(cachedData.current_dir);
                }
            } catch (e) {
                console.warn('Error al leer caché:', e);
            }
            
            // Hacer la solicitud al servidor
            fetch('/api/list_files', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ directory: currentDirectory })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Error del servidor: ${response.status} ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.error) {
                    this.showNotification(data.error, 'warning');
                    return;
                }
                
                // Actualizar la caché
                fileCache.set(currentDirectory, data);
                
                // Actualizar UI
                if (window.renderFileList && typeof window.renderFileList === 'function') {
                    window.renderFileList(data.files, data.current_dir);
                }
                
                if (window.updateBreadcrumb && typeof window.updateBreadcrumb === 'function') {
                    window.updateBreadcrumb(data.current_dir);
                }
                
                // Actualizar el path actual
                directoryPath.textContent = data.current_dir;
            })
            .catch(error => {
                console.error('Error al actualizar archivos:', error);
                this.showNotification('Error al cargar archivos: ' + error.message, 'danger');
                
                fileExplorerContent.innerHTML = `
                    <div class="p-4 text-center text-danger">
                        <i class="bi bi-exclamation-triangle" style="font-size: 2rem;"></i>
                        <p class="mt-2">${error.message}</p>
                        <button class="btn btn-sm btn-outline-primary mt-3" onclick="window.fileActions.refreshFileExplorer()">
                            <i class="bi bi-arrow-repeat"></i> Intentar nuevamente
                        </button>
                    </div>
                `;
            });
        },
        
        // Mostrar notificaciones
        showNotification: function(message, type = 'info') {
            const notificationsContainer = document.getElementById('notifications');
            if (!notificationsContainer) return;
            
            const toast = document.createElement('div');
            toast.className = `toast align-items-center border-0 bg-${type} text-white`;
            toast.setAttribute('role', 'alert');
            toast.setAttribute('aria-live', 'assertive');
            toast.setAttribute('aria-atomic', 'true');
            
            toast.innerHTML = `
                <div class="d-flex">
                    <div class="toast-body">
                        ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Cerrar"></button>
                </div>
            `;
            
            notificationsContainer.appendChild(toast);
            
            // Verificar si bootstrap está disponible
            if (typeof bootstrap !== 'undefined') {
                const bsToast = new bootstrap.Toast(toast, {
                    autohide: true,
                    delay: 5000
                });
                bsToast.show();
            } else {
                // Fallback si bootstrap no está disponible
                setTimeout(() => {
                    toast.classList.add('show');
                }, 100);
                
                // Auto-hide after 5 seconds
                setTimeout(() => {
                    toast.classList.remove('show');
                    setTimeout(() => toast.remove(), 500);
                }, 5000);
            }
            
            // Eliminar después de ocultarse
            toast.addEventListener('hidden.bs.toast', function() {
                toast.remove();
            });
        },
        
        // Funciones auxiliares (se exponen para que las páginas puedan usarlas)
        updateBreadcrumb: function(path) {
            if (window.updateBreadcrumb && typeof window.updateBreadcrumb === 'function') {
                window.updateBreadcrumb(path);
            }
        },
        
        renderFileList: function(files, currentDir) {
            if (window.renderFileList && typeof window.renderFileList === 'function') {
                window.renderFileList(files, currentDir);
            }
        }
    };
    
    // Exponer funciones al ámbito global
    window.fileActions = fileActions;
    
    // Inicializar context menu para elementos del explorador
    document.addEventListener('DOMContentLoaded', function() {
        // Agregar listeners para clicks fuera de menus contextuales
        document.addEventListener('click', function(e) {
            const contextMenus = document.querySelectorAll('.file-context-menu');
            contextMenus.forEach(menu => {
                if (!menu.contains(e.target)) {
                    menu.remove();
                }
            });
        });
    });
})();