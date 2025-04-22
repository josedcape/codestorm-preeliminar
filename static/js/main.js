/**
 * Funciones principales de Codestorm Assistant
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Codestorm Assistant inicializado');
    
    // Inicializar tooltips de Bootstrap si existen
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
    
    // Inicializar popovers de Bootstrap si existen
    if (typeof bootstrap !== 'undefined' && bootstrap.Popover) {
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(function (popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });
    }
    
    // Función para mostrar mensajes de notificación
    window.showNotification = function(message, type = 'info') {
        const alertContainer = document.getElementById('alert-container');
        if (!alertContainer) {
            // Crear contenedor si no existe
            const container = document.createElement('div');
            container.id = 'alert-container';
            container.style.position = 'fixed';
            container.style.top = '10px';
            container.style.right = '10px';
            container.style.zIndex = '9999';
            document.body.appendChild(container);
        }
        
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        document.getElementById('alert-container').appendChild(alert);
        
        // Auto-cerrar después de 5 segundos
        setTimeout(() => {
            if (alert) {
                alert.classList.remove('show');
                setTimeout(() => alert.remove(), 300);
            }
        }, 5000);
    };
    
    // Hacer que los campos de formulario con la clase 'autosize' se ajusten automáticamente
    document.querySelectorAll('textarea.autosize').forEach(textarea => {
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = this.scrollHeight + 'px';
        });
        
        // Trigger inicial
        textarea.dispatchEvent(new Event('input'));
    });
    
    // Integración markdown automática para elementos con la clase 'markdown-content'
    if (typeof marked !== 'undefined') {
        document.querySelectorAll('.markdown-content').forEach(element => {
            const markdown = element.textContent || element.innerText;
            element.innerHTML = marked(markdown);
            
            // Resaltar código si prism está disponible
            if (typeof Prism !== 'undefined') {
                element.querySelectorAll('pre code').forEach(block => {
                    Prism.highlightElement(block);
                });
            }
        });
    }
    
    // Función para copiar texto al portapapeles
    window.copyToClipboard = function(text) {
        navigator.clipboard.writeText(text)
            .then(() => {
                showNotification('Copiado al portapapeles', 'success');
            })
            .catch(err => {
                console.error('Error al copiar: ', err);
                showNotification('Error al copiar al portapapeles', 'danger');
            });
    };
});

// Función para formatear fechas
function formatDate(date) {
    if (!(date instanceof Date)) {
        date = new Date(date);
    }
    
    const options = {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    };
    
    return date.toLocaleDateString('es-ES', options);
}

// Función para formatear bytes a unidades legibles
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB'];
    
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}