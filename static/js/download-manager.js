/**
 * Gestor de descargas y repositorios
 * Proporciona funcionalidades para descargar archivos/directorios y clonar repositorios
 */
const DownloadManager = (function() {
    // Variables privadas
    let currentPath = '/';
    
    /**
     * Inicializa el gestor de descargas
     */
    function initialize() {
        // Agregar botones a la interfaz de usuario
        addDownloadButtons();
        
        // Configurar el modal para clonar repositorios
        setupCloneRepoModal();
        
        // Configurar eventos
        setupEventListeners();
    }
    
    /**
     * Añade botones de descarga a los elementos del explorador de archivos
     */
    function addDownloadButtons() {
        // Se ejecutará después de cargar el explorador de archivos
        document.addEventListener('filesLoaded', function() {
            // Agregar botones a los elementos de archivo
            addFileDownloadButtons();
            
            // Agregar botones a los directorios
            addDirectoryDownloadButtons();
        });
    }
    
    /**
     * Añade botones de descarga a los elementos de archivo
     */
    function addFileDownloadButtons() {
        const fileItems = document.querySelectorAll('.file-item:not(.directory)');
        
        fileItems.forEach(item => {
            // No modificar el elemento de navegación hacia atrás (..)
            if (item.querySelector('span').textContent === '..') return;
            
            // Verificar si ya tiene un botón de descarga
            if (item.querySelector('.download-btn')) return;
            
            // Crear botón de descarga
            const downloadBtn = document.createElement('button');
            downloadBtn.className = 'btn btn-sm btn-outline-info download-btn ms-2';
            downloadBtn.innerHTML = '<i class="bi bi-download"></i>';
            downloadBtn.title = 'Descargar archivo';
            
            // Agregar evento de descarga
            downloadBtn.addEventListener('click', function(e) {
                e.stopPropagation(); // Evitar navegación al hacer clic
                
                const fileName = item.querySelector('span').textContent;
                const filePath = currentPath === '/' 
                    ? fileName 
                    : `${currentPath}/${fileName}`;
                
                // Iniciar descarga
                window.location.href = `/api/download_file/${filePath}`;
            });
            
            // Agregar botón al elemento
            item.appendChild(downloadBtn);
        });
    }
    
    /**
     * Añade botones de descarga a los directorios
     */
    function addDirectoryDownloadButtons() {
        const dirItems = document.querySelectorAll('.file-item.directory');
        
        dirItems.forEach(item => {
            // No modificar el elemento de navegación hacia atrás (..)
            if (item.querySelector('span').textContent === '..') return;
            
            // Verificar si ya tiene un botón de descarga
            if (item.querySelector('.download-btn')) return;
            
            // Crear botón de descarga ZIP
            const downloadBtn = document.createElement('button');
            downloadBtn.className = 'btn btn-sm btn-outline-success download-btn ms-2';
            downloadBtn.innerHTML = '<i class="bi bi-file-earmark-zip"></i>';
            downloadBtn.title = 'Descargar como ZIP';
            
            // Agregar evento de descarga
            downloadBtn.addEventListener('click', function(e) {
                e.stopPropagation(); // Evitar navegación al hacer clic
                
                const dirName = item.querySelector('span').textContent;
                const dirPath = currentPath === '/' 
                    ? dirName 
                    : `${currentPath}/${dirName}`;
                
                // Iniciar descarga
                window.location.href = `/api/download_directory/${dirPath}`;
            });
            
            // Agregar botón al elemento
            item.appendChild(downloadBtn);
        });
    }
    
    /**
     * Configura el modal para clonar repositorios
     */
    function setupCloneRepoModal() {
        // Crear el modal si no existe
        if (!document.getElementById('cloneRepoModal')) {
            const modalHTML = `
                <div class="modal fade" id="cloneRepoModal" tabindex="-1" aria-labelledby="cloneRepoModalLabel" aria-hidden="true">
                    <div class="modal-dialog">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title" id="cloneRepoModalLabel">Clonar Repositorio Git</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <form id="cloneRepoForm">
                                    <div class="mb-3">
                                        <label for="repoUrl" class="form-label">URL del Repositorio</label>
                                        <input type="text" class="form-control" id="repoUrl" 
                                            placeholder="https://github.com/usuario/repositorio.git" required>
                                        <div class="form-text text-light">
                                            Ingresa la URL del repositorio Git que deseas clonar.
                                        </div>
                                    </div>
                                </form>
                                <div id="cloneStatus" class="alert d-none"></div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                                <button type="button" class="btn btn-success" id="cloneRepoBtn">Clonar</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            // Agregar modal al documento
            const modalContainer = document.createElement('div');
            modalContainer.innerHTML = modalHTML;
            document.body.appendChild(modalContainer);
        }
    }
    
    /**
     * Configura los eventos para el gestor de descargas
     */
    function setupEventListeners() {
        // Eventos para cambio de directorio
        document.addEventListener('directoryChanged', function(e) {
            currentPath = e.detail.path || '/';
            
            // Actualizar botones de descarga
            setTimeout(() => {
                addFileDownloadButtons();
                addDirectoryDownloadButtons();
            }, 300);
        });
        
        // Evento para mostrar modal de clonar repositorio
        document.addEventListener('DOMContentLoaded', function() {
            const cloneRepoBtn = document.getElementById('clone-repo-btn');
            if (cloneRepoBtn) {
                cloneRepoBtn.addEventListener('click', function() {
                    const modal = new bootstrap.Modal(document.getElementById('cloneRepoModal'));
                    modal.show();
                });
            }
            
            // Configurar el botón para clonar repositorio
            const confirmCloneBtn = document.getElementById('cloneRepoBtn');
            if (confirmCloneBtn) {
                confirmCloneBtn.addEventListener('click', cloneRepository);
            }
        });
    }
    
    /**
     * Clona un repositorio Git en el directorio actual
     */
    function cloneRepository() {
        const repoUrl = document.getElementById('repoUrl').value.trim();
        const cloneStatus = document.getElementById('cloneStatus');
        
        if (!repoUrl) {
            showCloneStatus('danger', 'Por favor, ingresa la URL del repositorio.');
            return;
        }
        
        // Mostrar mensaje de carga
        showCloneStatus('info', '<i class="bi bi-arrow-repeat spin"></i> Clonando repositorio, esto puede tardar unos momentos...');
        
        // Deshabilitar botón durante la clonación
        document.getElementById('cloneRepoBtn').disabled = true;
        
        // Enviar solicitud al servidor
        fetch('/api/clone_repository', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ repo_url: repoUrl })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showCloneStatus('danger', 'Error: ' + data.error);
            } else {
                showCloneStatus('success', 'Repositorio clonado correctamente.');
                
                // Cerrar modal después de un breve retraso
                setTimeout(() => {
                    bootstrap.Modal.getInstance(document.getElementById('cloneRepoModal')).hide();
                    
                    // Recargar el directorio actual
                    if (window.fileExplorer && typeof window.fileExplorer.loadDirectory === 'function') {
                        window.fileExplorer.loadDirectory(currentPath);
                    }
                }, 1500);
            }
        })
        .catch(error => {
            showCloneStatus('danger', 'Error al comunicarse con el servidor: ' + error.message);
        })
        .finally(() => {
            // Re-habilitar botón
            document.getElementById('cloneRepoBtn').disabled = false;
        });
    }
    
    /**
     * Muestra un mensaje de estado en el modal de clonación
     */
    function showCloneStatus(type, message) {
        const cloneStatus = document.getElementById('cloneStatus');
        cloneStatus.className = `alert alert-${type}`;
        cloneStatus.innerHTML = message;
        cloneStatus.classList.remove('d-none');
    }
    
    // Interfaz pública
    return {
        initialize,
        addDownloadButtons,
        cloneRepository,
        
        // Para acceso desde consola o depuración
        _getCurrentPath: function() {
            return currentPath;
        }
    };
})();

// Inicializar cuando el documento esté listo
document.addEventListener('DOMContentLoaded', function() {
    // Si estamos en la página de explorador de archivos
    if (document.querySelector('.file-explorer')) {
        DownloadManager.initialize();
        
        // Exponer para uso global
        window.downloadManager = DownloadManager;
    }
});