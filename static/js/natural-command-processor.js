/**
 * CODESTORM - Procesador de Comandos en Lenguaje Natural
 * Este módulo permite interpretar instrucciones en lenguaje natural
 * y convertirlas en acciones sobre archivos y código.
 */

// Namespace global para el procesador de comandos
window.naturalCommandProcessor = (function() {
    // Patrones de comandos para acciones comunes
    const commandPatterns = {
        modifyFile: /modifica|edita|cambia|actualiza|agrega (en|a)|añade (en|a)/i,
        createFile: /crea|genera|nuevo archivo|nueva archivo/i,
        deleteFile: /elimina|borra|quita|remueve/i,
        executeCommand: /ejecuta|corre|lanza|inicia/i,
        showFile: /muestra|visualiza|ver|abre/i
    };

    // Patrones para identificar archivos
    const filePatterns = {
        htmlFile: /\.html$|\.htm$/i,
        cssFile: /\.css$/i,
        jsFile: /\.js$/i,
        pythonFile: /\.py$/i,
        jsonFile: /\.json$/i
    };

    // Función para extraer nombres de archivos mencionados en el texto
    function extractFilename(text) {
        // Buscar patrones como 'archivo X', 'archivo llamado X', 'el X'
        const filePatterns = [
            /(?:archivo|fichero|documento)\s+(?:llamado\s+)?["']?([a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9]+)["']?/i,
            /(?:en|a|el|la)\s+(?:archivo|fichero)?\s*["']?([a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9]+)["']?/i,
            /["']([a-zA-Z0-9_\-\.\/]+\.[a-zA-Z0-9]+)["']/i
        ];

        for (const pattern of filePatterns) {
            const match = text.match(pattern);
            if (match && match[1]) {
                return match[1].trim();
            }
        }

        return null;
    }

    // Función para extraer el contenido a modificar/agregar
    function extractContent(text) {
        // Buscar contenido entre comillas, triples comillas o después de "contenido:", "código:"
        const contentPatterns = [
            /(?:contenido|código|texto):\s*["'](.+?)["']/is,
            /["'](.+?)["']/is,
            /```(?:\w+)?\s*(.+?)```/is,
            /contenido|código|texto\s+(?:siguiente|este):\s*(.+)/is
        ];

        for (const pattern of contentPatterns) {
            const match = text.match(pattern);
            if (match && match[1]) {
                return match[1].trim();
            }
        }

        return null;
    }

    // Función para determinar la acción a realizar
    function determineAction(text) {
        if (commandPatterns.modifyFile.test(text)) {
            return 'modify';
        } else if (commandPatterns.createFile.test(text)) {
            return 'create';
        } else if (commandPatterns.deleteFile.test(text)) {
            return 'delete';
        } else if (commandPatterns.executeCommand.test(text)) {
            return 'execute';
        } else if (commandPatterns.showFile.test(text)) {
            return 'show';
        }
        return null;
    }

    // Función para extraer un comando de terminal
    function extractCommand(text) {
        const commandPatterns = [
            /(?:comando|instrucción|terminal):\s*["'](.+?)["']/i,
            /(?:ejecuta|corre|lanza|ejecutar|correr)\s+["'](.+?)["']/i,
            /(?:ejecuta|corre|lanza|ejecutar|correr)\s+(?:el comando|la instrucción)?\s+(.+)/i
        ];

        for (const pattern of commandPatterns) {
            const match = text.match(pattern);
            if (match && match[1]) {
                return match[1].trim();
            }
        }

        return null;
    }

    // Función para procesar una petición en lenguaje natural
    function processRequest(text) {
        const action = determineAction(text);
        if (!action) {
            return {
                success: false,
                message: "No se pudo determinar la acción a realizar. Por favor, sé más específico."
            };
        }

        let filename = extractFilename(text);
        let content = extractContent(text);
        let command = extractCommand(text);

        // Construir respuesta basada en la acción
        const response = {
            action: action,
            success: true
        };

        switch (action) {
            case 'modify':
            case 'create':
                if (!filename) {
                    return {
                        success: false,
                        message: "No se pudo identificar el nombre del archivo. Por favor, especifica claramente el nombre del archivo."
                    };
                }
                if (!content && action === 'create') {
                    return {
                        success: false,
                        message: "No se pudo identificar el contenido para el archivo. Por favor, incluye el contenido entre comillas o después de 'contenido:'."
                    };
                }
                response.filename = filename;
                response.content = content;
                break;
            
            case 'delete':
            case 'show':
                if (!filename) {
                    return {
                        success: false,
                        message: "No se pudo identificar el nombre del archivo. Por favor, especifica claramente el nombre del archivo."
                    };
                }
                response.filename = filename;
                break;
            
            case 'execute':
                if (!command) {
                    return {
                        success: false,
                        message: "No se pudo identificar el comando a ejecutar. Por favor, especifica claramente el comando."
                    };
                }
                response.command = command;
                break;
        }

        return response;
    }

    // Función para ejecutar la acción procesada
    function executeAction(parsedRequest) {
        if (!parsedRequest.success) {
            return Promise.reject(new Error(parsedRequest.message));
        }

        switch (parsedRequest.action) {
            case 'modify':
                return modifyFile(parsedRequest.filename, parsedRequest.content);
            
            case 'create':
                return createFile(parsedRequest.filename, parsedRequest.content);
            
            case 'delete':
                return deleteFile(parsedRequest.filename);
            
            case 'show':
                return showFile(parsedRequest.filename);
            
            case 'execute':
                return executeCommand(parsedRequest.command);
            
            default:
                return Promise.reject(new Error("Acción no soportada"));
        }
    }

    // Implementación de las acciones
    function modifyFile(filename, content) {
        return new Promise((resolve, reject) => {
            // Primero obtener el contenido actual del archivo
            fetch(`/api/files/view?path=${encodeURIComponent(filename)}`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`El archivo ${filename} no existe o no se puede acceder a él.`);
                    }
                    return response.json();
                })
                .then(data => {
                    // Ahora actualizar el archivo con el contenido nuevo
                    return fetch('/api/files/save', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            path: filename,
                            content: data.content + '\n' + content // Agregar el nuevo contenido
                        })
                    });
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`No se pudo modificar el archivo ${filename}.`);
                    }
                    return response.json();
                })
                .then(data => {
                    resolve({
                        success: true,
                        message: `Archivo ${filename} modificado correctamente.`,
                        data: data
                    });
                })
                .catch(error => {
                    reject(error);
                });
        });
    }

    function createFile(filename, content) {
        return new Promise((resolve, reject) => {
            fetch('/api/files/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    path: filename,
                    content: content || ''
                })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`No se pudo crear el archivo ${filename}.`);
                }
                return response.json();
            })
            .then(data => {
                resolve({
                    success: true,
                    message: `Archivo ${filename} creado correctamente.`,
                    data: data
                });
            })
            .catch(error => {
                reject(error);
            });
        });
    }

    function deleteFile(filename) {
        return new Promise((resolve, reject) => {
            fetch('/api/files/delete', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    path: filename
                })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`No se pudo eliminar el archivo ${filename}.`);
                }
                return response.json();
            })
            .then(data => {
                resolve({
                    success: true,
                    message: `Archivo ${filename} eliminado correctamente.`,
                    data: data
                });
            })
            .catch(error => {
                reject(error);
            });
        });
    }

    function showFile(filename) {
        return new Promise((resolve, reject) => {
            fetch(`/api/files/view?path=${encodeURIComponent(filename)}`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`El archivo ${filename} no existe o no se puede acceder a él.`);
                    }
                    return response.json();
                })
                .then(data => {
                    resolve({
                        success: true,
                        message: `Contenido del archivo ${filename}:`,
                        data: data
                    });
                })
                .catch(error => {
                    reject(error);
                });
        });
    }

    function executeCommand(command) {
        return new Promise((resolve, reject) => {
            fetch('/api/terminal/execute', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    command: command
                })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Error al ejecutar el comando: ${command}`);
                }
                return response.json();
            })
            .then(data => {
                resolve({
                    success: true,
                    message: `Comando ejecutado correctamente: ${command}`,
                    data: data
                });
            })
            .catch(error => {
                reject(error);
            });
        });
    }

    // Interfaz pública del módulo
    return {
        processRequest: processRequest,
        executeAction: executeAction,
        extractFilename: extractFilename,
        extractContent: extractContent,
        extractCommand: extractCommand
    };
})();