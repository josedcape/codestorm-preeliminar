// CODESTORM - Sistema de chat con agentes especializados y funcionalidades avanzadas

// Función principal para inicializar el chat
function initializeChat() {
    console.log("Codestorm Assistant inicializado");
    
    // Cargar los agentes en el selector
    loadAgentSelector();
    
    // Configurar selectores de agentes y modelos
    setupSelectors();
    
    // Configurar funcionamiento del chat
    setupChatFunctionality();
    
    // Inicializar detección de comandos especiales
    initCreationCommandDetection();
}

// Configurar los selectores de agentes y modelos
function setupSelectors() {
    const modelSelect = document.getElementById('model-select');
    const agentSelector = document.getElementById('agent-selector');
    
    // Evento para cambiar de modelo
    if (modelSelect) {
        modelSelect.addEventListener('change', function() {
            console.log("Modelo cambiado a: " + this.value);
            localStorage.setItem('codestorm_selected_model', this.value);
        });
        
        // Cargar modelo guardado si existe
        const savedModel = localStorage.getItem('codestorm_selected_model');
        if (savedModel && modelSelect.querySelector(`option[value="${savedModel}"]`)) {
            modelSelect.value = savedModel;
        }
    }
    
    // Evento para cambiar de agente
    if (agentSelector) {
        agentSelector.addEventListener('change', function() {
            const selectedAgentId = this.value;
            setActiveAgent(selectedAgentId);
        });
    }
}

// Configurar la funcionalidad principal del chat
function setupChatFunctionality() {
    const chatMessages = document.getElementById('chat-messages');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const fileInput = document.getElementById('file-input');
    const voiceButton = document.getElementById('voice-button');
    
    // Inicializar estado de la aplicación
    window.app = window.app || {};
    
    // Evento para enviar mensaje con el botón
    if (sendButton) {
        sendButton.addEventListener('click', function() {
            const message = chatInput.value.trim();
            if (message) {
                sendMessage(message);
                chatInput.value = '';
                chatInput.style.height = '50px';
                chatInput.focus();
            }
        });
    }
    
    // Evento para enviar mensaje con Enter (pero no con Shift+Enter)
    if (chatInput) {
        chatInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendButton.click();
            }
        });
    }
    
    // Gestionar archivos cargados
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            handleFileUpload(this.files);
        });
    }
    
    // Configurar reconocimiento de voz si está disponible
    setupVoiceRecognition();
}

// Configurar reconocimiento de voz
function setupVoiceRecognition() {
    const voiceButton = document.getElementById('voice-button');
    const chatInput = document.getElementById('chat-input');
    
    if (voiceButton && 'webkitSpeechRecognition' in window) {
        let recognition = new webkitSpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.lang = 'es-ES';
        
        let isRecording = false;
        
        voiceButton.addEventListener('click', function() {
            if (isRecording) {
                recognition.stop();
                voiceButton.style.backgroundColor = '';
                voiceButton.innerHTML = '<i class="bi bi-mic"></i>';
                isRecording = false;
            } else {
                recognition.start();
                voiceButton.style.backgroundColor = 'rgba(255, 0, 0, 0.2)';
                voiceButton.innerHTML = '<i class="bi bi-mic-fill"></i>';
                isRecording = true;
                chatInput.focus();
            }
        });
        
        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            chatInput.value += transcript;
            chatInput.dispatchEvent(new Event('input'));
        };
        
        recognition.onend = function() {
            voiceButton.style.backgroundColor = '';
            voiceButton.innerHTML = '<i class="bi bi-mic"></i>';
            isRecording = false;
        };
    } else if (voiceButton) {
        voiceButton.addEventListener('click', function() {
            alert('El reconocimiento de voz no está soportado en este navegador.');
        });
    }
}

// Manejar archivos subidos
function handleFileUpload(files) {
    if (!files || files.length === 0) return;
    
    const chatInput = document.getElementById('chat-input');
    let fileInfo = '';
    
    if (files.length === 1) {
        const file = files[0];
        fileInfo = `[Archivo: ${file.name} (${formatFileSize(file.size)})]`;
    } else {
        fileInfo = `[${files.length} archivos seleccionados: `;
        for (let i = 0; i < Math.min(files.length, 3); i++) {
            fileInfo += `${files[i].name}${i < Math.min(files.length, 3) - 1 ? ', ' : ''}`;
        }
        if (files.length > 3) {
            fileInfo += ` y ${files.length - 3} más`;
        }
        fileInfo += ']';
    }
    
    if (chatInput.value) {
        chatInput.value += '\n' + fileInfo;
    } else {
        chatInput.value = fileInfo;
    }
    
    // Ajustar altura
    chatInput.dispatchEvent(new Event('input'));
    chatInput.focus();
    
    // Almacenar archivos para enviarlos después
    window.app.selectedFiles = files;
}

// Formato legible para tamaño de archivos
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Cargar los agentes en el selector
function loadAgentSelector() {
    const agentSelector = document.getElementById('agent-selector');
    const mobileAgentSelector = document.getElementById('mobile-agent-selector');
    
    if (!agentSelector) return;
    
    // Verificar que SPECIALIZED_AGENTS está disponible
    if (typeof window.SPECIALIZED_AGENTS === 'undefined') {
        console.error("Error: SPECIALIZED_AGENTS no está definido");
        // Usar agentes predefinidos básicos si no están disponibles
        window.SPECIALIZED_AGENTS = {
            developer: {
                id: 'developer',
                name: 'Agente de Desarrollo',
                icon: 'bi-code-slash',
                description: 'Experto en optimización y edición de código en tiempo real',
                capabilities: ['Corrección de código', 'Optimización', 'Desarrollo']
            },
            architect: {
                id: 'architect',
                name: 'Agente de Arquitectura',
                icon: 'bi-diagram-3',
                description: 'Diseñador de arquitecturas escalables',
                capabilities: ['Diseño de sistemas', 'Planificación', 'Estructura']
            }
        };
    }
    
    // Cargar agente activo (por defecto developer)
    const savedAgentId = localStorage.getItem('codestorm_selected_agent') || 'developer';
    setActiveAgent(savedAgentId);
}

// Establecer el agente activo
function setActiveAgent(agentId) {
    // Asegurarse de que SPECIALIZED_AGENTS está definido
    if (typeof window.SPECIALIZED_AGENTS === 'undefined') {
        console.error("Error: SPECIALIZED_AGENTS no está definido");
        return;
    }
    
    // Obtener el agente seleccionado o usar el agente desarrollador por defecto
    window.app = window.app || {};
    window.app.activeAgent = window.SPECIALIZED_AGENTS[agentId] || window.SPECIALIZED_AGENTS.developer;
    
    // Guardar en localStorage
    localStorage.setItem('codestorm_selected_agent', agentId);
    
    // Actualizar el valor de los selectores (desktop y móvil)
    const agentSelector = document.getElementById('agent-selector');
    const mobileAgentSelector = document.getElementById('mobile-agent-selector');
    
    if (agentSelector) {
        agentSelector.value = agentId;
    }
    
    if (mobileAgentSelector) {
        mobileAgentSelector.value = agentId;
    }
    
    // Actualizar la información mostrada
    updateAgentInfo(window.app.activeAgent);
    
    // Añadir mensaje informativo al chat
    addSystemMessage(`Has cambiado al <strong>${window.app.activeAgent.name}</strong>. Este agente se especializa en: ${window.app.activeAgent.description}.`);
}

// Actualizar la información del agente en la UI
function updateAgentInfo(agent) {
    const agentIcon = document.getElementById('agent-icon');
    const agentName = document.getElementById('agent-name');
    const agentDescription = document.getElementById('agent-description');
    
    if (agentIcon) {
        agentIcon.className = `bi ${agent.icon}`;
    }
    
    if (agentName) {
        agentName.textContent = agent.name;
    }
    
    if (agentDescription) {
        agentDescription.textContent = agent.description;
    }
}

// Inicializar detección de comandos de creación
function initCreationCommandDetection() {
    // Patrones para detectar comandos de creación (mejorados)
    window.app.creationPatterns = {
        page: /crea(r)?\s+(una)?\s+p[áa]gina|genera(r)?\s+(una)?\s+p[áa]gina|p[áa]gina\s+de\s+ventas/i,
        component: /crea(r)?\s+(un)?\s+componente|genera(r)?\s+(un)?\s+componente/i,
        form: /crea(r)?\s+(un)?\s+formulario|genera(r)?\s+(un)?\s+formulario/i
    };
    
    // Almacenar información de conversación contextual
    window.app.conversationState = {
        hasColorPreference: false,
        colorPreference: '',
        hasStyleInfo: false,
        styleInfo: '',
        hasContentInfo: false,
        contentInfo: '',
        creationMode: false,
        creationStep: 0,
        lastInstructionType: '',
        pendingActions: [],
        creationInProgress: false,
        messageHistory: []
    };
}

// Verificar si el mensaje es un comando de creación
function handleCreationCommand(message) {
    // Si no hay patrones definidos, no es un comando de creación
    if (!window.app || !window.app.creationPatterns) return false;
    
    const lowerMsg = message.toLowerCase();
    let isCreationCommand = false;
    
    // Comprobar cada patrón
    for (const type in window.app.creationPatterns) {
        if (window.app.creationPatterns[type].test(lowerMsg)) {
            window.app.conversationState.creationMode = true;
            window.app.conversationState.lastInstructionType = type;
            isCreationCommand = true;
            break;
        }
    }
    
    // Si es un comando de creación pero no estamos en modo avanzado, solo devolver false
    // para que el backend lo maneje normalmente
    return false;
}

// Enviar mensaje al backend
function sendMessage(message) {
    // Verificar si es un comando de creación
    if (handleCreationCommand(message)) {
        return; // Si se manejó como comando de creación, no enviamos al backend
    }
    
    // Añadir mensaje del usuario al chat
    addUserMessage(message);
    
    // Verificar si es un comando para modificar archivos o ejecutar comandos en lenguaje natural
    if (window.naturalCommandProcessor) {
        const parsedRequest = window.naturalCommandProcessor.processRequest(message);
        if (parsedRequest.success) {
            // Es un comando para manipular archivos o ejecutar comandos
            // Mostrar indicador de carga
            addLoadingMessage();
            
            // Procesar la solicitud mediante el API de lenguaje natural en el backend
            fetch('/api/natural_language', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text: message
                }),
            })
            .then(response => response.json())
            .then(data => {
                // Remover indicador de carga
                removeLoadingMessage();
                
                // Obtener el agente activo
                const activeAgent = window.app.activeAgent || window.SPECIALIZED_AGENTS.developer;
                
                if (data.success) {
                    // La acción fue exitosa, mostrar el resultado
                    let resultMessage = data.message || 'Acción completada correctamente';
                    
                    // Si hay contenido de archivo o salida de comando, agregarla
                    if (data.content) {
                        resultMessage += '\n\n```' + (data.file_type || '') + '\n' + data.content + '\n```';
                    }
                    
                    if (data.stdout) {
                        resultMessage += '\n\n```bash\n# Salida del comando:\n' + data.stdout + '\n```';
                    }
                    
                    if (data.stderr && data.stderr.trim()) {
                        resultMessage += '\n\n```bash\n# Errores:\n' + data.stderr + '\n```';
                    }
                    
                    // Agregar respuesta del agente
                    addAgentMessage(resultMessage, activeAgent);
                } else {
                    // Hubo un error en la acción
                    addAgentMessage('No pude completar esa acción: ' + data.message, activeAgent);
                }
            })
            .catch(error => {
                console.error('Error al procesar lenguaje natural:', error);
                removeLoadingMessage();
                addSystemMessage('Error de conexión. Por favor, inténtalo de nuevo.');
            });
            
            return; // Terminamos aquí porque ya procesamos el comando
        }
    }
    
    // Obtener el agente activo
    const activeAgent = window.app.activeAgent || window.SPECIALIZED_AGENTS.developer;
    const agentId = activeAgent.id || 'developer';
    
    // Mostrar indicador de carga con estilo futurista
    addLoadingMessage();
    
    // Determinar el modelo a usar
    const modelSelect = document.getElementById('model-select');
    const selectedModel = modelSelect ? modelSelect.value : 'openai';
    
    // Obtener el contexto de la conversación reciente (últimos 5 mensajes)
    let conversationContext = [];
    const chatMessages = document.querySelectorAll('.chat-message');
    let contextCount = 0;
    
    // Reunir los últimos mensajes como contexto, hasta un máximo de 5
    for (let i = chatMessages.length - 2; i >= 0 && contextCount < 5; i--) { // -2 para ignorar el mensaje actual
        const msg = chatMessages[i];
        const role = msg.classList.contains('user-message') ? 'user' : 
                     msg.classList.contains('system-message') ? 'system' : 'assistant';
        const content = msg.querySelector('.message-content').textContent;
        
        // Añadir al inicio para mantener el orden cronológico
        conversationContext.unshift({
            role: role,
            content: content
        });
        
        contextCount++;
    }
    
    console.log("Enviando mensaje al backend:", {
        message: message,
        agent_id: agentId,
        context: conversationContext,
        model: selectedModel
    });
    
    // Guardar historial de mensajes
    window.app.conversationState.messageHistory.push({
        role: 'user',
        content: message,
        timestamp: new Date().toISOString()
    });
    
    // Enviar al backend
    fetch('/api/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            message: message,
            agent_id: agentId,
            context: conversationContext,
            model: selectedModel,
            conversation_state: window.app.conversationState
        }),
    })
    .then(response => response.json())
    .then(data => {
        // Remover indicador de carga
        removeLoadingMessage();
        
        if (data.error) {
            addSystemMessage(`Error: ${data.error}`);
            return;
        }
        
        // Guardar respuesta en el historial
        window.app.conversationState.messageHistory.push({
            role: 'assistant',
            content: data.response,
            timestamp: new Date().toISOString()
        });
        
        // Mostrar la respuesta del agente
        addAgentMessage(data.response, activeAgent);
    })
    .catch(error => {
        console.error('Error al enviar mensaje:', error);
        removeLoadingMessage();
        addSystemMessage('Error de conexión. Por favor, inténtalo de nuevo.');
    });
}

// Añadir mensaje del usuario al chat
function addUserMessage(message) {
    const chatMessages = document.getElementById('chat-messages');
    if (!chatMessages) return;
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'chat-message user-message';
    
    const currentTime = getCurrentTime();
    
    const headerDiv = document.createElement('div');
    headerDiv.className = 'message-header';
    headerDiv.innerHTML = `
        <span class="message-sender">Tú</span>
        <span class="message-time">${currentTime}</span>
    `;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = formatMarkdown(escapeHtml(message));
    
    messageDiv.appendChild(headerDiv);
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    
    // Ajustar scroll
    scrollToBottom(chatMessages);
}

// Añadir mensaje del agente al chat
function addAgentMessage(message, agent) {
    const chatMessages = document.getElementById('chat-messages');
    if (!chatMessages) return;
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'chat-message agent-message';
    
    const currentTime = getCurrentTime();
    
    const headerDiv = document.createElement('div');
    headerDiv.className = 'message-header';
    headerDiv.innerHTML = `
        <span class="message-sender">${agent.name}</span>
        <span class="message-time">${currentTime}</span>
    `;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    // Formatear el contenido con markdown y resaltado de código
    contentDiv.innerHTML = formatMarkdown(message);
    
    messageDiv.appendChild(headerDiv);
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    
    // Resaltar bloques de código
    messageDiv.querySelectorAll('pre code').forEach((block) => {
        hljs.highlightElement(block);
    });
    
    // Ajustar scroll
    scrollToBottom(chatMessages);
    
    // Añadir botones de copiar código
    addCopyCodeButtons(messageDiv);
}

// Añadir botones para copiar código
function addCopyCodeButtons(messageDiv) {
    messageDiv.querySelectorAll('pre').forEach((preBlock) => {
        // Verificar si ya tiene un encabezado
        let headerExists = preBlock.previousElementSibling && preBlock.previousElementSibling.classList.contains('code-header');
        
        if (!headerExists) {
            // Crear el encabezado para el código
            const codeHeader = document.createElement('div');
            codeHeader.className = 'code-header';
            
            // Determinar el lenguaje
            let language = 'código';
            const codeBlock = preBlock.querySelector('code');
            if (codeBlock && codeBlock.className) {
                const langMatch = codeBlock.className.match(/language-(\w+)/);
                if (langMatch) {
                    language = langMatch[1];
                }
            }
            
            codeHeader.innerHTML = `
                <div class="code-language">${language}</div>
                <div class="code-buttons">
                    <button class="code-button copy-code-button">
                        <i class="bi bi-clipboard"></i> Copiar
                    </button>
                </div>
            `;
            
            // Insertar el encabezado antes del bloque pre
            preBlock.parentNode.insertBefore(codeHeader, preBlock);
            
            // Añadir evento de clic para copiar el código
            const copyButton = codeHeader.querySelector('.copy-code-button');
            copyButton.addEventListener('click', function() {
                const code = preBlock.textContent;
                navigator.clipboard.writeText(code).then(() => {
                    copyButton.innerHTML = '<i class="bi bi-check2"></i> Copiado';
                    setTimeout(() => {
                        copyButton.innerHTML = '<i class="bi bi-clipboard"></i> Copiar';
                    }, 2000);
                });
            });
        }
    });
}

// Añadir mensaje del sistema al chat
function addSystemMessage(message) {
    const chatMessages = document.getElementById('chat-messages');
    if (!chatMessages) return;
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'chat-message system-message';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = message;
    
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    
    // Ajustar scroll
    scrollToBottom(chatMessages);
}

// Añadir indicador de carga al chat
function addLoadingMessage() {
    const chatMessages = document.getElementById('chat-messages');
    if (!chatMessages) return;
    
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'chat-message agent-message loading-message';
    loadingDiv.innerHTML = `
        <div class="message-content loading-animation">
            <div class="loading-dot"></div>
            <div class="loading-dot"></div>
            <div class="loading-dot"></div>
        </div>
    `;
    
    chatMessages.appendChild(loadingDiv);
    
    // Ajustar scroll
    scrollToBottom(chatMessages);
}

// Eliminar indicador de carga del chat
function removeLoadingMessage() {
    const loadingMessage = document.querySelector('.loading-message');
    if (loadingMessage) {
        loadingMessage.remove();
    }
}

// Formatear markdown a HTML con soporte para código
function formatMarkdown(text) {
    if (!text) return '';
    
    // Reemplazar enlaces
    text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" class="chat-link">$1</a>');
    
    // Reemplazar bloques de código con language hints
    text = text.replace(/```(\w+)?\n([\s\S]*?)```/g, function(match, language, code) {
        const lang = language || '';
        return `<pre><code class="language-${lang}">${escapeHtml(code.trim())}</code></pre>`;
    });
    
    // Reemplazar código inline
    text = text.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');
    
    // Reemplazar negrita
    text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    
    // Reemplazar cursiva
    text = text.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    
    // Reemplazar listas
    if (text.includes('\n- ')) {
        // Capturar todas las listas juntas
        text = text.replace(/(\n- [^\n]+)+/g, function(match) {
            // Procesar cada elemento de la lista
            return '<ul>' + match.split('\n- ').filter(Boolean).map(item => `<li>${item}</li>`).join('') + '</ul>';
        });
    }
    
    // Reemplazar encabezados
    text = text.replace(/\n#{1,6} (.*)/g, function(match, title) {
        const level = match.trim().indexOf(' ');
        return `<h${level}>${title}</h${level}>`;
    });
    
    // Reemplazar párrafos
    text = text.replace(/\n\n([^#\n-].*)/g, '<p>$1</p>');
    
    // Reemplazar saltos de línea
    text = text.replace(/\n/g, '<br>');
    
    return text;
}

// Escapar HTML para prevenir inyección
function escapeHtml(text) {
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// Obtener hora actual formateada
function getCurrentTime() {
    const now = new Date();
    let hours = now.getHours();
    let minutes = now.getMinutes();
    
    // Asegurar formato de dos dígitos
    hours = hours < 10 ? '0' + hours : hours;
    minutes = minutes < 10 ? '0' + minutes : minutes;
    
    return `${hours}:${minutes}`;
}

// Desplazar al final del contenedor
function scrollToBottom(container) {
    if (container) {
        setTimeout(() => {
            container.scrollTop = container.scrollHeight;
        }, 100);
    }
}