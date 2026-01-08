# CVision — Plataforma Inteligente de Evaluación de Candidatos con IA

CVision es una plataforma de apoyo al proceso de selección de personal basada en Inteligencia Artificial, diseñada para **automatizar la ingestión, anonimización, evaluación y visualización de currículums vitae (CVs)**, manteniendo siempre el **control humano** en la toma de decisiones y cumpliendo con los principios de **IA responsable y privacidad por diseño**.

El proyecto se ha desarrollado como un **Producto Mínimo Viable (PMV)** con una arquitectura, escalable y orientada a un entorno empresarial real.

---

## 📌 Problema que aborda

Los procesos tradicionales de selección presentan varios retos:

- Cribado manual de CVs costoso en tiempo
- Evaluaciones iniciales subjetivas
- Riesgo de sesgos inconscientes
- Gestión de información altamente sensible
- Falta de trazabilidad en las decisiones

CVision aborda estos problemas mediante:
- Automatización del procesamiento de CVs
- Separación estricta entre datos personales y datos evaluables
- Scoring asistido por IA (no decisional)
- Centralización del flujo de selección en una aplicación web

---

## 🧠 Visión general de la solución

CVision implementa un **pipeline de datos y evaluación con IA** que permite:

1. Extraer información estructurada de CVs en múltiples formatos  
2. Anonimizar los datos personales antes de cualquier análisis con IA  
3. Almacenar la información en una base de datos relacional  
4. Comparar perfiles de candidatos con vacantes abiertas mediante LLMs  
5. Mostrar rankings e informes detallados en una aplicación web para RRHH  

---

## 🏗️ Arquitectura del sistema

La siguiente imagen resume la arquitectura completa de la solución:

![Arquitectura del Proyecto](arquitectura_CVision.png)

---

## 🔄 Pipeline de procesamiento de CVs

### 1. Ingesta y extracción de datos
- Activación manual por parte del personal de RRHH
- Lectura de CVs desde un repositorio en la nube
- Formatos soportados: PDF, DOC, DOCX, TXT
- Conversión a texto plano:
  - **PDF**: PyMuPDF (extracción en memoria)
  - **DOC/DOCX**: LibreOffice (archivos temporales eliminados tras uso)

### 2. Procesamiento mediante LLM local
- Envío del texto del CV a un LLM ejecutado en entorno local
- Extracción de entidades relevantes:
  - Datos personales
  - Experiencia profesional
  - Formación académica
  - Competencias técnicas y soft skills
- Salida estructurada en formato JSON (en memoria)

---

## 🔐 Anonimización y privacidad

La anonimización es un pilar fundamental del sistema:

- Eliminación de:
  - Nombre
  - Dirección
  - Email
  - Teléfono
- Cumplimiento de:
  - RGPD
  - LOPDGDD
- Separación clara entre:
  - **Datos personales** (columnas relacionales)
  - **Datos anonimizados** (JSON almacenado en el campo `Otros`)

Los modelos externos **solo consumen información anonimizada**.

---

## 🗄️ Tabulación y almacenamiento

Una vez finalizada la extracción y anonimización:

- Conexión a base de datos relacional (Amazon RDS)
- Generación de dos representaciones:
  - **CSV tabular** (datos personales + JSON en columna `Otros`)
  - **JSON anonimizado** (experiencia, formación, skills)
- Garantía de trazabilidad y coherencia entre datos personales y evaluables

---

## 🧪 Proceso de Scoring con IA

### Fuentes de datos
- **Candidatos**: información anonimizada desde CSV / base de datos
- **Vacantes abiertas**: requisitos del puesto en formato JSON

### Evaluación con LLM (Gemini AI)
Para cada par Candidato–Vacante:
- Se envía el JSON del candidato + JSON de la vacante
- El modelo simula tres perfiles evaluadores:
  - Evaluador técnico
  - Evaluador de RRHH
  - Manager neutral
- Se evalúan cuatro dimensiones:
  - Experiencia profesional
  - Formación académica
  - Hard skills
  - Soft skills

### Resultado
- Puntuación global (0–100)
- Justificación sintética
- Evaluación de habilidades (escala A–D)
- Pesos configurables por RRHH
- Persistencia en base de datos y CSV histórico (`dataset_ranking.csv`)

> La IA **no decide**. Solo prioriza y justifica.

---

## 🖥️ Aplicación web de RRHH

La aplicación web centraliza todo el flujo de selección:

### Módulos principales
- **Dashboard**: métricas globales y guía de uso
- **Gestión de Puestos**: creación de plantillas de rol
- **Centro de Vacantes**: apertura y cierre de procesos
- **Ranking de Candidatos**: Top 5 y lista completa
- **Informe de Candidato**: evaluación detallada y editable

---

## 📄 Informe de RRHH

Cada candidato dispone de un informe completo con:

- Decisión manual: ¿Apto para entrevista? (Sí / No)
- Puntuación global y justificaciones
- Datos personales
- Formación académica
- Trayectoria profesional
- Evaluación de competencias
- Observaciones internas
- Preguntas sugeridas para entrevista
- Exportación a PDF
- Sincronización con base de datos

El juicio humano **prevalece siempre** sobre la evaluación automática.

---

## 🛠️ Tecnologías utilizadas

- **Backend**: Python
- **Modelos de lenguaje**:
  - LLM local (extracción y anonimización)
  - Gemini AI (scoring con datos anonimizados)
- **Base de datos**: Amazon RDS
- **Frontend**: HTML / Web App
- **Procesamiento de documentos**:
  - PyMuPDF
  - LibreOffice
- **Formatos de datos**: JSON, CSV

---

## 🚀 Evolución futura

- Ingesta automática y en tiempo real
- Sistemas de colas (SQS / RabbitMQ)
- OCR para CVs escaneados
- Control de duplicados y versionado
- Chat inteligente para RRHH
- API REST para integraciones externas
- Integración con BI (Power BI, Tableau)
- Conexión con ATS corporativos

---

