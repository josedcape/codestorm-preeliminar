
/**
 * Codestorm Mobile Responsive Enhancement
 * Mejora la experiencia en dispositivos móviles
 */

document.addEventListener('DOMContentLoaded', function() {
    // Ajustar altura de contenedores de chat para móviles
    function adjustChatContainerHeight() {
        const chatContainers = document.querySelectorAll('.chat-container, .chat-container-futuristic');
        const windowHeight = window.innerHeight;
        const isMobile = window.innerWidth < 768;
        
        chatContainers.forEach(container => {
            if (isMobile) {
                // En móviles, usar un cálculo más apropiado para la altura
                const navbarHeight = document.querySelector('.navbar').offsetHeight || 56;
                const footerHeight = document.querySelector('footer') ? document.querySelector('footer').offsetHeight : 40;
                const containerTop = container.getBoundingClientRect().top;
                const availableHeight = windowHeight - containerTop - footerHeight - 20; // 20px de margen
                
                container.style.height = `${availableHeight}px`;
            } else {
                // En desktop, usar los valores por defecto de CSS
                container.style.height = '';
            }
        });
    }
    
    // Manejar el despliegue del menú en móviles
    const navbarToggler = document.querySelector('.navbar-toggler');
    if (navbarToggler) {
        navbarToggler.addEventListener('click', function() {
            // Cerrar otros elementos expandibles cuando se abre el menú
            const mobileSidebar = document.getElementById('mobileSidebar');
            if (mobileSidebar && mobileSidebar.classList.contains('show')) {
                const bsCollapse = new bootstrap.Collapse(mobileSidebar);
                bsCollapse.hide();
            }
        });
    }
    
    // Mejorar interacción con la barra lateral
    const sidebarToggleBtn = document.querySelector('[data-bs-target="#mobileSidebar"]');
    if (sidebarToggleBtn) {
        sidebarToggleBtn.addEventListener('click', function() {
            setTimeout(adjustChatContainerHeight, 350); // Ajustar después de la animación
        });
    }
    
    // Detectar cambios de orientación
    window.addEventListener('resize', function() {
        adjustChatContainerHeight();
    });
    
    // Asegurar que el enfoque funcione bien en dispositivos táctiles
    const touchInputs = document.querySelectorAll('textarea, input:not([type="file"]), .chat-input, .chat-input-futuristic');
    touchInputs.forEach(input => {
        input.addEventListener('focus', function() {
            // Permitir tiempo para que el teclado virtual aparezca
            setTimeout(adjustChatContainerHeight, 300);
        });
        
        input.addEventListener('blur', function() {
            // Permitir tiempo para que el teclado virtual desaparezca
            setTimeout(adjustChatContainerHeight, 300);
        });
    });
    
    // Inicializar ajustes
    adjustChatContainerHeight();
    
    // Detectar cambios de orientación en dispositivos móviles
    window.addEventListener('orientationchange', function() {
        setTimeout(adjustChatContainerHeight, 200);
    });
});
