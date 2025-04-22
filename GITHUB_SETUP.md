# Instrucciones para Subir a GitHub

Este documento contiene las instrucciones paso a paso para subir el repositorio CODESTORM a GitHub.

## Requisitos previos

1. Cuenta de GitHub: Necesitas tener una cuenta activa en GitHub.
2. Repositorio creado: Debes crear un repositorio vacío en GitHub con el nombre "CODESTORM" en tu cuenta "josedcape".
3. Credenciales de GitHub: Necesitarás autenticarte con tu usuario y contraseña, o usando un token de acceso personal.

## Pasos para subir el código

### Paso 1: Verificar la configuración remota

El remoto ya está configurado correctamente a:
```
https://github.com/josedcape/CODESTORM.git
```

### Paso 2: Autenticarse en GitHub

Para autenticarte en GitHub, puedes usar alguno de estos métodos:

**Opción 1: Usar credenciales en la terminal**
```
git config --global user.name "Tu nombre"
git config --global user.email "tu.email@ejemplo.com"
```

**Opción 2: Crear y usar un token de acceso personal (recomendado)**
1. Ve a GitHub -> Settings -> Developer settings -> Personal access tokens -> Tokens (classic)
2. Haz clic en "Generate new token (classic)"
3. Dale un nombre descriptivo y selecciona el alcance "repo" para acceso completo al repositorio
4. Genera el token y guárdalo de forma segura
5. Cuando hagas push, usa el token como contraseña

### Paso 3: Hacer push al repositorio remoto

```
git push -u origin main
```

Si usas un token de acceso personal, te pedirá el nombre de usuario y contraseña. Ingresa tu nombre de usuario de GitHub y el token como contraseña.

### Alternativa: Clonar y subir manualmente

Si tienes problemas para hacer push desde Replit, puedes:

1. Descargar el código como un archivo ZIP desde Replit
2. Descomprimirlo en tu computadora
3. Inicializar un nuevo repositorio Git:
   ```
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/josedcape/CODESTORM.git
   git push -u origin main
   ```

## Verificar la subida

Después de hacer push, visita https://github.com/josedcape/CODESTORM para confirmar que todos los archivos se han subido correctamente.