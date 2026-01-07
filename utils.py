import asyncio
from flask import logging
from openai import OpenAI
import google.generativeai as genai
import json
import mysql.connector
from mysql.connector import Error
from collections import defaultdict
import statistics
from unidecode import unidecode
import os
from dotenv import load_dotenv
import time
from collections import defaultdict
from typing import List, Dict, Any


load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)
DB_CONFIG = {
    "database": os.getenv('DB_NAME'),
    "user": os.getenv('DB_USER'),
    "password": os.getenv('DB_PASS'),
    "host": os.getenv('DB_HOST'),
    "port": "3306"
}

PESOS = {
    "experiencia": 0.25, "formacion": 0.25,
    "skills_tecnicas": 0.25, "soft_skills": 0.25
}


MAX_CONSULTAS_CONCURRENTES = 70
TIMEOUT = 35

EVALUADORES = {
        "Evaluador Técnico": "Eres un evaluador técnico con un enfoque escéptico especialista en el área de {nombre_vacante}. Tu tarea es analizar la información del candidato con un alto grado de escepticismo, buscando inconsistencias y áreas de mejora. Eres meticuloso en tu evaluación y no aceptas afirmaciones sin evidencia sólida.",
        "Evaluador RRHH": "Eres un evaluador de recursos humanos con un enfoque en el potencial y las soft skills, especialista en el área de {nombre_vacante}. Tu tarea es analizar la información del candidato buscando habilidades interpersonales, adaptabilidad y potencial de crecimiento. Eres empático en tu evaluación y valoras las experiencias y actitudes del candidato.",
        "Evaluador Manager": "Eres un manager neutral con experiencia en la gestión de equipos en el área de {nombre_vacante}. Tu tarea es analizar la información del candidato desde una perspectiva objetiva, considerando tanto las habilidades técnicas como las soft skills. Eres equilibrado en tu evaluación y valoras la diversidad de experiencias."
    }


def _calcular_consenso_skill(lista_ratings: list) -> str:
    mapa_valor = {'A': 1, 'B': 2, 'C': 3, 'D': 4}
    mapa_letra = {1: 'A', 2: 'B', 3: 'C', 4: 'D'}
    valores_numericos = [mapa_valor[r] for r in lista_ratings if r in mapa_valor]
    if not valores_numericos: return 'N/A'
    mediana = statistics.median(valores_numericos)
    return mapa_letra.get(round(mediana), 'A')

def _unique_list(lst: list) -> list:
    return list(dict.fromkeys(lst))

# --- Procesamiento Principal ---
def _procesar_evaluaciones(data: list) -> dict:
    """
    Procesa una lista de evaluaciones de diferentes perfiles, agrupa por candidato,
    y calcula una puntuación final consolidada y otros datos de consenso.
    """
    candidatos_agrupados = defaultdict(list)
    for evaluacion in data:
        candidatos_agrupados[evaluacion['id_candidato']].append(evaluacion)

    resultados_finales = {}

    for candidato_id, evaluaciones in candidatos_agrupados.items():
        evaluaciones_con_clave = [
            (eval, eval.get('perfil_evaluador', ''))
            for eval in evaluaciones
        ]
        
        puntuaciones_sum = defaultdict(float)
        num_evaluaciones = len(evaluaciones)
        
        # ---> INICIO DE LA CORRECCIÓN <---
        
        # Define la escala máxima de las puntuaciones de entrada (ej: 100).
        # Esto se usará para normalizar todas las notas a una escala de 0 a 10.
        MAX_SCORE_ENTRADA = 100.0

        for eval in evaluaciones:
            for categoria, score in eval.get('puntuaciones_parciales', {}).items():
                try:
                    score_num = float(score)
                    
                    # Normaliza el score a una escala de 0 a 10 antes de sumarlo.
                    # Si un score es 90, se convierte en 9.0 para los cálculos.
                    score_normalizado = score_num / (MAX_SCORE_ENTRADA / 10.0)
                    
                    puntuaciones_sum[categoria] += score_normalizado

                except (ValueError, TypeError):
                    # Si el 'score' no es un número (ej: "N/A"), ignóralo.
                    print(f"Aviso: Valor no numérico '{score}' en '{categoria}' para el candidato {candidato_id}. Se omitirá.")
                    pass
        
        # ---> FIN DE LA CORRECCIÓN <---

        puntuaciones_promediadas = {
            cat: round(total / num_evaluaciones, 2) for cat, total in puntuaciones_sum.items()
        }
        
        puntuacion_ponderada = sum(puntuaciones_promediadas.get(cat, 0) * peso for cat, peso in PESOS.items())
        
        # Ahora que la puntuación ponderada está en escala 0-10, la multiplicamos por 10
        # para obtener el resultado final en escala 0-100.
        puntuacion_global_final = int(puntuacion_ponderada * 10)

        razonamiento_final = "\n\n---\n\n".join(
            f"--- Razonamiento del {clave} ---\n{eval.get('razonamiento_paso_a_paso', 'No proporcionado.')}"
            for eval, clave in evaluaciones_con_clave
        )
        
        justificacion_final = "\n".join(
            f"- Justificación del {clave}: {eval.get('justificacion', 'No proporcionada.')}"
            for eval, clave in evaluaciones_con_clave
        )

        soft_skills_agrupadas = defaultdict(list)
        hard_skills_agrupadas = defaultdict(list)
        for eval, _ in evaluaciones_con_clave:
            for skill, rating in eval.get('match_soft_skills', {}).items(): soft_skills_agrupadas[skill].append(rating)
            for skill, rating in eval.get('match_skills_tecnicas', {}).items(): hard_skills_agrupadas[skill].append(rating)

        soft_skills_consenso = {s: _calcular_consenso_skill(r) for s, r in soft_skills_agrupadas.items()}
        hard_skills_consenso = {s: _calcular_consenso_skill(r) for s, r in hard_skills_agrupadas.items()}

        preguntas_por_perfil = defaultdict(list)
        for eval, clave in evaluaciones_con_clave:
            preguntas_por_perfil[clave].extend(eval.get('preguntas_entrevista', []))
        
        evaluacion_final_candidato = {
            'puntuacion_global': puntuacion_global_final,
            'razonamiento_paso_a_paso': razonamiento_final,
            'puntuaciones_parciales_promediadas': puntuaciones_promediadas,
            'justificacion_consolidada': justificacion_final,
            'match_soft_skills_consenso': soft_skills_consenso,
            'match_skills_tecnicas_consenso': hard_skills_consenso,
            'PREGUNTAS_TECNICAS': _unique_list(preguntas_por_perfil.get("Evaluador Técnico", [])),
            'PREGUNTAS_RRHH': _unique_list(preguntas_por_perfil.get("Evaluador RRHH", [])),
            'PREGUNTAS_MANAGER': _unique_list(preguntas_por_perfil.get("Evaluador Manager", []))
        }
        
        resultados_finales[candidato_id] = evaluacion_final_candidato
        
    return resultados_finales
    
def obtener_datos_todos_los_candidatos() -> dict:
    """
    Recupera los datos de la columna 'Otros' de TODOS los candidatos y los devuelve
    en un diccionario con el formato {id_candidato: datos_json}.
    """
    conn = None
    todos_los_candidatos = {}
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        query = "SELECT id_candidato, Otros FROM CANDIDATOS;"

        cursor.execute(query)

        for row in cursor.fetchall():
            json_string = row.get('Otros')
            # Parseamos la cadena de texto JSON a un diccionario de Python
            todos_los_candidatos[row['id_candidato']] = json.loads(json_string) if json_string else {}

        print(f"✅ Datos para {len(todos_los_candidatos)} candidatos cargados en memoria.")
        return todos_los_candidatos

    except Error as e:
        print(f"❌ Error al obtener los datos de todos los candidatos: {e}")
        return {}
    finally:
        if conn and conn.is_connected():
            conn.close()
    
def _eliminar_evaluaciones_por_puesto(nombre_vacante: str):
    """
    Elimina todas las evaluaciones de SCORING y VALORACION_HARD_SKILL
    asociadas a un puesto específico. Es el paso previo a una re-evaluación.
    """
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        conn.autocommit = False
        cursor = conn.cursor()
        print(f"   -> Eliminando evaluaciones antiguas del puesto '{nombre_vacante}'...")

        # El orden es importante para no violar restricciones de claves foráneas.
        # Primero borramos de la tabla que tiene la dependencia.
        cursor.execute("DELETE FROM VALORACION_SOFT_SKILL")
        cursor.execute("DELETE FROM VALORACION_HARD_SKILL WHERE PUESTO = %s;", (nombre_vacante,))
        cursor.execute("DELETE FROM SCORING WHERE PUESTO = %s;", (nombre_vacante,))

        # Nota: VALORACION_SOFT_SKILL no se ve afectada, ya que es agnóstica al puesto.

        conn.commit()
        print(f"   -> OK. {cursor.rowcount} evaluaciones eliminadas de la tabla SCORING.")
    except Error as e:
        print(f"❌ Error al eliminar las evaluaciones del puesto '{nombre_vacante}': {e}")
        if conn:
            conn.rollback()
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

async def evaluar_candidato_con_llm(semaphore,id, candidato_json, requisitos, perfil_evaluador):
    """
    Realiza una evaluación detallada y, además, genera 5 preguntas de entrevista.
    """
    async with semaphore:
        if not isinstance(requisitos, dict):
            requisitos = {}

        candidato_str = json.dumps(candidato_json, indent=2, ensure_ascii=False)
        requisitos_str = json.dumps(requisitos, indent=2, ensure_ascii=False)
        requisitos_block = f"```json\n{requisitos_str}\n```"
        candidato_block = f"```json\n{candidato_str}\n```"
        
        prompt = f"""
        **Tu perspectiva como evaluador**
        {EVALUADORES[perfil_evaluador]}

        Evalúa al siguiente candidato para el puesto definido en los requisitos, basándote **únicamente** en la información de su perfil en formato JSON.

        **Requisitos del Puesto:**
        {requisitos_block}

        **Perfil del Candidato (JSON):**
        {candidato_block}

        **Tu Tarea:**
        1.  Realiza un análisis siguiendo el **orden estricto de importancia**.
        2.  **Genera 5 preguntas de entrevista** diseñadas para profundizar en las áreas más débiles o dudosas que hayas identificado en tu análisis.
        3.  Devuelve toda tu evaluación en el formato JSON requerido.

        **Orden de Análisis Obligatorio:**
        1.  **Experiencia Profesional (`trayectoria_profesional`):** El factor más crítico.
        2.  **Formación (`formacion`):** Segundo factor más importante.
        3.  **Competencias Técnicas (`competencias_tecnicas`):** Evalúa el nivel de las competencias.
        4.  **Soft Skills (`soft_skills`):** El factor de menor peso.

        **Formato JSON de Salida Requerido:**
        1.  `id_candidato`: El ID del candidato {id}.
        2.  `perfil_evaluador`: El perfil del evaluador utilizado {perfil_evaluador}.
        3.  `razonamiento_paso_a_paso`: Un texto donde analizas al candidato **siguiendo los 4 puntos del orden de análisis obligatorio**.
        4.  `puntuaciones_parciales`: Un objeto JSON con una puntuación de 0 a 100 para cada categoría. Ejemplo: {{"experiencia": 80, "formacion": 90, "skills_tecnicas": 70, "soft_skills": 80}}
        5.  `justificacion`: Un resumen breve (máximo 3 frases) de tu evaluación.
        6.  `match_soft_skills`: Para cada habilidad, evalúa el nivel de evidencia en el texto y asigna una calificación: 'A' (evidencia mínima), 'B' (evidencia moderada), 'C' (evidencia sólida), 'D' (evidencia muy fuerte y demostrada). Si la habilidad no se menciona en absoluto, usa el valor 'A'.
        7.  `match_skills_tecnicas`: Para cada habilidad, evalúa el nivel de evidencia en el texto y asigna una calificación: 'A' (evidencia mínima), 'B' (evidencia moderada), 'C' (evidencia sólida), 'D' (evidencia muy fuerte y demostrada). Si la habilidad no se menciona en absoluto, usa el valor 'A'.
        8.  `preguntas_entrevista`: Una lista de 5 preguntas en formato string.

        **Reglas Críticas de Puntuación:**
        - **0-25 (Candidato Irrelevante):** Si la experiencia Y la formación son de un campo completamente diferente.
        - **26-50 (Candidato Poco Relevante):** Si tiene la formación base pero carece de experiencia práctica y skills críticas.
        - **51-75 (Candidato Viable):** Si demuestra buena alineación en formación O en experiencia, con algunas carencias en skills.
        - **76-100 (Candidato Fuerte):** Si muestra fuerte alineación en experiencia Y formación, y domina la mayoría de skills.
        **Reglas Críticas de Formato:**
        - La salida debe ser **únicamente un objeto JSON válido** y nada más.
        - No incluyas comentarios, texto introductorio o final fuera del bloque JSON.
        - Asegúrate de que todos los campos estén separados por comas.
        - Escapa correctamente todos los caracteres especiales dentro de los strings, como saltos de línea (usando \\n) o comillas dobles (usando \\\").
        """

        try:
            model = genai.GenerativeModel(
                'gemini-2.0-flash',
                generation_config={"response_mime_type": "application/json", "temperature": 0.1}
            )
            response = await model.generate_content_async(prompt)
            return json.loads(response.text)
        except Exception as e:
            print(f"Error al evaluar con la API de Gemini: {e}")
            # Devuelve una estructura de error consistente que incluye el campo de preguntas
            return {
                "id_candidato": id,
                "perfil_evaluador": perfil_evaluador,
                "razonamiento_paso_a_paso": f"Error en el procesamiento con Gemini: {e}",
                "puntuaciones_parciales": {"experiencia": 0, "formacion": 0, "skills_tecnicas": 0, "soft_skills": 0},
                "justificacion": "Error en el procesamiento.",
                "match_soft_skills": {},
                "match_skills_tecnicas": {},
                "preguntas_entrevista": ["Error al generar preguntas."]
            }

    
def _calcular_consenso_skill(lista_ratings: list) -> str:
    """Calcula la calificación de consenso (mediana) para una skill."""
    mapa_valor = {'A': 1, 'B': 2, 'C': 3, 'D': 4}
    mapa_letra = {v: k for k, v in mapa_valor.items()}
    valores_numericos = [mapa_valor.get(r, 0) for r in lista_ratings]
    if not valores_numericos: return 'A'
    mediana = statistics.median(valores_numericos)
    return mapa_letra.get(round(mediana), 'A')
            
def obtener_requisitos_puesto(puesto: str) -> dict:
    """
    Recupera la misión, hard skills y soft skills para un puesto de trabajo específico.
    """
    conn = None
    requisitos_puesto = {
        'puesto': puesto,
        'mision': '',
        'skills_tecnicas_requeridas': [],
        'soft_skills_deseadas': []
    }

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        with conn.cursor() as cur:
            # 2. Recuperar la MISION del puesto
            query_mision = "SELECT MISION FROM PUESTOS_PREDEFINIDOS WHERE PUESTO = %s;"
            cur.execute(query_mision, (puesto,))
            resultado_mision = cur.fetchone()
            if resultado_mision:
                requisitos_puesto['mision'] = resultado_mision[0]
            else:
                print(f"⚠️  No se encontró el puesto '{puesto}' en la tabla PUESTOS_PREDEFINIDOS.")

            # 3. Recuperar las HARD SKILLS del puesto
            query_hard_skills = "SELECT HARD_SKILL FROM CAT_HARD_SKILL WHERE PUESTO = %s;"
            cur.execute(query_hard_skills, (puesto,))
            # El resultado es una lista de tuplas [(skill1,), (skill2,)...], la aplanamos.
            resultados_hard_skills = cur.fetchall()
            requisitos_puesto['skills_tecnicas_requeridas'] = [item[0] for item in resultados_hard_skills]

            # 4. Recuperar todas las SOFT SKILLS
            query_soft_skills = "SELECT SOFT_SKILL FROM CAT_SOFT_SKILL;"
            cur.execute(query_soft_skills)
            resultados_soft_skills = cur.fetchall()
            requisitos_puesto['soft_skills_deseadas'] = [item[0] for item in resultados_soft_skills]

            print(f"✅ Requisitos para el puesto '{puesto}' recuperados con éxito.")
            return requisitos_puesto

    except Error as error:
        print(f"❌ Error al recuperar los requisitos del puesto: {error}")
        return None
    finally:
        if conn and conn.is_connected():
            conn.close()


def normalizar_texto(texto: str) -> str:
    """Convierte texto a minúsculas, sin tildes ni espacios extra."""
    if not isinstance(texto, str): return ""
    return unidecode(texto).lower().strip()

def guardar_evaluaciones_masivamente(lista_evaluaciones: dict, nombre_vacante: str):
    """
    Guarda una lista de evaluaciones en la BD de forma masiva y eficiente.
    Utiliza una única transacción y minimiza las consultas a la BD.
    
    Args:
        lista_evaluaciones (list): Una lista de diccionarios. Cada diccionario
                                  debe contener 'id_candidato' y 'evaluacion'.
        nombre_vacante (str): El nombre de la vacante para la que se evalúa.
    """
        
    if not lista_evaluaciones:
        print("La lista de evaluaciones está vacía. No hay nada que hacer.")
        return

    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        conn.autocommit = False
        cursor = conn.cursor()

        # --- 1. PRE-CÁLCULOS Y CONSULTAS ÚNICAS ---

        # Obtener mapas de skills UNA SOLA VEZ
        cursor.execute("SELECT ID_SOFT_SKILL, SOFT_SKILL FROM CAT_SOFT_SKILL;")
        mapa_soft_skill_id = {normalizar_texto(nombre): id_skill for id_skill, nombre in cursor.fetchall()}
        
        cursor.execute("SELECT ID_HARD_SKILL, HARD_SKILL FROM CAT_HARD_SKILL WHERE PUESTO = %s;", (nombre_vacante,))
        mapa_hard_skill_id = {normalizar_texto(nombre): id_skill for id_skill, nombre in cursor.fetchall()}
        
        # Comprobar duplicados de SCORING de forma masiva
        ids_candidatos_entrantes = [candidato_id for candidato_id, item in lista_evaluaciones.items()]
        placeholders = ', '.join(['%s'] * len(ids_candidatos_entrantes))
        query_check_scoring = f"SELECT ID_CANDIDATO FROM SCORING WHERE PUESTO = %s AND ID_CANDIDATO IN ({placeholders});"
        cursor.execute(query_check_scoring, (nombre_vacante, *ids_candidatos_entrantes))
        candidatos_con_scoring = {row[0] for row in cursor.fetchall()}

        # Comprobar qué candidatos ya tienen soft skills de forma masiva
        query_check_soft = f"SELECT DISTINCT ID_CANDIDATO FROM VALORACION_SOFT_SKILL WHERE ID_CANDIDATO IN ({placeholders});"
        cursor.execute(query_check_soft, (*ids_candidatos_entrantes,))
        candidatos_con_soft_skills = {row[0] for row in cursor.fetchall()}

        # --- 2. PREPARAR DATOS PARA INSERCIÓN MASIVA ---

        datos_para_scoring = []
        datos_para_soft_skills = []
        datos_para_hard_skills = []

        for key, item in lista_evaluaciones.items():
            id_candidato = key
            evaluacion = item

            # Omitir si ya existe una evaluación para este puesto
            if id_candidato in candidatos_con_scoring:
                print(f"⚠️  AVISO: Ya existe SCORING para el candidato {id_candidato}. Se omite.")
                continue

            # Preparar datos para la tabla SCORING
            puntuaciones_parciales = evaluacion.get('puntuaciones_parciales_promediadas', {})
            datos_para_scoring.append((
                nombre_vacante,
                id_candidato,
                evaluacion.get('puntuacion_global'),
                evaluacion.get('justificacion_consolidada'),
                puntuaciones_parciales.get('formacion'),
                puntuaciones_parciales.get('experiencia'),
                puntuaciones_parciales.get('soft_skills'),
                puntuaciones_parciales.get('skills_tecnicas'),
                json.dumps(evaluacion.get('PREGUNTAS_TECNICAS', []), ensure_ascii=False),
                json.dumps(evaluacion.get('PREGUNTAS_RRHH', []), ensure_ascii=False),
                json.dumps(evaluacion.get('PREGUNTAS_MANAGER', []), ensure_ascii=False)
            ))

            # Preparar datos para VALORACION_HARD_SKILL
            for nombre_skill, valoracion in evaluacion.get('match_skills_tecnicas_consenso', {}).items():
                id_skill = mapa_hard_skill_id.get(normalizar_texto(nombre_skill))
                if id_skill:
                    # Se añade una entrada por cada marca (IA y Humano, por ejemplo)
                    datos_para_hard_skills.append((nombre_vacante, id_candidato, id_skill, valoracion, 0))
                    datos_para_hard_skills.append((nombre_vacante, id_candidato, id_skill, valoracion, 1))

            # Preparar datos para VALORACION_SOFT_SKILL (solo si no existen previamente)
            if id_candidato not in candidatos_con_soft_skills:
                for nombre_skill, valoracion in evaluacion.get('match_soft_skills_consenso', {}).items():
                    id_skill = mapa_soft_skill_id.get(normalizar_texto(nombre_skill))
                    if id_skill:
                        datos_para_soft_skills.append((id_candidato, id_skill, valoracion, 0))
                        datos_para_soft_skills.append((id_candidato, id_skill, valoracion, 1))
        
        # --- 3. EJECUTAR INSERCIONES MASIVAS ---
        
        if datos_para_scoring:
            print(f"1/3 - Insertando {len(datos_para_scoring)} registros en SCORING...")
            query_scoring = """INSERT INTO SCORING (PUESTO, ID_CANDIDATO, SCORE, Justificacion, SCORE_FORMACION, 
                               SCORE_EXPERIENCIA, SCORE_SOFT_SKILL, SCORE_HARD_SKILL, PREGUNTAS_TECNICAS, 
                               PREGUNTAS_RRHH, PREGUNTAS_MANAGER) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);"""
            cursor.executemany(query_scoring, datos_para_scoring)
            print("  -> OK")

        if datos_para_soft_skills:
            print(f"2/3 - Insertando {len(datos_para_soft_skills)} registros en VALORACION_SOFT_SKILL...")
            query_soft_skills = "INSERT INTO VALORACION_SOFT_SKILL (ID_CANDIDATO, ID_SOFT_SKILL, VALORACION, MARCA_IA) VALUES (%s, %s, %s, %s);"
            cursor.executemany(query_soft_skills, datos_para_soft_skills)
            print("  -> OK")

        if datos_para_hard_skills:
            print(f"3/3 - Insertando {len(datos_para_hard_skills)} registros en VALORACION_HARD_SKILL...")
            query_hard_skills = "INSERT INTO VALORACION_HARD_SKILL (PUESTO, ID_CANDIDATO, ID_HARD_SKILL, VALORACION, MARCA_IA) VALUES (%s, %s, %s, %s, %s);"
            cursor.executemany(query_hard_skills, datos_para_hard_skills)
            print("  -> OK")

        conn.commit()
        print("\n✅ Transacción completada. Todos los datos han sido guardados.")

    except Error as error:
        print(f"\n❌ Error durante la transacción masiva: {error}")
        if conn:
            print("  -> Revertiendo cambios (rollback)...")
            conn.rollback()
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
            print("  -> Conexión a la base de datos cerrada.")

def guardar_evaluacion_en_db(evaluacion: dict, id_candidato: int, nombre_vacante: str):
    """
    Guarda la evaluación completa (scores, justificación y preguntas) en la BD.
    Es transaccional, evita duplicados y normaliza los nombres de las skills.
    """
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        conn.autocommit = False
        cursor = conn.cursor()

        # --- COMPROBACIÓN INICIAL ---
        query_check = "SELECT COUNT(*) FROM SCORING WHERE PUESTO = %s AND ID_CANDIDATO = %s;"
        cursor.execute(query_check, (nombre_vacante, id_candidato))
        count = cursor.fetchone()[0]

        if count > 0:
            print(f"⚠️  AVISO: Ya existe una evaluación para el candidato {id_candidato} en el puesto '{nombre_vacante}'. Se omite la inserción.")
            return

        # --- Si la comprobación pasa, la ejecución continúa ---

        # 1. Escribir en la tabla SCORING (con scores parciales y preguntas)
        print("1/3 - Insertando en la tabla SCORING...")
        query_scoring = """
            INSERT INTO SCORING
            (PUESTO, ID_CANDIDATO, SCORE, Justificacion,
             SCORE_FORMACION, SCORE_EXPERIENCIA, SCORE_SOFT_SKILL, SCORE_HARD_SKILL,
             PREGUNTAS_TECNICAS, PREGUNTAS_RRHH, PREGUNTAS_MANAGER)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        puntuaciones_parciales = evaluacion.get('puntuaciones_parciales', {})

        datos_scoring = (
            nombre_vacante,
            id_candidato,
            evaluacion.get('puntuacion_global'),
            evaluacion.get('justificacion'),
            puntuaciones_parciales.get('formacion'),
            puntuaciones_parciales.get('experiencia'),
            puntuaciones_parciales.get('soft_skills'),
            puntuaciones_parciales.get('skills_tecnicas'),
            json.dumps(evaluacion.get('PREGUNTAS_TECNICAS', []), ensure_ascii=False), # <-- AÑADIDO
            json.dumps(evaluacion.get('PREGUNTAS_RRHH', []), ensure_ascii=False),     # <-- AÑADIDO
            json.dumps(evaluacion.get('PREGUNTAS_MANAGER', []), ensure_ascii=False)  # <-- AÑADIDO
        )
        cursor.execute(query_scoring, datos_scoring)
        print("   -> OK")

        # 2. Comprobar e Insertar en VALORACION_SOFT_SKILL
        print("2/3 - Comprobando y/o insertando en la tabla VALORACION_SOFT_SKILL...")
        query_check_soft = "SELECT COUNT(*) FROM VALORACION_SOFT_SKILL WHERE ID_CANDIDATO = %s;"
        cursor.execute(query_check_soft, (id_candidato,))
        soft_skills_count = cursor.fetchone()[0]

        if soft_skills_count == 0:
            print("   -> No existen soft skills previas. Insertando nuevas valoraciones...")
            cursor.execute("SELECT ID_SOFT_SKILL, SOFT_SKILL FROM CAT_SOFT_SKILL;")
            mapa_soft_skill_id = {normalizar_texto(nombre): id_skill for id_skill, nombre in cursor.fetchall()}
            datos_soft_skills = []
            for nombre_skill, valoracion in evaluacion.get('match_soft_skills', {}).items():
                id_skill = mapa_soft_skill_id.get(normalizar_texto(nombre_skill))
                if id_skill:
                    datos_soft_skills.append((id_candidato, id_skill, valoracion, 0))
                    datos_soft_skills.append((id_candidato, id_skill, valoracion, 1))

            if datos_soft_skills:
                query_soft_skills = "INSERT INTO VALORACION_SOFT_SKILL (ID_CANDIDATO, ID_SOFT_SKILL, VALORACION, MARCA_IA) VALUES (%s, %s, %s, %s);"
                cursor.executemany(query_soft_skills, datos_soft_skills)
                print(f"   -> OK ({len(datos_soft_skills)} filas insertadas)")
        else:
            print(f"   -> OK. Ya existen valoraciones de soft skills para este candidato. Se omite la inserción.")

        # 3. Escribir en la tabla VALORACION_HARD_SKILL
        print("3/3 - Insertando en la tabla VALORACION_HARD_SKILL...")
        cursor.execute("SELECT ID_HARD_SKILL, HARD_SKILL FROM CAT_HARD_SKILL WHERE PUESTO = %s;", (nombre_vacante,))
        mapa_hard_skill_id = {normalizar_texto(nombre): id_skill for id_skill, nombre in cursor.fetchall()}
        datos_hard_skills = []
        for nombre_skill, valoracion in evaluacion.get('match_skills_tecnicas', {}).items():
            id_skill = mapa_hard_skill_id.get(normalizar_texto(nombre_skill))
            if id_skill:
                datos_hard_skills.append((nombre_vacante, id_candidato, id_skill, valoracion, 0))
                datos_hard_skills.append((nombre_vacante, id_candidato, id_skill, valoracion, 1))

        if datos_hard_skills:
            query_hard_skills = "INSERT INTO VALORACION_HARD_SKILL (PUESTO, ID_CANDIDATO, ID_HARD_SKILL, VALORACION, MARCA_IA) VALUES (%s, %s, %s, %s, %s);"
            cursor.executemany(query_hard_skills, datos_hard_skills)
            print(f"   -> OK ({len(datos_hard_skills)} filas)")

        conn.commit()
        print("\n✅ Transacción completada. Todos los datos han sido guardados.")

    except Error as error:
        print(f"\n❌ Error durante la transacción: {error}")
        if conn:
            print("   -> Revertiendo cambios (rollback)...")
            conn.rollback()
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
            print("   -> Conexión a la base de datos cerrada.")
    
async def orquestador_reevaluar_puesto_modificado(nombre_vacante: str):
    """
    Orquesta la re-evaluación completa de un puesto que ha sido modificado.
    Primero borra todas las evaluaciones existentes para ese puesto y luego
    lanza el proceso de evaluación contra todos los candidatos.
    """
    print(f"\n{'#'*25} INICIO PIPELINE: RE-EVALUACIÓN DEL PUESTO '{nombre_vacante}' {'#'*25}")

    # --- PASO 1: BORRAR DATOS ANTIGUOS ---
    print(f"\n--- Fase 1/2: Limpiando datos de evaluaciones previas... ---")
    _eliminar_evaluaciones_por_puesto(nombre_vacante)

    # --- PASO 2: RE-EVALUAR (REUTILIZANDO LA LÓGICA EXISTENTE) ---
    print(f"\n--- Fase 2/2: Lanzando nueva evaluación completa... ---")
    # Reutilizamos completamente la función original. ¡Máxima eficiencia!
    await (orquestador_evaluar_puesto_nuevo_optimizado(nombre_vacante))

    print(f"\n{'#'*25} FIN PIPELINE: RE-EVALUACIÓN COMPLETADA {'#'*25}")

async def orquestador_evaluar_puesto_nuevo_optimizado(nombre_vacante: str):
    """
    Toma una vacante y la evalúa contra todos los candidatos disponibles
    de forma optimizada, minimizando las llamadas a la base de datos.
    """
    print(f"\n{'='*20} INICIANDO WORKFLOW OPTIMIZADO: EVALUAR PUESTO '{nombre_vacante}' {'='*20}")

    # 1. Obtenemos los requisitos del puesto UNA SOLA VEZ
    requisitos_puesto = obtener_requisitos_puesto(nombre_vacante)

    
    
    if not requisitos_puesto:
        print(f"🛑 Proceso detenido. No se pudieron obtener los requisitos para el puesto '{nombre_vacante}'.")
        return

    # 2. Obtenemos los datos de TODOS los candidatos UNA SOLA VEZ
    todos_los_candidatos = obtener_datos_todos_los_candidatos()
    
    
    
    if not todos_los_candidatos:
        print("🛑 Proceso detenido. No se encontraron candidatos para evaluar.")
        return
    semaphore = asyncio.Semaphore(MAX_CONSULTAS_CONCURRENTES)
    tasks = []
    # 3. Iteramos sobre los candidatos (ya en memoria) y ejecutamos la evaluación
    for i, (id_candidato, datos_candidato) in enumerate(todos_los_candidatos.items()):
        for evaluador in EVALUADORES.keys():
            task = evaluar_candidato_con_llm(semaphore,id_candidato ,datos_candidato, requisitos_puesto, evaluador.format(nombre_vacante=nombre_vacante))
            tasks.append(task)
        #print(f"\n--- ({i+1}/{num_candidatos}) Evaluando al candidato con ID: {id_candidato} ---")
    all_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 4. Procesamos y guardamos todas las evaluaciones

    evaluacion_consensuada = _procesar_evaluaciones(all_results)
    guardar_evaluaciones_masivamente(evaluacion_consensuada, nombre_vacante)
    print(f"\n{'='*20} WORKFLOW COMPLETADO: EVALUACIÓN")
    
    


