# Contribuyendo a CODESTORM

¡Gracias por tu interés en contribuir a CODESTORM! Este documento proporciona pautas para contribuir a este proyecto.

## Código de conducta

Por favor, sé respetuoso y considerado con los demás contribuyentes. No se tolerará ningún tipo de acoso o comportamiento ofensivo.

## Cómo contribuir

### Reportando bugs

Si encuentras un bug, por favor crea un issue en GitHub con la siguiente información:
- Título claro y descriptivo
- Pasos detallados para reproducir el bug
- Comportamiento esperado y comportamiento actual
- Capturas de pantalla si aplica
- Entorno (navegador, sistema operativo, etc.)

### Sugerencias de mejora

Para proponer nuevas características o mejoras:
- Verifica primero si la idea ya ha sido propuesta en los issues
- Crea un nuevo issue con un título claro
- Describe detalladamente la funcionalidad propuesta
- Explica por qué sería útil para el proyecto

### Pull Requests

1. Bifurca (fork) el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/amazing-feature`)
3. Haz los cambios necesarios
4. Asegúrate de que el código sigue las convenciones de estilo
5. Haz commit de tus cambios (`git commit -m 'Añadir amazing-feature'`)
6. Sube tus cambios (`git push origin feature/amazing-feature`)
7. Abre un Pull Request

## Convenciones de código

### Python
- Sigue PEP 8
- Utiliza docstrings para todas las funciones y clases
- Mantén los nombres de variables y funciones descriptivos
- Comenta el código cuando sea necesario para explicar la lógica

### JavaScript
- Utiliza camelCase para variables y funciones
- Utiliza 4 espacios para indentación
- Escribe comentarios para explicar la lógica compleja

## Estructura del proyecto

```
CODESTORM/
├── app.py              # Aplicación Flask principal
├── main.py             # Punto de entrada
├── models.py           # Modelos de base de datos
├── static/             # Archivos estáticos (CSS, JS)
│   ├── css/            # Hojas de estilo
│   └── js/             # Scripts JavaScript
├── templates/          # Plantillas HTML
├── user_workspaces/    # Espacios de trabajo de usuarios
└── .env                # Variables de entorno (no incluido en el repositorio)
```

## Proceso de desarrollo

1. Los issues etiquetados como "good first issue" son buenos para comenzar
2. Para cambios importantes, primero discute a través de un issue
3. Sigue el flujo de trabajo de Git Flow (feature branches, development, main)
4. Asegúrate de que tus cambios no rompan tests existentes
5. Añade tests para nuevas características cuando sea apropiado

## Licencia

Al contribuir, aceptas que tus contribuciones serán licenciadas bajo la misma licencia que el proyecto (MIT).