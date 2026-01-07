# 🤖 CVision - Inteligencia Artificial para RRHH

**CVision** es una aplicación web full-stack que utiliza IA (Google Gemini) para automatizar la criba curricular. Extrae datos, anonimiza información sensible y genera un ranking de candidatos basado en su ajuste con la vacante.

## 🌟 Funcionalidades Clave
- **Extracción Automática**: Procesa CVs en PDF/DOCX.
- **Anonimización**: Cumplimiento de RGPD eliminando datos personales antes del análisis.
- **IA Scoring**: Evaluación objetiva de Hard y Soft Skills mediante LLMs.
- **Exportación**: Generación de informes detallados en PDF para reclutadores.

## 🛠️ Tecnologías
- **Backend**: Python / Flask.
- **IA**: Google Gemini API.
- **Base de Datos**: MySQL.
- **Frontend**: HTML5, CSS3, JavaScript.

## 🚀 Cómo ejecutarlo
1. Clona el repositorio.
2. Crea un entorno virtual: `python -m venv venv`.
3. Instala dependencias: `pip install -r requirements.txt`.
4. Configura tu `.env` con las credenciales de DB y Gemini API.
5. Ejecuta: `python app.py`.
