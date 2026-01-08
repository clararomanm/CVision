# CVision: Inteligencia Artificial Aplicada a la Selección de Talento (TFM)

**CVision** es una solución integral diseñada para modernizar y automatizar los departamentos de Recursos Humanos (RRHH). Este proyecto nace como respuesta a la ineficiencia de los procesos tradicionales, transformando la gestión de talento mediante un pipeline de datos inteligente y modelos de lenguaje de última generación.

---

## 🎯 Visión del Proyecto
El objetivo principal es reducir los sesgos humanos y optimizar el tiempo de respuesta en la cobertura de vacantes. CVision no solo lee CVs, sino que los entiende, anonimiza y evalúa de forma objetiva frente a requisitos técnicos específicos.

## 🏗️ Arquitectura y Solución Técnica
El proyecto implementa un flujo de datos estructurado en 4 etapas críticas:

1.  **Ingesta y Extracción**: Procesamiento de currículums en diversos formatos (PDF, DOCX) convirtiendo información no estructurada en datos aprovechables.
2.  **Anonimización Inteligente**: Sistema diseñado bajo el cumplimiento de la **RGPD y LOPDGDD**, separando los datos personales del perfil profesional para garantizar una evaluación ciega y justa.
3.  **Motor de Scoring e IA**: Uso de **Google Gemini** y **LLMs** para realizar un análisis comparativo entre el candidato y la vacante. Se evalúan cuatro ejes con pesos específicos:
    * Experiencia Profesional (25%)
    * Formación Académica (25%)
    * Hard Skills (25%)
    * Soft Skills (25%)
4.  **Panel de Control (WebApp)**: Interfaz intuitiva para técnicos de RRHH que permite la gestión de vacantes, visualización de rankings y exportación de informes detallados en PDF.
graph TD
    %% Estilos de Nodos (Estilo Google Cloud)
    classDef frontend fill:#4285F4,stroke:#3b78e7,color:#fff,font-weight:bold
    classDef backend fill:#34A853,stroke:#2d9249,color:#fff,font-weight:bold
    classDef ai fill:#FBBC05,stroke:#f2a600,color:#202124,font-weight:bold
    classDef database fill:#EA4335,stroke:#d33828,color:#fff,font-weight:bold
    classDef logic fill:#f1f3f4,stroke:#dadce0,color:#202124,font-style:italic

    subgraph Client_Tier [Capa de Presentación]
        A[CVision.html <br/> UI Dinámica - Tailwind CSS]:::frontend
    end

    subgraph App_Tier [Capa de Aplicación - Flask]
        B[app.py <br/> API REST Server]:::backend
        C[utils.py <br/> Orquestador de Lógica]:::backend
        
        subgraph Async_Engine [Motor de Concurrencia]
            D{asyncio.Semaphore <br/> N=70}:::logic
        end
    end

    subgraph AI_Services [Capa de Inteligencia Artificial]
        E[Google Gemini Pro API <br/> Modelos de Lenguaje]:::ai
        F[Anonimizador de Datos <br/> Filtro PII / RGPD]:::ai
    end

    subgraph Data_Tier [Capa de Datos]
        G[(MySQL Database <br/> Local/Cloud)]:::database
        H[Repositorio CVs <br/> PDF / DOCX]:::database
    end

    %% Flujo de ejecución detallado
    A -- "1. Trigger: Clic Actualizar" --> B
    B -- "2. Llamada asíncrona" --> C
    C -- "3. Lectura de binarios" --> H
    C -- "4. Limpieza RGPD" --> F
    F -- "5. Prompt Contextualizado" --> D
    D -- "6. Peticiones Paralelas" --> E
    E -- "7. JSON Scoring" --> D
    D -- "8. Consolidación" --> C
    C -- "9. SQL Update / Insert" --> G
    G -- "10. Ranking Actualizado" --> A
## 🛠️ Stack Tecnológico
* **Lenguaje**: Python 3.x
* **Backend**: Flask (con soporte asíncrono para procesamiento paralelo).
* **IA & NLP**: Google Generative AI (Gemini), OpenAI API.
* **Base de Datos**: MySQL (Arquitectura relacional para gestión de candidatos y puestos).
* **Frontend**: HTML5, CSS3 moderno, JavaScript (Integración con APIs mediante CORS).
* **Entorno**: Gestión de variables mediante `python-dotenv`.

## 📂 Estructura del Repositorio
* `app.py`: Servidor principal y definición de rutas de la API.
* `utils.py`: Lógica de negocio, integración con modelos de IA y motor de scoring.
* `requirements.txt`: Dependencias del proyecto.
* `templates/`: Interfaz de usuario (CVision.html).
* `.gitignore`: Configuración de seguridad para excluir datos sensibles y entornos virtuales.

## 🚀 Instalación y Configuración
1.  **Clonar el repositorio:**
    ```bash
    git clone [https://github.com/TU_USUARIO/ML-IA-Portfolio.git](https://github.com/TU_USUARIO/ML-IA-Portfolio.git)
    ```
2.  **Crear entorno virtual:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # En Windows: venv\Scripts\activate
    ```
3.  **Instalar dependencias:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Variables de Entorno:** Configura un archivo `.env` con:
    ```env
    DB_HOST=tu_host
    DB_NAME=tu_db
    DB_USER=tu_usuario
    DB_PASS=tu_password
    GOOGLE_API_KEY=tu_api_key_de_gemini
    ```

## 📈 Metodología de Trabajo
El proyecto se ha desarrollado bajo metodologías ágiles, dividiendo la carga de trabajo en Sprints:
* **Análisis**: Identificación de KPIs y retos de RRHH.
* **Diseño**: Definición de modelos de datos y algoritmos de ranking.
* **Validación**: Pruebas internas para asegurar la calidad técnica y la adaptación a procesos humanos.

---
*Este proyecto es parte de mi Trabajo Fin de Máster, enfocado en demostrar la capacidad de integrar Ingeniería de Datos e Inteligencia Artificial en entornos empresariales reales.*
