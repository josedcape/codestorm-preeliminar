/**
 * CODESTORM - Sistema Multi-Agente Interconectado
 * Este módulo permite la coordinación entre múltiples agentes especializados
 * para trabajar juntos en tareas complejas.
 */

// Namespace global para el sistema multi-agente
window.multiAgentSystem = (function() {
    // Registro de agentes disponibles y sus capacidades
    let agents = {};
    
    // Cola de mensajes para comunicación entre agentes
    let messageQueue = [];
    
    // Estado actual de la conversación y contexto
    let conversationContext = {
        history: [],
        currentTask: null,
        activeAgents: []
    };
    
    // Peso de confianza para cada agente (0-100)
    let agentConfidence = {};
    
    // Umbrales de confianza para derivación a otros agentes
    const CONFIDENCE_THRESHOLD = 70;
    
    // Eventos personalizados para comunicación
    const events = {
        MESSAGE_RECEIVED: 'agentMessageReceived',
        AGENT_ACTIVATED: 'agentActivated',
        AGENT_COMPLETED: 'agentTaskCompleted',
        CONTEXT_UPDATED: 'contextUpdated'
    };
    
    // Inicializar el sistema
    function initialize() {
        // Inicializar con los agentes predefinidos en SPECIALIZED_AGENTS
        if (window.SPECIALIZED_AGENTS) {
            for (const agentId in window.SPECIALIZED_AGENTS) {
                registerAgent(
                    agentId,
                    window.SPECIALIZED_AGENTS[agentId].name,
                    window.SPECIALIZED_AGENTS[agentId].description,
                    window.SPECIALIZED_AGENTS[agentId].capabilities || [],
                    window.SPECIALIZED_AGENTS[agentId].icon || 'bi-robot'
                );
            }
        }
        
        // Configurar eventos personalizados
        setupEventListeners();
        
        console.log("Sistema Multi-Agente inicializado:", agents);
    }
    
    // Configurar listeners de eventos
    function setupEventListeners() {
        document.addEventListener(events.MESSAGE_RECEIVED, handleAgentMessage);
        document.addEventListener(events.AGENT_ACTIVATED, handleAgentActivation);
        document.addEventListener(events.AGENT_COMPLETED, handleAgentCompletion);
    }
    
    // Registrar un nuevo agente en el sistema
    function registerAgent(id, name, description, capabilities, icon) {
        agents[id] = {
            id: id,
            name: name,
            description: description,
            capabilities: capabilities,
            icon: icon,
            isActive: false,
            lastResponse: null
        };
        
        // Inicializar confianza
        agentConfidence[id] = 90; // Valor inicial de confianza
        
        return agents[id];
    }
    
    // Analizar mensaje y determinar el agente más adecuado - Versión mejorada con análisis contextual
    function analyzeMessage(message) {
        // Palabras clave asociadas con cada tipo de agente - Ampliadas y categorizadas
        const keywordMapping = {
            developer: {
                // Lenguajes de programación y tecnologías
                languages: [
                    'javascript', 'typescript', 'python', 'java', 'c#', 'c++', 'php', 'ruby',
                    'go', 'rust', 'swift', 'kotlin', 'scala', 'perl', 'bash', 'powershell'
                ],
                // Conceptos de programación
                concepts: [
                    'código', 'programar', 'función', 'clase', 'método', 'bug', 'error',
                    'depurar', 'implementar', 'refactorizar', 'optimizar', 'compilar',
                    'desarrollo', 'loop', 'bucle', 'variable', 'constante', 'array', 'objeto',
                    'try-catch', 'excepción', 'manejo de errores', 'asíncrono', 'síncrono',
                    'promesa', 'callback', 'await', 'async'
                ],
                // Frameworks y bibliotecas
                frameworks: [
                    'api', 'biblioteca', 'framework', 'react', 'angular', 'vue', 'node', 'express', 
                    'flask', 'django', 'spring', 'laravel', 'rails', 'bootstrap', 'jquery',
                    'webpack', 'vite', 'npm', 'yarn', 'pip', 'composer', 'maven', 'gradle',
                    'docker', 'kubernetes', 'redux', 'vuex', 'nextjs', 'nuxtjs'
                ],
                // Acciones de desarrollo
                actions: [
                    'programar', 'codificar', 'implementar', 'desarrollar', 'escribir código',
                    'testear', 'probar', 'depurar', 'corregir', 'fix', 'arreglar', 'resolver',
                    'optimizar', 'mejorar', 'refactorizar', 'limpiar', 'documentar', 'comentar',
                    'mantener', 'modificar', 'actualizar', 'agregar', 'eliminar', 'cambiar',
                    'ejecutar', 'compilar', 'transpilar', 'deployar', 'desplegar'
                ]
            },
            architect: {
                // Conceptos arquitectónicos
                concepts: [
                    'arquitectura', 'sistema', 'diseño', 'patrón', 'estructura', 'componente',
                    'módulo', 'escalabilidad', 'mantenibilidad', 'microservicio', 'monolito',
                    'acoplamiento', 'cohesión', 'mvc', 'mvvm', 'api', 'interfaz', 'backend',
                    'frontend', 'base de datos', 'modelo', 'diagrama', 'uml', 'flujo de datos',
                    'cliente-servidor', 'capas', 'servicios', 'principios solid', 'serverless',
                    'cloud', 'infraestructura', 'almacenamiento', 'procesamiento', 'distribuido'
                ],
                // Tecnologías y plataformas
                technologies: [
                    'aws', 'azure', 'gcp', 'firebase', 'docker', 'kubernetes', 'terraform',
                    'jenkins', 'gitlab', 'github actions', 'travis', 'circleci', 'ansible',
                    'puppet', 'chef', 'redis', 'elasticsearch', 'rabbitmq', 'kafka', 'consul',
                    'etcd', 'prometheus', 'grafana', 'splunk', 'datadog', 'new relic'
                ],
                // Tipos de bases de datos
                databases: [
                    'sql', 'nosql', 'mysql', 'postgresql', 'oracle', 'mongodb', 'cassandra',
                    'dynamodb', 'neo4j', 'redis', 'couchdb', 'firestore', 'bigtable', 'hbase',
                    'inmemory', 'indexado', 'columnar', 'grafos', 'clave-valor', 'documentos'
                ],
                // Acciones de arquitectura
                actions: [
                    'diseñar', 'estructurar', 'planificar', 'modelar', 'diagramar', 'organizar',
                    'definir', 'establecer', 'configurar', 'integrar', 'desacoplar', 'documentar',
                    'revisar', 'auditar', 'validar', 'verificar', 'escalar', 'optimizar', 
                    'automatizar', 'orquestar', 'securizar', 'distribuir', 'centralizar'
                ]
            },
            advanced: {
                // Tecnologías avanzadas
                technologies: [
                    'machine learning', 'ml', 'inteligencia artificial', 'ia', 'deep learning',
                    'blockchain', 'iot', 'internet de las cosas', 'realidad virtual', 'vr',
                    'realidad aumentada', 'ar', 'computer vision', 'visión artificial', 'nlp',
                    'procesamiento de lenguaje natural', 'big data', 'data science', 'ciencia de datos',
                    'seguridad', 'criptografía', 'computación cuántica', 'edge computing',
                    'cloud computing', 'web3', 'nft', 'cripto', 'cryptocurrency'
                ],
                // Frameworks y herramientas avanzadas
                frameworks: [
                    'tensorflow', 'pytorch', 'keras', 'scikit-learn', 'pandas', 'numpy',
                    'apache spark', 'hadoop', 'kubernetes', 'istio', 'openshift', 'hyperledger',
                    'ethereum', 'jupyter', 'r', 'matlab', 'unity', 'unreal engine', 'opencv',
                    'nltk', 'spacy', 'gpt', 'transformers', 'bert', 'llm'
                ],
                // Conceptos avanzados
                concepts: [
                    'algoritmo', 'red neuronal', 'análisis predictivo', 'clasificación',
                    'clustering', 'regresión', 'series temporales', 'detección de anomalías',
                    'reinforcement learning', 'aprendizaje supervisado', 'aprendizaje no supervisado',
                    'tokenización', 'embeddings', 'contratos inteligentes', 'consenso',
                    'hashing', 'encriptación', 'autenticación', 'autorización', 'federación'
                ],
                // Acciones avanzadas
                actions: [
                    'entrenar', 'predecir', 'clasificar', 'segmentar', 'generar', 'transformar',
                    'analizar', 'visualizar', 'simular', 'detectar', 'reconocer', 'extraer',
                    'automatizar', 'escalar', 'desplegar', 'monitorear', 'adaptar', 'integrar',
                    'securizar', 'optimizar', 'personalizar', 'federar', 'distribuir'
                ]
            }
        };
        
        // Calcular puntuación para cada agente - Versión mejorada con ponderación por categoría
        const scores = {};
        const messageLower = message.toLowerCase();
        
        // Pesos para diferentes categorías de keywords
        const categoryWeights = {
            languages: 2,     // Alto impacto para lenguajes específicos
            concepts: 1.5,    // Impacto medio-alto para conceptos
            frameworks: 1.8,  // Impacto alto para frameworks
            technologies: 1.8,// Impacto alto para tecnologías
            databases: 1.5,   // Impacto medio-alto para bases de datos
            actions: 1.2      // Impacto medio para verbos/acciones
        };
        
        // Pesos de frecuencia y posición
        const frequencyMultiplier = 1.5; // Multiplicador por repeticiones
        const positionBonus = 0.5;      // Bonus por aparición al principio del mensaje
        
        // Extracción de frases complejas antes de tokenización
        let complexPatterns = [];
        for (const agentId in keywordMapping) {
            for (const category in keywordMapping[agentId]) {
                const phrases = keywordMapping[agentId][category].filter(kw => kw.includes(' '));
                complexPatterns = [...complexPatterns, ...phrases];
            }
        }
        
        // Detectar frases complejas primero
        let complexMatches = {};
        complexPatterns.forEach(phrase => {
            if (messageLower.includes(phrase)) {
                complexMatches[phrase] = (messageLower.match(new RegExp(phrase, 'g')) || []).length;
            }
        });
        
        // Inicializar puntuaciones
        for (const agentId in keywordMapping) {
            scores[agentId] = 0;
        }
        
        // Evaluar frases complejas encontradas
        for (const phrase in complexMatches) {
            for (const agentId in keywordMapping) {
                for (const category in keywordMapping[agentId]) {
                    if (keywordMapping[agentId][category].includes(phrase)) {
                        // Otorgar puntos adicionales por frases complejas encontradas
                        const weight = categoryWeights[category] || 1;
                        const frequency = complexMatches[phrase];
                        
                        // Aplicar multiplicador por frecuencia
                        let points = weight * (1 + (frequency - 1) * frequencyMultiplier);
                        
                        // Bonus por posición (si aparece en el primer 20% del mensaje)
                        if (messageLower.indexOf(phrase) < messageLower.length * 0.2) {
                            points += positionBonus;
                        }
                        
                        scores[agentId] += points;
                    }
                }
            }
        }
        
        // Ahora procesar palabras individuales (evitando duplicación con frases ya contadas)
        for (const agentId in keywordMapping) {
            for (const category in keywordMapping[agentId]) {
                // Filtrar solo keywords de una palabra
                const keywords = keywordMapping[agentId][category].filter(kw => !kw.includes(' '));
                
                keywords.forEach(keyword => {
                    // Buscar la palabra completa con límites de palabra
                    const regex = new RegExp(`\\b${keyword}\\b`, 'gi');
                    const matches = messageLower.match(regex);
                    
                    if (matches) {
                        const count = matches.length;
                        const weight = categoryWeights[category] || 1;
                        
                        // Aplicar multiplicador por frecuencia
                        let points = weight * (1 + (count - 1) * 0.5);
                        
                        // Bonus por posición (si aparece en el primer 20% del mensaje)
                        if (messageLower.indexOf(keyword) < messageLower.length * 0.2) {
                            points += positionBonus;
                        }
                        
                        scores[agentId] += points;
                    }
                });
            }
        }
        
        // Normalizar puntuación (0-100)
        const maxScore = Math.max(...Object.values(scores), 0.1); // Evitar división por cero
        
        for (const agentId in scores) {
            scores[agentId] = Math.min(100, Math.round((scores[agentId] / maxScore) * 100));
        }
        
        // Contextualización adicional - check patterns related to file operations
        if (/modifica|crea|edita|archivo|guardar|crear|fichero|file|documento/i.test(messageLower)) {
            // Si el mensaje se refiere a operaciones de archivos, dar boost al developer
            scores['developer'] = Math.min(100, scores['developer'] + 25);
        }
        
        // Encontrar el agente con mayor puntuación
        let bestAgent = null;
        let highestScore = 0;
        
        for (const agentId in scores) {
            if (scores[agentId] > highestScore) {
                highestScore = scores[agentId];
                bestAgent = agentId;
            }
        }
        
        // Si ningún agente alcanza un umbral mínimo, usar avanzado como fallback
        if (highestScore < 20) {
            return {
                agentId: 'advanced',
                confidence: 40, // Confianza media-baja
                message: "No estoy seguro de qué agente es el más adecuado, activando el Agente Avanzado para esta tarea general."
            };
        }
        
        return {
            agentId: bestAgent,
            confidence: highestScore,
            scores: scores
        };
    }
    
    // Activar un agente específico
    function activateAgent(agentId, task) {
        if (!agents[agentId]) {
            console.error(`Agente ${agentId} no encontrado`);
            return false;
        }
        
        // Desactivar agentes actualmente activos
        for (const id in agents) {
            if (agents[id].isActive && id !== agentId) {
                agents[id].isActive = false;
            }
        }
        
        // Activar el nuevo agente
        agents[agentId].isActive = true;
        conversationContext.activeAgents.push(agentId);
        conversationContext.currentTask = task;
        
        // Disparar evento de activación
        const event = new CustomEvent(events.AGENT_ACTIVATED, {
            detail: {
                agentId: agentId,
                task: task,
                timestamp: new Date().toISOString()
            }
        });
        document.dispatchEvent(event);
        
        return true;
    }
    
    // Enviar mensaje al agente activo
    function sendMessageToAgent(message) {
        // Primero, analizar el mensaje para determinar el agente más adecuado
        const analysis = analyzeMessage(message);
        
        // Si no hay un agente activo, o hay uno mejor para esta tarea, activar el recomendado
        const activeAgentId = getActiveAgentId();
        if (!activeAgentId || (analysis.confidence > CONFIDENCE_THRESHOLD && activeAgentId !== analysis.agentId)) {
            activateAgent(analysis.agentId, message);
        }
        
        // Actualizar el contexto de la conversación
        conversationContext.history.push({
            role: 'user',
            content: message,
            timestamp: new Date().toISOString()
        });
        
        // Si hay un procesador natural de comandos, intentar procesarlo
        if (window.naturalCommandProcessor) {
            const parsedRequest = window.naturalCommandProcessor.processRequest(message);
            if (parsedRequest.success) {
                // Es un comando para manipular archivos o ejecutar comandos
                window.naturalCommandProcessor.executeAction(parsedRequest)
                    .then(result => {
                        // Agregar respuesta al historial
                        const response = {
                            role: 'assistant',
                            agentId: getActiveAgentId(),
                            content: result.message,
                            data: result.data,
                            timestamp: new Date().toISOString()
                        };
                        
                        conversationContext.history.push(response);
                        
                        // Disparar evento de mensaje recibido
                        const event = new CustomEvent(events.MESSAGE_RECEIVED, {
                            detail: response
                        });
                        document.dispatchEvent(event);
                    })
                    .catch(error => {
                        // Manejar error en la ejecución
                        const errorResponse = {
                            role: 'assistant',
                            agentId: getActiveAgentId(),
                            content: `Error: ${error.message}`,
                            error: true,
                            timestamp: new Date().toISOString()
                        };
                        
                        conversationContext.history.push(errorResponse);
                        
                        // Disparar evento de mensaje recibido (error)
                        const event = new CustomEvent(events.MESSAGE_RECEIVED, {
                            detail: errorResponse
                        });
                        document.dispatchEvent(event);
                    });
                
                return true;
            }
        }
        
        // Si no es un comando o no se pudo procesar, enviarlo al backend
        return sendToBackend(message, getActiveAgentId());
    }
    
    // Enviar al backend para procesamiento
    function sendToBackend(message, agentId) {
        // Asegurarse de que hay un agente activo
        if (!agentId) {
            console.error("No hay un agente activo para procesar el mensaje");
            return false;
        }
        
        // Obtener el modelo seleccionado
        const modelSelect = document.getElementById('model-select');
        const selectedModel = modelSelect ? modelSelect.value : 'openai';
        
        // Preparar prompt con contexto específico del agente
        const agentPrompt = agents[agentId].prompt || 
            `Eres un asistente especializado en ${agents[agentId].description}. Ayuda al usuario con su solicitud.`;
        
        // Enviar al backend
        fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                agent_id: agentId,
                agent_prompt: agentPrompt,
                context: conversationContext.history.slice(-5), // Últimos 5 mensajes como contexto
                model: selectedModel
            }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.response) {
                // Actualizar el historial y la respuesta del agente
                const response = {
                    role: 'assistant',
                    agentId: agentId,
                    content: data.response,
                    timestamp: new Date().toISOString()
                };
                
                agents[agentId].lastResponse = response;
                conversationContext.history.push(response);
                
                // Disparar evento de mensaje recibido
                const event = new CustomEvent(events.MESSAGE_RECEIVED, {
                    detail: response
                });
                document.dispatchEvent(event);
                
                // Verificar si el agente ha completado la tarea
                checkTaskCompletion(data.response, agentId);
            }
        })
        .catch(error => {
            console.error('Error en la comunicación con el backend:', error);
        });
        
        return true;
    }
    
    // Verificar si la tarea ha sido completada
    function checkTaskCompletion(response, agentId) {
        // Patrones que indican completitud
        const completionPatterns = [
            /he\s+(?:completado|terminado|finalizado|concluido)/i,
            /(?:tarea|solicitud)\s+(?:completada|terminada|finalizada|concluida)/i,
            /(?:listo|hecho|completo|terminado)[\.\!]/i
        ];
        
        // Verificar si algún patrón coincide
        const isCompleted = completionPatterns.some(pattern => pattern.test(response));
        
        if (isCompleted) {
            // Marcar la tarea como completada
            const event = new CustomEvent(events.AGENT_COMPLETED, {
                detail: {
                    agentId: agentId,
                    task: conversationContext.currentTask,
                    timestamp: new Date().toISOString()
                }
            });
            document.dispatchEvent(event);
        }
        
        return isCompleted;
    }
    
    // Obtener el agente activo actual
    function getActiveAgentId() {
        for (const id in agents) {
            if (agents[id].isActive) {
                return id;
            }
        }
        return null;
    }
    
    // Manejador de eventos para mensajes recibidos
    function handleAgentMessage(event) {
        const message = event.detail;
        
        // Actualizar confianza del agente basado en la calidad de respuesta
        // (esto podría mejorarse con feedback explícito del usuario)
        if (message.agentId) {
            // Mantener la confianza estable o ajustarla ligeramente
            agentConfidence[message.agentId] = Math.min(100, 
                agentConfidence[message.agentId] + (message.error ? -5 : 1));
        }
        
        // Aquí se podrían implementar más acciones como feedback automático
        
        // Si hay una interfaz UI para mostrar mensajes
        if (window.app && window.app.chat && typeof window.app.chat.addAgentMessage === 'function') {
            window.app.chat.addAgentMessage(message.content, agents[message.agentId]);
        }
    }
    
    // Manejador para activación de agentes
    function handleAgentActivation(event) {
        const { agentId } = event.detail;
        
        // Actualizar UI para mostrar el agente activo
        if (window.app && window.app.chat && typeof window.app.chat.setActiveAgent === 'function') {
            window.app.chat.setActiveAgent(agentId);
        }
    }
    
    // Manejador para completitud de tareas
    function handleAgentCompletion(event) {
        const { agentId, task } = event.detail;
        
        // Limpiar el estado de la tarea actual
        conversationContext.currentTask = null;
        
        // Agregar mensaje de sistema indicando que la tarea fue completada
        if (window.app && window.app.chat && typeof window.app.chat.addSystemMessage === 'function') {
            window.app.chat.addSystemMessage(`El ${agents[agentId].name} ha completado la tarea solicitada.`);
        }
    }
    
    // Derivar a otro agente
    function delegateToAgent(targetAgentId, reason) {
        const sourceAgentId = getActiveAgentId();
        
        if (!agents[targetAgentId]) {
            console.error(`No se puede derivar al agente ${targetAgentId} porque no existe`);
            return false;
        }
        
        // Agregar mensaje de transición
        const transitionMessage = {
            role: 'system',
            content: `${agents[sourceAgentId].name} ha derivado esta tarea a ${agents[targetAgentId].name}. Motivo: ${reason}`,
            timestamp: new Date().toISOString()
        };
        
        conversationContext.history.push(transitionMessage);
        
        // Activar el nuevo agente
        activateAgent(targetAgentId, conversationContext.currentTask);
        
        // Mostrar mensaje de transición en la UI
        if (window.app && window.app.chat && typeof window.app.chat.addSystemMessage === 'function') {
            window.app.chat.addSystemMessage(transitionMessage.content);
        }
        
        return true;
    }
    
    // Obtener recomendaciones de otros agentes
    function getRecommendationsFromAgents(query) {
        const activeAgentId = getActiveAgentId();
        const recommendations = [];
        
        // Simular consultas a otros agentes para obtener sus perspectivas
        // En una implementación real, esto podría involucrar solicitudes paralelas a cada agente
        
        for (const agentId in agents) {
            if (agentId !== activeAgentId) {
                const analysis = analyzeMessage(query);
                
                if (analysis.scores && analysis.scores[agentId] > 50) {
                    recommendations.push({
                        agentId: agentId,
                        confidence: analysis.scores[agentId],
                        message: `Recomendación del ${agents[agentId].name}: Este agente podría tener una perspectiva valiosa sobre este tema.`
                    });
                }
            }
        }
        
        return recommendations.sort((a, b) => b.confidence - a.confidence);
    }
    
    // Realizar una consulta colaborativa entre múltiples agentes - Versión mejorada
    function collaborativeQuery(query) {
        // Obtener recomendaciones
        const recommendations = getRecommendationsFromAgents(query);
        
        // Si hay recomendaciones con alta confianza, sugerir cambio de agente
        if (recommendations.length > 0 && recommendations[0].confidence > 80) {
            const topRecommendation = recommendations[0];
            
            // Cambiar automáticamente al agente más adecuado y notificar al usuario
            activateAgent(topRecommendation.agentId, query);
            
            if (window.app && window.app.chat && typeof window.app.chat.addSystemMessage === 'function') {
                window.app.chat.addSystemMessage(
                    `Se ha activado el ${agents[topRecommendation.agentId].name} para ayudarte con esta consulta específica.`
                );
            }
            
            // Añadir contexto de la decisión para que el agente tenga más información
            conversationContext.history.push({
                role: 'system',
                content: `Agente cambiado a ${agents[topRecommendation.agentId].name} debido a la naturaleza de la consulta. Confianza: ${topRecommendation.confidence}%`,
                timestamp: new Date().toISOString()
            });
        } else if (recommendations.length > 1) {
            // Si hay múltiples recomendaciones pero ninguna con confianza alta, consultar agentes secundarios
            // para obtener perspectivas adicionales
            const secondaryRecommendations = recommendations.slice(0, 2); // Tomar los 2 mejores agentes secundarios
            
            // Añadir una recomendación combinada de los agentes secundarios
            let combinedPerspective = 'Perspectivas adicionales:';
            for (const rec of secondaryRecommendations) {
                if (rec.confidence > 30) { // Solo considerar agentes con alguna confianza
                    combinedPerspective += `\n• ${agents[rec.agentId].name}: Este agente podría aportar conocimientos en ${agents[rec.agentId].capabilities[0]}.`;
                }
            }
            
            // Solo mostrar perspectivas si hay agentes secundarios relevantes
            if (combinedPerspective !== 'Perspectivas adicionales:' && 
                window.app && window.app.chat && typeof window.app.chat.addSystemMessage === 'function') {
                window.app.chat.addSystemMessage(combinedPerspective);
            }
        }
        
        // Proceder con el agente actual (o el recién activado)
        return sendMessageToAgent(query);
    }
    
    // Interfaz pública del módulo
    return {
        initialize: initialize,
        registerAgent: registerAgent,
        activateAgent: activateAgent,
        sendMessage: sendMessageToAgent,
        getActiveAgent: getActiveAgentId,
        delegateToAgent: delegateToAgent,
        collaborativeQuery: collaborativeQuery,
        getAgents: function() { return {...agents}; },
        getContext: function() { return {...conversationContext}; }
    };
})();