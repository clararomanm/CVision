CVision – AI-powered Candidate Evaluation Platform

CVision es una aplicación web full-stack que utiliza modelos de lenguaje (LLMs) para asistir en la evaluación de candidatos en procesos de selección, combinando criterios técnicos, de RRHH y de negocio de forma estructurada, auditable y reproducible.

El objetivo no es sustituir al recruiter, sino reducir el trabajo manual y repetitivo, mejorar la consistencia de las evaluaciones y generar información accionable (scoring, justificaciones y preguntas de entrevista).

🎯 Problema que resuelve

En muchos procesos de selección:

La evaluación de CVs es manual y poco escalable

Los criterios cambian según el evaluador

Es difícil justificar por qué un candidato obtiene cierta puntuación

Se pierde mucho tiempo generando preguntas de entrevista personalizadas

CVision aborda este problema mediante un motor de evaluación asistido por IA, manteniendo siempre el control humano sobre las decisiones finales.

🧠 Enfoque y principios de diseño

Este proyecto está diseñado con criterios enterprise y responsables:

La IA asiste, no decide de forma autónoma

Las evaluaciones son explicables y trazables

Separación clara entre:

Interfaz

API

Lógica de negocio

Persistencia

Modelos de IA

Uso de prompts estructurados y respuestas en JSON

Pensado para escalar y evolucionar hacia arquitecturas multiagente

🏗️ Arquitectura de la solución

La solución sigue una arquitectura por capas claramente definida:

1. Frontend Web

HTML / CSS / JavaScript

Interfaz ligera tipo SPA

Gestión de puestos y candidatos

Visualización de rankings y resultados

Exportación de informes a PDF

Archivo principal:

CVision.html

2. Backend – API REST

Implementado en Flask

Expone endpoints REST para el frontend

Orquesta el flujo de evaluación completo

Archivo principal:

app.py

3. Motor de Evaluación (Core)

Lógica central del sistema

Evaluación concurrente de candidatos

Simulación de distintos perfiles evaluadores

Normalización y consolidación de resultados

Generación de:

Puntuaciones

Justificaciones

Preguntas de entrevista

Archivo principal:

utils.py

4. Capa de Inteligencia Artificial

Integración con modelos LLM:

Google Gemini

OpenAI (opcional)

Uso de prompts estructurados

Respuestas forzadas en JSON para robustez

IA utilizada como motor de análisis, no como caja negra creativa

5. Persistencia de Datos

Base de datos MySQL

Almacenamiento de:

Candidatos

Puestos

Scoring

Evaluaciones históricas

Permite trazabilidad y re-evaluación

📐 Diagrama de arquitectura

El siguiente diagrama resume el flujo completo del sistema, desde la interacción del usuario hasta la evaluación asistida por IA y el almacenamiento de resultados:
![Arquitectura del Proyecto](arquitectura_CVision.png)

⚙️ Tecnologías utilizadas

Backend: Python, Flask

Frontend: HTML, CSS, JavaScript

Base de datos: MySQL

IA / LLMs: Google Gemini, OpenAI

Otros: AsyncIO, REST APIs, JSON, TailwindCSS

🚀 Ejecución local

Instalar dependencias:

pip install -r requirements.txt


Configurar variables de entorno:

DB_HOST
DB_NAME
DB_USER
DB_PASSWORD
GEMINI_API_KEY
OPENAI_API_KEY (opcional)


Ejecutar la aplicación:

python app.py


Acceder desde el navegador:

http://localhost:5000

🔒 Consideraciones de IA responsable

No se toman decisiones finales automáticamente

Las puntuaciones se acompañan siempre de justificación

El sistema está diseñado para asistencia, no sustitución humana

Preparado para evolucionar hacia validaciones adicionales y control de sesgos

📌 Estado del proyecto

🚧 En desarrollo
Próximos pasos:

Evolución hacia arquitectura multiagente

Agentes especializados por rol (técnico, RRHH, manager)

Mayor control de contexto y validación

Despliegue cloud para demo pública
