/**
 * Controlador para el Constructor de Tareas Autónomo
 * Este script maneja la creación y monitorización de proyectos
 * que se construyen de forma autónoma a partir de una descripción.
 */

class AutonomousProjectBuilder {
    constructor() {
        // Referencias a elementos de la UI
        this.projectDescription = document.getElementById('projectDescription');
        this.startButton = document.getElementById('startBuildButton');
        this.pauseButton = document.getElementById('pauseBuildButton');
        this.resumeButton = document.getElementById('resumeBuildButton');
        this.projectStatus = document.getElementById('projectStatus');
        this.progressBar = document.getElementById('buildProgress');
        this.chatMessages = document.getElementById('chatMessages');
        this.notificationsContainer = document.getElementById('notificationsPanel');
        this.developmentPlan = document.getElementById('developmentPlan');
        this.taskChecklist = document.getElementById('taskChecklist');
        this.togglePlanBtn = document.getElementById('togglePlanBtn');
        this.timeEstimation = document.getElementById('timeEstimation');
        this.estimatedTimeElement = document.getElementById('estimatedTime');
        
        // Referencias a elementos de configuración
        this.modelRadios = document.querySelectorAll('input[name="aiModelRadio"]');
        this.useArchitectAgent = document.getElementById('useArchitectAgent');
        this.useDeveloperAgent = document.getElementById('useDeveloperAgent');
        this.useTestingAgent = document.getElementById('useTestingAgent');
        this.useFixingAgent = document.getElementById('useFixingAgent');
        this.developmentSpeed = document.getElementById('developmentSpeed');
        
        // Estado del constructor
        this.activeProjectId = null;
        this.projectPhase = 'initial';
        this.isBuilding = false;
        this.isPaused = false;
        this.updateInterval = null;
        this.notificationsCount = 0;
        this.lastNotificationId = 0;
        this.errorCount = 0;
        this.projectNotifications = [];
        this.consoleOutput = [];
        this.tasks = [];
        this.currentTaskIndex = -1;
        this.estimatedTime = null;
        this.startTime = null;
        this.currentAgent = 'architect';
        this.selectedModel = 'openai';
        
        // Inicializar eventos
        this.initEvents();
        
        // Crear contenedor de notificaciones si no existe
        this.initNotificationsPanel();
        
        // Comprobar si hay un proyecto en progreso al cargar la página
        this.checkActiveProjects();
    }
    
    initNotificationsPanel() {
        // Si no existe el panel de notificaciones, crearlo
        if (!this.notificationsContainer) {
            const notificationsPanel = document.createElement('div');
            notificationsPanel.id = 'notificationsPanel';
            notificationsPanel.className = 'notifications-panel';
            notificationsPanel.innerHTML = `
                <div class="notifications-header">
                    <h5 class="mb-0">Notificaciones <span class="badge bg-primary" id="notificationsCount">0</span></h5>
                </div>
                <div class="notifications-body" id="notificationsList"></div>
            `;
            
            // Añadir al DOM después del chat
            const chatContainer = document.querySelector('.chat-messages');
            if (chatContainer) {
                chatContainer.parentNode.insertBefore(notificationsPanel, chatContainer.nextSibling);
            } else {
                document.body.appendChild(notificationsPanel);
            }
            
            this.notificationsContainer = notificationsPanel;
        }
    }
    
    initEvents() {
        // Botón para iniciar la construcción
        this.startButton.addEventListener('click', () => this.startProject());
        
        // Botón para pausar la construcción
        this.pauseButton.addEventListener('click', () => this.pauseProject());
        
        // Botón para reanudar la construcción
        this.resumeButton.addEventListener('click', () => this.resumeProject());
        
        // Botón para limpiar notificaciones
        const clearNotificationsBtn = document.getElementById('clearNotificationsBtn');
        if (clearNotificationsBtn) {
            clearNotificationsBtn.addEventListener('click', () => this.clearNotifications());
        }
        
        // Botón para alternar la visualización del plan de desarrollo
        if (this.togglePlanBtn) {
            this.togglePlanBtn.addEventListener('click', () => {
                const taskList = this.taskChecklist.parentElement;
                
                if (taskList.style.display === 'none') {
                    taskList.style.display = 'block';
                    this.togglePlanBtn.querySelector('i').setAttribute('data-feather', 'chevron-up');
                } else {
                    taskList.style.display = 'none';
                    this.togglePlanBtn.querySelector('i').setAttribute('data-feather', 'chevron-down');
                }
                
                feather.replace();
            });
        }
        
        // Selector de modelo principal mediante radios
        if (this.modelRadios) {
            this.modelRadios.forEach(radio => {
                radio.addEventListener('change', (e) => {
                    this.selectedModel = e.target.value;
                    this.showSystemMessage(`Modelo principal cambiado a: ${e.target.value}`);
                    
                    // Actualizar el modelo en el dropdown de la barra de navegación
                    if (document.getElementById('currentModel')) {
                        const modelName = {
                            'openai': 'OpenAI',
                            'anthropic': 'Anthropic',
                            'gemini': 'Gemini'
                        }[e.target.value] || e.target.value;
                        document.getElementById('currentModel').textContent = modelName;
                    }
                    
                    // Eliminar el mensaje después de 2 segundos
                    setTimeout(() => {
                        const systemMessages = document.querySelectorAll('.system-message');
                        systemMessages.forEach(message => {
                            if (message.textContent.includes('Modelo principal cambiado')) {
                                message.remove();
                            }
                        });
                    }, 2000);
                });
            });
        }
        
        // Selector de modo de desarrollo
        if (this.developmentSpeed) {
            this.developmentSpeed.addEventListener('change', (e) => {
                const speedOption = e.target.value;
                let mensaje;
                
                switch (speedOption) {
                    case 'fast':
                        mensaje = 'Modo rápido: El constructor priorizará la velocidad sobre la validación exhaustiva';
                        break;
                    case 'balanced':
                        mensaje = 'Modo equilibrado: Balance entre velocidad y validación';
                        break;
                    case 'thorough':
                        mensaje = 'Modo exhaustivo: Mayor validación y pruebas, pero más lento';
                        break;
                    default:
                        mensaje = `Modo de desarrollo cambiado a: ${speedOption}`;
                }
                
                this.showSystemMessage(mensaje);
                
                // Eliminar el mensaje después de 2 segundos
                setTimeout(() => {
                    const systemMessages = document.querySelectorAll('.system-message');
                    systemMessages.forEach(message => {
                        if (message.textContent.includes('Modo')) {
                            message.remove();
                        }
                    });
                }, 2000);
            });
        }
        
        // Configuración de agentes especializados
        const agentSwitches = [
            this.useArchitectAgent,
            this.useDeveloperAgent,
            this.useTestingAgent,
            this.useFixingAgent
        ];
        
        agentSwitches.forEach(switchElem => {
            if (switchElem) {
                switchElem.addEventListener('change', (e) => {
                    const agentName = e.target.id.replace('use', '').replace('Agent', '');
                    const status = e.target.checked ? 'activado' : 'desactivado';
                    this.showSystemMessage(`Agente ${agentName} ${status}`);
                    
                    // Eliminar el mensaje después de 2 segundos
                    setTimeout(() => {
                        const systemMessages = document.querySelectorAll('.system-message');
                        systemMessages.forEach(message => {
                            if (message.textContent.includes('Agente')) {
                                message.remove();
                            }
                        });
                    }, 2000);
                });
            }
        });
        
        // Selector de modelo (menú desplegable viejo - compatibilidad)
        const modelOptions = document.querySelectorAll('.model-option');
        modelOptions.forEach(option => {
            option.addEventListener('click', (e) => {
                e.preventDefault();
                this.selectedModel = option.getAttribute('data-model');
                
                // Actualizar los radios de modelo principal
                if (this.modelRadios) {
                    this.modelRadios.forEach(radio => {
                        if (radio.value === this.selectedModel) {
                            radio.checked = true;
                        }
                    });
                }
                
                // Actualizar el texto del dropdown
                if (document.getElementById('currentModel')) {
                    document.getElementById('currentModel').textContent = option.textContent;
                }
                
                this.showSystemMessage(`Modelo cambiado a ${option.textContent}`);
                
                // Eliminar el mensaje después de 2 segundos
                setTimeout(() => {
                    const systemMessages = document.querySelectorAll('.system-message');
                    systemMessages.forEach(message => {
                        if (message.textContent.includes('Modelo cambiado')) {
                            message.remove();
                        }
                    });
                }, 2000);
            });
        });
    }
    
    /**
     * Limpia todas las notificaciones.
     */
    clearNotifications() {
        const notificationsList = document.getElementById('notificationsList');
        if (notificationsList) {
            // Eliminar todas las notificaciones con animación
            const notifications = notificationsList.querySelectorAll('.notification');
            notifications.forEach(notification => {
                notification.classList.add('notification-closing');
            });
            
            // Después de la animación, eliminar los elementos
            setTimeout(() => {
                notificationsList.innerHTML = `
                    <div class="p-3 text-center text-muted">
                        No hay notificaciones aún
                    </div>
                `;
                
                // Reiniciar contadores
                this.notificationsCount = 0;
                const countBadge = document.getElementById('notificationsCount');
                if (countBadge) {
                    countBadge.textContent = '0';
                }
            }, 300);
        }
    }
    
    /**
     * Inicia un nuevo proyecto de construcción.
     */
    startProject() {
        const description = this.projectDescription.value.trim();
        
        if (!description) {
            this.showSystemMessage('❌ Por favor, proporciona una descripción para tu proyecto.');
            return;
        }
        
        if (this.isBuilding) {
            this.showSystemMessage('❌ Ya hay un proyecto en construcción. Debes esperar a que termine o crear uno nuevo.');
            return;
        }
        
        // Mostrar indicador de carga
        this.isBuilding = true;
        this.startButton.disabled = true;
        this.pauseButton.disabled = false;
        this.resumeButton.disabled = true;
        this.showSystemMessage('⏳ Iniciando construcción del proyecto...');
        
        // Inicializar o reiniciar la UI
        this.resetUI();
        
        // Obtener modelo seleccionado
        let selectedModel = 'openai';
        this.modelRadios.forEach(radio => {
            if (radio.checked) {
                selectedModel = radio.value;
            }
        });
        
        // Obtener configuración de agentes
        const agents = {
            architect: this.useArchitectAgent ? this.useArchitectAgent.checked : true,
            developer: this.useDeveloperAgent ? this.useDeveloperAgent.checked : true,
            testing: this.useTestingAgent ? this.useTestingAgent.checked : true,
            fixing: this.useFixingAgent ? this.useFixingAgent.checked : true
        };
        
        // Obtener velocidad de desarrollo
        const speed = this.developmentSpeed ? this.developmentSpeed.value : 'balanced';
        
        // Enviar la petición al servidor con la configuración completa
        fetch('/api/constructor/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                description: description,
                model: selectedModel,
                agents: agents,
                development_speed: speed,
                config: {
                    model: selectedModel,
                    agents: agents,
                    development_speed: speed
                }
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Guardar el ID del proyecto activo
                this.activeProjectId = data.project_id;
                
                // Actualizar la UI
                this.projectStatus.textContent = 'Estado: Construcción iniciada';
                this.progressBar.style.width = '5%';
                this.progressBar.textContent = '5%';
                
                // Agregar el mensaje del usuario al chat
                this.addMessage(description, 'user');
                
                // Comenzar a monitorizar el progreso
                this.startProgressMonitoring();
                
                // Mostrar mensaje de éxito
                this.showSystemMessage('✅ La construcción del proyecto ha comenzado. Se irá mostrando el progreso automáticamente.');
            } else {
                // Mostrar error
                this.isBuilding = false;
                this.startButton.disabled = false;
                this.pauseButton.disabled = true;
                this.showSystemMessage(`❌ Error: ${data.error || 'No se pudo iniciar la construcción'}`);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            this.isBuilding = false;
            this.startButton.disabled = false;
            this.pauseButton.disabled = true;
            this.showSystemMessage('❌ Error de conexión. Por favor, intenta de nuevo.');
        });
    }
    
    /**
     * Pausa la construcción del proyecto activo.
     */
    pauseProject() {
        if (!this.activeProjectId || !this.isBuilding) {
            return;
        }
        
        fetch(`/api/constructor/pause/${this.activeProjectId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.isPaused = true;
                this.pauseButton.disabled = true;
                this.resumeButton.disabled = false;
                this.projectStatus.textContent = 'Estado: Pausado';
                this.showSystemMessage('⏸️ Construcción pausada. Puedes reanudarla cuando quieras.');
            } else {
                this.showSystemMessage(`❌ Error: ${data.error || 'No se pudo pausar la construcción'}`);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            this.showSystemMessage('❌ Error de conexión al intentar pausar.');
        });
    }
    
    /**
     * Reanuda la construcción de un proyecto pausado.
     */
    resumeProject() {
        if (!this.activeProjectId || !this.isBuilding || !this.isPaused) {
            return;
        }
        
        fetch(`/api/constructor/resume/${this.activeProjectId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.isPaused = false;
                this.pauseButton.disabled = false;
                this.resumeButton.disabled = true;
                this.projectStatus.textContent = 'Estado: En construcción';
                this.showSystemMessage('▶️ Construcción reanudada. Continuando con el proceso...');
            } else {
                this.showSystemMessage(`❌ Error: ${data.error || 'No se pudo reanudar la construcción'}`);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            this.showSystemMessage('❌ Error de conexión al intentar reanudar.');
        });
    }
    
    /**
     * Comienza la monitorización periódica del progreso del proyecto.
     */
    startProgressMonitoring() {
        // Limpiar cualquier intervalo existente
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        
        // Consultar inmediatamente el estado
        this.fetchProjectStatus();
        
        // Configurar intervalo de actualización (cada 3 segundos)
        this.updateInterval = setInterval(() => {
            this.fetchProjectStatus();
        }, 3000);
    }
    
    /**
     * Consulta el estado actual del proyecto activo.
     */
    fetchProjectStatus() {
        if (!this.activeProjectId) {
            return;
        }
        
        fetch(`/api/constructor/projects/${this.activeProjectId}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const project = data.project;
                    
                    // Actualizar la UI con el progreso
                    this.updateProjectUI(project);
                    
                    // Si el proyecto se ha completado o ha fallado, detener la monitorización
                    if (['completed', 'error'].includes(project.status)) {
                        this.stopProgressMonitoring();
                        this.isBuilding = false;
                        this.startButton.disabled = false;
                        this.pauseButton.disabled = true;
                        this.resumeButton.disabled = true;
                    }
                } else {
                    console.error('Error al obtener estado del proyecto:', data.error);
                }
            })
            .catch(error => {
                console.error('Error de conexión:', error);
            });
    }
    
    /**
     * Actualiza la UI con la información del proyecto.
     */
    updateProjectUI(project) {
        // Actualizar barra de progreso
        this.progressBar.style.width = `${project.progress}%`;
        this.progressBar.textContent = `${project.progress}%`;
        
        // Actualizar estado
        const phases = {
            'initial': 'Iniciando',
            'analysis': 'Analizando requisitos',
            'planning': 'Planificando estructura',
            'implementation': 'Implementando',
            'testing': 'Verificando',
            'refinement': 'Refinando',
            'completed': 'Completado'
        };
        
        const agentNames = {
            'architect': 'Arquitecto',
            'developer': 'Desarrollador',
            'testing': 'QA Tester',
            'fixing': 'Corrector',
            'general': 'General'
        };
        
        const statusText = phases[project.phase] || project.phase;
        
        // Si hay un agente activo, mostrarlo en el estado
        if (project.current_agent && agentNames[project.current_agent]) {
            this.projectStatus.textContent = `Estado: ${statusText} (${project.progress}%) - Agente: ${agentNames[project.current_agent]}`;
            
            // Resaltar visualmente el agente activo en la interfaz
            this.updateActiveAgentVisual(project.current_agent);
        } else {
            this.projectStatus.textContent = `Estado: ${statusText} (${project.progress}%)`;
        }
        
        // Comprobar si hay errores para actualizar el contador
        if (project.error_count && project.error_count !== this.errorCount) {
            this.errorCount = project.error_count;
            // Resaltar el contador de errores
            const errorBadge = document.createElement('span');
            errorBadge.className = 'badge bg-danger ms-2';
            errorBadge.textContent = `${this.errorCount} errores`;
            
            // Añadir al estado si no existe ya
            const existingBadge = this.projectStatus.querySelector('.badge');
            if (existingBadge) {
                existingBadge.textContent = `${this.errorCount} errores`;
            } else if (this.errorCount > 0) {
                this.projectStatus.appendChild(errorBadge);
            }
        }
        
        // Detectar y notificar cambio de agente
        if (project.current_agent && project.current_agent !== this.currentAgent) {
            const prevAgent = this.currentAgent;
            this.currentAgent = project.current_agent;
            
            // Solo notificar si no es la primera vez (prevAgent existe)
            if (prevAgent) {
                // Enviar notificación de cambio de agente
                this.addNotification({
                    title: `Cambio de Agente`,
                    message: `${agentNames[prevAgent] || prevAgent} → ${agentNames[this.currentAgent] || this.currentAgent}: El control ha sido transferido para continuar con la fase actual.`,
                    type: 'info',
                    timestamp: new Date().toISOString()
                });
            }
            
            // Actualizar visualmente qué agente está activo en la configuración
            this.updateActiveAgentVisual(this.currentAgent);
        }
        
        // Actualizar notificaciones si hay nuevas
        if (project.notifications && project.notifications.length > this.projectNotifications.length) {
            const newNotifications = project.notifications.slice(this.projectNotifications.length);
            newNotifications.forEach(notification => {
                this.addNotification(notification);
            });
            this.projectNotifications = [...project.notifications];
        }
        
        // Actualizar consola si hay nueva salida
        if (project.console_output && project.console_output.length > this.consoleOutput.length) {
            const newOutput = project.console_output.slice(this.consoleOutput.length);
            newOutput.forEach(line => {
                // Analizar la línea para detectar errores
                if (line.includes('Error:') || line.includes('Exception:')) {
                    this.addNotification({
                        title: 'Error detectado en consola',
                        message: line,
                        type: 'error',
                        timestamp: new Date().toISOString()
                    });
                }
            });
            this.consoleOutput = [...project.console_output];
        }
        
        // Actualizar el plan de desarrollo y tareas
        if (project.plan && project.plan.tasks) {
            // Si es la primera vez que recibimos un plan, inicializarlo
            if (!this.tasks || this.tasks.length === 0) {
                this.setPlan(project.plan.tasks, project.plan.estimatedTime || 60);
                
                // Notificar al usuario
                this.addNotification({
                    title: 'Plan de desarrollo generado',
                    message: `Se ha generado un plan con ${project.plan.tasks.length} tareas. Tiempo estimado: ${this.formatTimeEstimate(project.plan.estimatedTime || 60)}`,
                    type: 'info',
                    timestamp: new Date().toISOString()
                });
            } else {
                // Si ya tenemos un plan, actualizar el estado de las tareas
                project.plan.tasks.forEach((task, index) => {
                    if (index < this.tasks.length && this.tasks[index].status !== task.status) {
                        this.updateTaskStatus(index, task.status);
                    }
                });
            }
        }
        
        // Actualizar la tarea actual si ha cambiado
        if (project.currentTaskIndex !== undefined && 
            project.currentTaskIndex !== null && 
            project.currentTaskIndex !== this.currentTaskIndex &&
            project.currentTaskIndex < (this.tasks?.length || 0)) {
            this.setCurrentTask(project.currentTaskIndex);
        }
        
        // Esta sección ya está manejada arriba, eliminada para evitar duplicación
        
        // Actualizar mensajes si hay nuevos
        if (project.messages) {
            // Obtener mensajes actuales en la UI
            const currentMessages = document.querySelectorAll('.chat-message');
            const currentCount = currentMessages.length;
            
            // Si hay más mensajes en el servidor que en la UI, añadir los nuevos
            if (project.messages.length > currentCount) {
                const newMessages = project.messages.slice(currentCount);
                newMessages.forEach(msg => {
                    this.addMessage(msg.content, msg.role);
                    
                    // Si es un mensaje del sistema, también añadir como notificación
                    if (msg.role === 'system') {
                        // Extraer título del mensaje (primera línea)
                        const lines = msg.content.split('\n');
                        const title = lines[0].replace(/[*#]/g, '').trim();
                        const message = lines.slice(1).join('\n').trim();
                        
                        this.addNotification({
                            title: title || 'Notificación del sistema',
                            message: message || msg.content,
                            type: msg.content.includes('❌') ? 'error' : 
                                  msg.content.includes('⚠️') ? 'warning' : 
                                  msg.content.includes('✅') ? 'success' : 'info',
                            timestamp: new Date().toISOString()
                        });
                    }
                });
            }
        }
    }
    
    /**
     * Añade una notificación al panel de notificaciones.
     */
    addNotification(notification) {
        // Incrementar contador
        this.lastNotificationId++;
        this.notificationsCount++;
        
        // Actualizar el contador en la UI
        const countBadge = document.getElementById('notificationsCount');
        if (countBadge) {
            countBadge.textContent = this.notificationsCount;
        }
        
        // Crear elemento de notificación
        const notificationElement = document.createElement('div');
        notificationElement.className = `notification notification-${notification.type}`;
        notificationElement.dataset.id = this.lastNotificationId;
        
        // Formatear la fecha
        const timestamp = new Date(notification.timestamp);
        const formattedTime = timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        // Iconos según el tipo
        const icons = {
            'info': 'info',
            'success': 'check-circle',
            'warning': 'alert-triangle',
            'error': 'alert-octagon'
        };
        
        const icon = icons[notification.type] || 'bell';
        
        // Crear contenido HTML
        notificationElement.innerHTML = `
            <div class="notification-header">
                <span class="notification-icon"><i data-feather="${icon}"></i></span>
                <span class="notification-title">${notification.title}</span>
                <span class="notification-time">${formattedTime}</span>
                <button class="notification-close" title="Descartar"><i data-feather="x"></i></button>
            </div>
            <div class="notification-body">
                <p>${notification.message}</p>
            </div>
        `;
        
        // Añadir al contenedor
        const notificationsList = document.getElementById('notificationsList');
        if (notificationsList) {
            notificationsList.appendChild(notificationElement);
            
            // Inicializar iconos
            feather.replace();
            
            // Configurar botón de cierre
            const closeBtn = notificationElement.querySelector('.notification-close');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => {
                    notificationElement.classList.add('notification-closing');
                    setTimeout(() => {
                        notificationElement.remove();
                        this.notificationsCount--;
                        if (countBadge) {
                            countBadge.textContent = this.notificationsCount;
                        }
                    }, 300);
                });
            }
            
            // Hacer scroll al final
            notificationsList.scrollTop = notificationsList.scrollHeight;
        }
        
        // Para notificaciones de error, mostrar también en el chat
        if (notification.type === 'error' && !this.chatMessages.querySelector(`[data-notification-id="${this.lastNotificationId}"]`)) {
            this.showSystemMessage(`❌ ${notification.title}: ${notification.message}`, this.lastNotificationId);
        }
    }
    
    /**
     * Detiene la monitorización periódica.
     */
    stopProgressMonitoring() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }
    
    /**
     * Comprueba si hay algún proyecto activo al cargar la página.
     */
    checkActiveProjects() {
        fetch('/api/constructor/projects')
            .then(response => response.json())
            .then(data => {
                if (data.success && data.projects && data.projects.length > 0) {
                    // Buscar proyectos en estado activo o pausado
                    const activeProjects = data.projects.filter(p => 
                        p.status === 'active' || p.status === 'paused');
                    
                    if (activeProjects.length > 0) {
                        // Tomar el proyecto más reciente
                        const project = activeProjects[0];
                        
                        // Preguntar al usuario si desea continuar con este proyecto
                        if (confirm(`Se ha encontrado un proyecto en construcción: "${project.name}". ¿Deseas continuar su construcción?`)) {
                            // Restaurar el estado
                            this.activeProjectId = project.project_id;
                            this.isBuilding = true;
                            this.isPaused = project.status === 'paused';
                            
                            // Actualizar la UI
                            this.updateProjectUI(project);
                            
                            // Habilitar/deshabilitar botones según el estado
                            this.startButton.disabled = true;
                            this.pauseButton.disabled = this.isPaused;
                            this.resumeButton.disabled = !this.isPaused;
                            
                            // Comenzar monitorización
                            this.startProgressMonitoring();
                            
                            this.showSystemMessage('✅ Proyecto restaurado correctamente. Continuando con la construcción...');
                        }
                    }
                }
            })
            .catch(error => {
                console.error('Error al comprobar proyectos activos:', error);
            });
    }
    
    /**
     * Reinicia la UI para un nuevo proyecto.
     */
    resetUI() {
        // Limpiar mensajes anteriores
        this.chatMessages.innerHTML = '';
        
        // Reiniciar barra de progreso
        this.progressBar.style.width = '0%';
        this.progressBar.textContent = '0%';
        
        // Reiniciar estado
        this.projectStatus.textContent = 'Estado: Iniciando...';
        
        // Limpiar lista de tareas
        if (this.taskChecklist) {
            this.taskChecklist.innerHTML = `
                <li class="list-group-item text-center text-muted py-3">
                    El plan de desarrollo se generará al iniciar la construcción
                </li>
            `;
        }
        
        // Ocultar el panel de plan de desarrollo y el tiempo estimado
        if (this.developmentPlan) {
            this.developmentPlan.classList.add('d-none');
        }
        
        if (this.timeEstimation) {
            this.timeEstimation.classList.add('d-none');
        }
        
        // Reiniciar variables de estado
        this.tasks = [];
        this.currentTaskIndex = -1;
        this.errorCount = 0;
        
        // Quitar los resaltados de agentes activos
        const agentSwitches = document.querySelectorAll('.agent-selection .form-check');
        agentSwitches.forEach(item => {
            item.classList.remove('active-agent');
        });
        this.projectNotifications = [];
        this.consoleOutput = [];
        this.estimatedTime = null;
        this.startTime = null;
    }
    
    /**
     * Establece el plan de desarrollo con las tareas planificadas.
     */
    setPlan(tasks, estimatedTime) {
        this.tasks = tasks;
        this.estimatedTime = estimatedTime;
        
        // Mostrar el panel del plan
        if (this.developmentPlan) {
            this.developmentPlan.classList.remove('d-none');
        }
        
        // Mostrar el tiempo estimado
        if (this.timeEstimation && this.estimatedTimeElement) {
            this.timeEstimation.classList.remove('d-none');
            this.estimatedTimeElement.textContent = this.formatTimeEstimate(estimatedTime);
        }
        
        // Guardar la hora de inicio
        this.startTime = new Date();
        
        // Actualizar la UI con las tareas
        this.updateTaskList();
    }
    
    /**
     * Actualiza la lista de tareas en la UI
     */
    updateTaskList() {
        if (!this.taskChecklist) return;
        
        // Limpiar el contenedor
        this.taskChecklist.innerHTML = '';
        
        // No hay tareas
        if (!this.tasks || this.tasks.length === 0) {
            this.taskChecklist.innerHTML = `
                <li class="list-group-item text-center text-muted py-3">
                    No hay tareas planificadas aún
                </li>
            `;
            return;
        }
        
        // Agregar cada tarea a la lista
        this.tasks.forEach((task, index) => {
            const isCompleted = task.status === 'completed';
            const isCurrent = index === this.currentTaskIndex;
            
            const taskElement = document.createElement('li');
            taskElement.className = `list-group-item task-item ${isCompleted ? 'task-completed' : ''} ${isCurrent ? 'task-current' : ''}`;
            
            // Crear contenido HTML de la tarea
            taskElement.innerHTML = `
                <div class="task-checkbox">
                    <input type="checkbox" class="form-check-input" ${isCompleted ? 'checked' : ''} disabled>
                </div>
                <div class="task-content">
                    <span class="task-title">${task.title}</span>
                    <div class="task-description">${task.description || ''}</div>
                    <div class="task-meta">
                        ${task.time ? `<span class="task-time"><i data-feather="clock"></i> ${this.formatTimeEstimate(task.time)}</span>` : ''}
                        ${task.agent ? `<span class="task-agent">${task.agent}</span>` : ''}
                    </div>
                </div>
            `;
            
            // Añadir a la lista
            this.taskChecklist.appendChild(taskElement);
        });
        
        // Inicializar iconos
        feather.replace();
    }
    
    /**
     * Actualiza el estado de una tarea específica
     */
    updateTaskStatus(taskIndex, newStatus) {
        if (taskIndex >= 0 && taskIndex < this.tasks.length) {
            this.tasks[taskIndex].status = newStatus;
            
            // Si la tarea se completó, actualizar la tarea actual
            if (newStatus === 'completed' && taskIndex === this.currentTaskIndex) {
                this.currentTaskIndex++;
                this.addNotification({
                    title: `Tarea completada: ${this.tasks[taskIndex].title}`,
                    message: `Se ha completado la tarea ${taskIndex + 1} de ${this.tasks.length}`,
                    type: "success",
                    timestamp: new Date().toISOString()
                });
            }
            
            // Actualizar la lista de tareas en la UI
            this.updateTaskList();
        }
    }
    
    /**
     * Establece la tarea actual en ejecución
     */
    setCurrentTask(taskIndex) {
        if (taskIndex >= 0 && taskIndex < this.tasks.length) {
            this.currentTaskIndex = taskIndex;
            
            // Establecer estado a 'in-progress'
            this.tasks[taskIndex].status = 'in-progress';
            
            // Actualizar la lista de tareas en la UI
            this.updateTaskList();
            
            // Notificar el cambio de tarea
            this.addNotification({
                title: `Iniciando tarea: ${this.tasks[taskIndex].title}`,
                message: `Se está trabajando en la tarea ${taskIndex + 1} de ${this.tasks.length}`,
                type: "info",
                timestamp: new Date().toISOString()
            });
            
            // Si hay un cambio de agente, notificarlo
            if (this.tasks[taskIndex].agent && this.tasks[taskIndex].agent !== this.currentAgent) {
                this.currentAgent = this.tasks[taskIndex].agent;
                this.addNotification({
                    title: `Cambio de agente`,
                    message: `El agente "${this.currentAgent}" está trabajando ahora en esta tarea`,
                    type: "info",
                    timestamp: new Date().toISOString()
                });
            }
        }
    }
    
    /**
     * Formatea un tiempo estimado en minutos a un formato legible
     */
    formatTimeEstimate(minutes) {
        if (!minutes) return "--:--";
        
        const hours = Math.floor(minutes / 60);
        const mins = minutes % 60;
        
        if (hours > 0) {
            return `${hours}h ${mins}m`;
        } else {
            return `${mins}m`;
        }
    }
    
    /**
     * Muestra un mensaje de sistema.
     */
    showSystemMessage(message, notificationId = null) {
        const systemMessageElement = document.createElement('div');
        systemMessageElement.className = 'system-message';
        
        // Si viene de una notificación, añadir atributo para evitar duplicados
        if (notificationId) {
            systemMessageElement.dataset.notificationId = notificationId;
        }
        
        // Procesar el mensaje por si contiene Markdown
        if (message.includes('**') || message.includes('#') || message.includes('```')) {
            systemMessageElement.innerHTML = this.processMarkdown(message);
        } else {
            systemMessageElement.textContent = message;
        }
        
        this.chatMessages.appendChild(systemMessageElement);
        this.scrollToBottom();
    }
    
    /**
     * Añade un mensaje al chat.
     */
    addMessage(content, role) {
        const messageElement = document.createElement('div');
        messageElement.className = `chat-message ${role}-message`;
        
        // Configurar avatar e información de remitente
        const senderInfo = (role === 'user') 
            ? 'Tú'
            : 'Constructor Autónomo';
        
        // Crear contenido HTML del mensaje
        messageElement.innerHTML = `
            <div class="message-header">
                <span class="sender-name">${senderInfo}</span>
                <span class="message-time">${this.formatTime(new Date())}</span>
            </div>
            <div class="message-content"></div>
            ${role === 'assistant' ? '<div class="message-actions"><button class="copy-btn" title="Copiar al portapapeles"><i data-feather="copy"></i></button></div>' : ''}
        `;
        
        // Procesar el contenido Markdown para el asistente
        if (role === 'assistant') {
            const processedContent = this.processMarkdown(content);
            messageElement.querySelector('.message-content').innerHTML = processedContent;
        } else {
            messageElement.querySelector('.message-content').textContent = content;
        }
        
        // Añadir el mensaje al contenedor
        this.chatMessages.appendChild(messageElement);
        
        // Inicializar iconos de Feather
        feather.replace();
        
        // Inicializar resaltado de código
        if (role === 'assistant') {
            hljs.highlightAll();
        }
        
        // Configurar botón de copia
        if (role === 'assistant') {
            const copyBtn = messageElement.querySelector('.copy-btn');
            copyBtn.addEventListener('click', () => {
                this.copyToClipboard(content);
                
                // Cambiar el icono temporalmente para indicar éxito
                const icon = copyBtn.querySelector('i');
                icon.setAttribute('data-feather', 'check');
                feather.replace();
                
                // Restaurar después de 2 segundos
                setTimeout(() => {
                    icon.setAttribute('data-feather', 'copy');
                    feather.replace();
                }, 2000);
            });
        }
        
        // Hacer scroll al final de la conversación
        this.scrollToBottom();
    }
    
    /**
     * Procesa contenido Markdown y protege código.
     */
    processMarkdown(content) {
        // Reemplazo para bloques de código para mantener el formato correcto
        content = content.replace(/```(\w+)?\s*\n([\s\S]*?)```/g, function(match, language, code) {
            language = language || 'plaintext';
            return `<pre><code class="hljs language-${language}">${this.escapeHtml(code.trim())}</code></pre>`;
        });
        
        // Procesar el resto con marked
        return marked.parse(content);
    }
    
    /**
     * Copia texto al portapapeles.
     */
    copyToClipboard(text) {
        // Crear un elemento temporal para copiar
        const tempElement = document.createElement('textarea');
        tempElement.value = text;
        tempElement.setAttribute('readonly', '');
        tempElement.style.position = 'absolute';
        tempElement.style.left = '-9999px';
        document.body.appendChild(tempElement);
        
        // Seleccionar y copiar
        tempElement.select();
        document.execCommand('copy');
        
        // Limpiar
        document.body.removeChild(tempElement);
    }
    
    /**
     * Hace scroll al final de la conversación.
     */
    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    /**
     * Formatea la hora.
     */
    formatTime(date) {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    
    /**
     * Actualiza visualmente cuál es el agente activo en la configuración.
     */
    updateActiveAgentVisual(agentId) {
        // Quitar la clase 'active-agent' de todos los agentes
        const agentSwitches = document.querySelectorAll('.agent-selection .form-check');
        agentSwitches.forEach(item => {
            item.classList.remove('active-agent');
            item.classList.remove('agent-transition');
        });
        
        // Añadir la clase 'active-agent' al agente activo
        const agentMap = {
            'architect': 'useArchitectAgent',
            'developer': 'useDeveloperAgent',
            'testing': 'useTestingAgent', 
            'fixing': 'useFixingAgent'
        };
        
        const targetSwitch = document.getElementById(agentMap[agentId]);
        if (targetSwitch) {
            const targetElement = targetSwitch.closest('.form-check');
            
            // Aplicar clase de transición primero para destacar el cambio
            targetElement.classList.add('agent-transition');
            
            // Luego de un breve tiempo, quitar la transición y dejar solo el active
            setTimeout(() => {
                if (targetElement) {
                    targetElement.classList.remove('agent-transition');
                    targetElement.classList.add('active-agent');
                }
            }, 1000);
            
            // Añadir un efecto de desplazamiento suave a la vista del agente activo
            targetElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
        
        // Actualizar dinámicamente el ícono del agente activo en la interfaz
        this.updateAgentStatusIcon(agentId);
    }
    
    /**
     * Actualiza el ícono de estado del agente en la interfaz principal.
     */
    updateAgentStatusIcon(agentId) {
        const agentIconMap = {
            'architect': 'layout',
            'developer': 'code',
            'testing': 'check-circle',
            'fixing': 'tool'
        };
        
        const agentNameMap = {
            'architect': 'Arquitecto',
            'developer': 'Desarrollador',
            'testing': 'QA Tester',
            'fixing': 'Corrector'
        };
        
        const statusIcon = document.getElementById('currentAgentIcon');
        const statusLabel = document.getElementById('currentAgentLabel');
        
        if (statusIcon) {
            // Actualizar el ícono
            statusIcon.innerHTML = '';
            const newIcon = document.createElement('i');
            newIcon.setAttribute('data-feather', agentIconMap[agentId] || 'user');
            statusIcon.appendChild(newIcon);
            
            // Reinicializar Feather Icons
            feather.replace();
            
            // Aplicar animación al ícono
            statusIcon.classList.add('icon-pulse');
            setTimeout(() => {
                statusIcon.classList.remove('icon-pulse');
            }, 1000);
        }
        
        if (statusLabel) {
            statusLabel.textContent = agentNameMap[agentId] || agentId;
            
            // Aplicar animación al texto
            statusLabel.classList.add('text-highlight');
            setTimeout(() => {
                statusLabel.classList.remove('text-highlight');
            }, 1000);
        }
    }
    
    /**
     * Escapa HTML para evitar XSS.
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Inicializar el constructor al cargar la página
document.addEventListener('DOMContentLoaded', function() {
    new AutonomousProjectBuilder();
});