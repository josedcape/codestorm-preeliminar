/**
 * Animaciones para Codestorm Assistant
 * Este archivo contiene las funciones para manejar animaciones y efectos visuales
 */

// Funciones de utilidad para animaciones
const AnimationUtils = {
    /**
     * Muestra un spinner de carga y oculta el elemento original
     * @param {HTMLElement} element - Elemento a reemplazar con el spinner
     * @param {string} size - Tamaño del spinner: 'sm', 'md', 'lg'
     * @param {string} color - Color del spinner (opcional)
     * @return {HTMLElement} - El spinner creado
     */
    showSpinner: function(element, size = 'md', color = null) {
        // Guardar el HTML original
        if (!element.dataset.originalHtml) {
            element.dataset.originalHtml = element.innerHTML;
        }
        
        // Crear spinner
        const spinnerSize = size === 'sm' ? 'spinner-sm' : (size === 'lg' ? 'spinner-lg' : '');
        const spinnerColor = color ? `border-top-color: ${color};` : '';
        
        // Reemplazar el contenido con el spinner
        element.innerHTML = `
            <div class="spinner-container">
                <div class="spinner ${spinnerSize}" style="${spinnerColor}"></div>
            </div>
        `;
        
        return element.querySelector('.spinner');
    },
    
    /**
     * Restaura el contenido original después de mostrar un spinner
     * @param {HTMLElement} element - Elemento que contiene el spinner
     */
    hideSpinner: function(element) {
        if (element.dataset.originalHtml) {
            element.innerHTML = element.dataset.originalHtml;
            delete element.dataset.originalHtml;
        }
    },
    
    /**
     * Muestra un indicador de escritura/carga
     * @param {HTMLElement} container - Contenedor donde mostrar el indicador
     * @param {string} message - Mensaje opcional para mostrar junto al indicador
     * @return {HTMLElement} - El indicador creado
     */
    showTypingIndicator: function(container, message = null) {
        const indicator = document.createElement('div');
        indicator.className = 'typing-indicator slide-in-up';
        indicator.innerHTML = `
            ${message ? `<span class="message">${message}</span>` : ''}
            <span></span>
            <span></span>
            <span></span>
        `;
        
        container.appendChild(indicator);
        return indicator;
    },
    
    /**
     * Elimina un indicador de escritura/carga
     * @param {HTMLElement} indicator - El indicador a eliminar
     */
    hideTypingIndicator: function(indicator) {
        if (indicator && indicator.parentNode) {
            indicator.classList.add('fade-out');
            setTimeout(() => {
                indicator.parentNode.removeChild(indicator);
            }, 300);
        }
    },
    
    /**
     * Crea un efecto de transición para un nuevo elemento
     * @param {HTMLElement} element - Elemento para animar
     * @param {string} animation - Tipo de animación: 'fade-in', 'slide-in-up', etc.
     */
    animateElement: function(element, animation = 'fade-in') {
        element.classList.add(animation);
        
        // Eliminar la clase de animación después de completarse
        element.addEventListener('animationend', function() {
            element.classList.remove(animation);
        }, {once: true});
    },
    
    /**
     * Muestra un indicador de "acción exitosa" en un elemento
     * @param {HTMLElement} element - Elemento para mostrar la animación
     */
    showSuccessAnimation: function(element) {
        element.classList.add('success-pulse');
        
        // Eliminar la clase después de la animación
        setTimeout(() => {
            element.classList.remove('success-pulse');
        }, 1500);
    },
    
    /**
     * Crea un loader de pantalla completa
     * @param {string} message - Mensaje a mostrar
     * @return {HTMLElement} - El loader creado
     */
    showFullscreenLoader: function(message = 'Cargando...') {
        // Crear el elemento del loader
        const loader = document.createElement('div');
        loader.className = 'fullscreen-loader fade-in';
        loader.innerHTML = `
            <div class="spinner spinner-lg"></div>
            <div class="message">${message}</div>
        `;
        
        // Añadir al body
        document.body.appendChild(loader);
        return loader;
    },
    
    /**
     * Elimina el loader de pantalla completa
     * @param {HTMLElement} loader - El loader a eliminar
     */
    hideFullscreenLoader: function(loader) {
        if (loader) {
            loader.classList.add('fade-out');
            setTimeout(() => {
                if (loader.parentNode) {
                    loader.parentNode.removeChild(loader);
                }
            }, 300);
        }
    },
    
    /**
     * Aplica efecto de shimmer a los elementos
     * @param {NodeList|HTMLElement[]} elements - Elementos para aplicar el efecto
     */
    applyShimmerEffect: function(elements) {
        elements.forEach(el => {
            el.classList.add('shimmer-effect');
        });
    },
    
    /**
     * Elimina efecto de shimmer de los elementos
     * @param {NodeList|HTMLElement[]} elements - Elementos para eliminar el efecto
     */
    removeShimmerEffect: function(elements) {
        elements.forEach(el => {
            el.classList.remove('shimmer-effect');
        });
    }
};

// Animaciones específicas para partes de la interfaz
const InterfaceAnimations = {
    /**
     * Inicializa todas las animaciones de la interfaz
     */
    init: function() {
        // Inicializar efectos hover en botones
        document.querySelectorAll('.btn-futuristic').forEach(btn => {
            btn.classList.add('hover-lift');
        });
        
        // Inicializar efectos de foco en elementos interactivos
        document.querySelectorAll('input, textarea, select').forEach(el => {
            el.classList.add('focus-ring');
        });
        
        // Inicializar transiciones en general
        document.querySelectorAll('.card, .alert, .dropdown-menu').forEach(el => {
            el.classList.add('transition-all');
        });
        
        // Animar entrada de elementos principales
        setTimeout(() => {
            const mainContent = document.querySelector('.main-content');
            if (mainContent) {
                AnimationUtils.animateElement(mainContent, 'fade-in');
            }
        }, 100);
    },
    
    /**
     * Animación para envío de mensajes en el chat
     * @param {HTMLElement} messageContainer - Contenedor de mensajes
     * @param {HTMLElement} form - Formulario de envío
     */
    setupChatAnimation: function(messageContainer, form) {
        if (!form || !messageContainer) return;
        
        form.addEventListener('submit', function(e) {
            // Obtener el botón de envío
            const submitButton = form.querySelector('button[type="submit"]');
            if (submitButton) {
                // Mostrar spinner en el botón
                AnimationUtils.showSpinner(submitButton, 'sm');
                
                // Mostrar indicador de escritura en el contenedor de mensajes
                const indicator = AnimationUtils.showTypingIndicator(messageContainer, "El asistente está pensando...");
                
                // Restaurar después de la respuesta (debe ser llamado manualmente después)
                window.restoreChat = function() {
                    AnimationUtils.hideSpinner(submitButton);
                    AnimationUtils.hideTypingIndicator(indicator);
                };
            }
        });
    },
    
    /**
     * Animación para carga de archivos
     * @param {HTMLElement} container - Contenedor de archivos
     */
    setupFileExplorerAnimation: function(container) {
        if (!container) return;
        
        // Interceptar clicks en botones de acción
        container.addEventListener('click', function(e) {
            // Buscar el botón más cercano
            const button = e.target.closest('button');
            if (button && !button.disabled) {
                // Si es un botón de acción, mostrar spinner
                if (button.classList.contains('btn-outline-info') || 
                    button.classList.contains('btn-outline-danger') ||
                    button.classList.contains('btn-futuristic')) {
                    
                    // Guardar el contenido original
                    const originalHtml = button.innerHTML;
                    
                    // Mostrar spinner
                    button.innerHTML = '<div class="spinner spinner-sm"></div>';
                    button.disabled = true;
                    
                    // Restaurar después de un tiempo (debe ser reemplazado por callback real)
                    setTimeout(() => {
                        button.innerHTML = originalHtml;
                        button.disabled = false;
                    }, 800);
                }
            }
        });
    },
    
    /**
     * Animación para carga de repositorios GitHub
     * @param {HTMLElement} button - Botón de clonar
     * @param {HTMLElement} statusContainer - Contenedor del status
     */
    setupGithubCloneAnimation: function(button, statusContainer) {
        if (!button || !statusContainer) return;
        
        // Original handleGithubClone function from your code
        const originalHandleClone = button.onclick;
        
        button.onclick = function(e) {
            // Mostrar animación de loading
            AnimationUtils.showSpinner(button, 'sm');
            button.disabled = true;
            
            // Mostrar animación en el contenedor de status
            statusContainer.innerHTML = '';
            statusContainer.style.display = 'block';
            statusContainer.className = 'alert alert-info fade-in';
            
            const loadingMessage = document.createElement('div');
            loadingMessage.className = 'shimmer-effect';
            loadingMessage.innerHTML = `
                <div class="d-flex align-items-center">
                    <div class="spinner spinner-sm me-2"></div>
                    <span>Clonando repositorio, por favor espera...</span>
                </div>
            `;
            statusContainer.appendChild(loadingMessage);
            
            // Llamar a la función original si existe
            if (typeof originalHandleClone === 'function') {
                originalHandleClone.call(this, e);
            }
        };
    }
};

// Inicializar animaciones cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    InterfaceAnimations.init();
    
    // Detectar la página actual y aplicar animaciones específicas
    const currentPath = window.location.pathname;
    
    // Aplicar animaciones específicas para el chat
    if (currentPath.includes('/chat')) {
        const messageContainer = document.querySelector('.chat-messages-container');
        const chatForm = document.querySelector('#chat-form');
        InterfaceAnimations.setupChatAnimation(messageContainer, chatForm);
    }
    
    // Aplicar animaciones para el explorador de archivos
    if (currentPath.includes('/files')) {
        const filesContainer = document.querySelector('#files-container');
        InterfaceAnimations.setupFileExplorerAnimation(filesContainer);
        
        // Configurar animación para clonar repos
        const cloneRepoBtn = document.querySelector('#clone-repo-btn');
        const cloneStatus = document.querySelector('#clone-status');
        if (cloneRepoBtn && cloneStatus) {
            InterfaceAnimations.setupGithubCloneAnimation(cloneRepoBtn, cloneStatus);
        }
    }
    
    // Aplicar animaciones para el corrector de código
    if (currentPath.includes('/code_corrector')) {
        const submitBtn = document.querySelector('#analyze-code-btn');
        if (submitBtn) {
            submitBtn.addEventListener('click', function() {
                AnimationUtils.showSpinner(this, 'sm');
                this.disabled = true;
                
                // Debe ser restaurado manualmente después
                window.restoreCodeButton = function() {
                    AnimationUtils.hideSpinner(submitBtn);
                    submitBtn.disabled = false;
                };
            });
        }
    }
});