import os
import mysql.connector
import json
import re
from flask import Flask, jsonify, request, render_template
from dotenv import load_dotenv
from flask_cors import CORS
import utils
import asyncio

# Cargar variables de entorno desde el archivo .env
load_dotenv()

app = Flask(__name__)
# Habilitar CORS para permitir peticiones desde el frontend
CORS(app)

# --- Configuración de la conexión a la base de datos ---
def get_db_connection():
    """Establece la conexión con la base de datos MySQL."""
    try:
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASS')
        )
        return conn
    except mysql.connector.Error as e:
        print(f"Error al conectar a la base de datos MySQL: {e}")
        return None

# --- Rutas de la API ---

@app.route('/')
def index():
    """Sirve el archivo HTML principal."""
    return render_template('CVision.html')

@app.route('/api/puestos', methods=['GET'])
def get_puestos():
    """Recupera la lista de puestos predefinidos de la base de datos."""
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor(dictionary=True) as cur:
                cur.execute("SELECT PUESTO as id, PUESTO as titulo, DESCRIPCION_CORTA, MISION, VACANTE FROM PUESTOS_PREDEFINIDOS ORDER BY PUESTO;")
                puestos = cur.fetchall()
            return jsonify(puestos)
        except mysql.connector.Error as e:
            print(f"Error al ejecutar la consulta: {e}")
            return jsonify({"error": "Error interno del servidor"}), 500
        finally:
            conn.close()
    return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

@app.route('/api/puesto/<path:puesto_id>', methods=['GET'])
def get_puesto_detail(puesto_id):
    """Recupera los detalles completos de un puesto específico, incluyendo ponderaciones."""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500
    
    try:
        with conn.cursor(dictionary=True) as cur:
            sql = """
                SELECT PUESTO, DESCRIPCION_CORTA, DESCRIPCION_LARGA, MISION, COMPETENCIAS,
                       POND_FORMACION, POND_EXPERIENCIA, POND_SOFT_SKILL, POND_HARD_SKILL
                FROM PUESTOS_PREDEFINIDOS 
                WHERE PUESTO = %s;
            """
            cur.execute(sql, (puesto_id,))
            puesto = cur.fetchone()

            if not puesto:
                return jsonify({"error": "Puesto no encontrado"}), 404
            
            puesto['COMPETENCIAS'] = parse_json_field(puesto.get('COMPETENCIAS'))
            
            return jsonify(puesto)

    except mysql.connector.Error as e:
        print(f"Error al recuperar el detalle del puesto: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500
    finally:
        if conn and conn.is_connected():
            conn.close()

@app.route('/api/puestos', methods=['POST'])
async def create_puesto():
    """Crea un nuevo puesto en la base de datos, incluyendo ponderaciones."""
    data = request.get_json()
    
    required_fields = ['puesto', 'descripcion_corta', 'descripcion_larga', 'mision', 'competencias']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Faltan datos en la petición"}), 400

    competencias_json = json.dumps(data['competencias'])

    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                sql = """
                    INSERT INTO PUESTOS_PREDEFINIDOS 
                    (PUESTO, DESCRIPCION_CORTA, DESCRIPCION_LARGA, MISION, COMPETENCIAS,
                     POND_FORMACION, POND_EXPERIENCIA, POND_SOFT_SKILL, POND_HARD_SKILL) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                """
                cur.execute(sql, (
                    data['puesto'],
                    data['descripcion_corta'],
                    data['descripcion_larga'],
                    data['mision'],
                    competencias_json,
                    data.get('pond_formacion', 0.25),
                    data.get('pond_experiencia', 0.25),
                    data.get('pond_soft_skill', 0.25),
                    data.get('pond_hard_skill', 0.25)
                ))
                conn.commit()
                await utils.orquestador_evaluar_puesto_nuevo_optimizado(data['puesto'])
            return jsonify({"mensaje": "Puesto creado con éxito"}), 201
        except mysql.connector.Error as e:
            print(f"Error al insertar en la base de datos: {e}")
            conn.rollback()
            return jsonify({"error": "Error interno del servidor al guardar los datos"}), 500
        finally:
            conn.close()
    
    return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

@app.route('/api/puesto/<path:puesto_id>', methods=['PUT'])
async def update_puesto(puesto_id):
    """Actualiza un puesto predefinido existente."""
    data = request.get_json()
    
    required_fields = ['puesto', 'descripcion_corta', 'descripcion_larga', 'mision', 'competencias']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Faltan datos en la petición"}), 400

    competencias_json = json.dumps(data['competencias'])

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500
    
    try:
        with conn.cursor() as cur:
            sql = """
                UPDATE PUESTOS_PREDEFINIDOS SET
                PUESTO = %s,
                DESCRIPCION_CORTA = %s,
                DESCRIPCION_LARGA = %s,
                MISION = %s,
                COMPETENCIAS = %s
                WHERE PUESTO = %s;
            """
            cur.execute(sql, (
                data['puesto'],
                data['descripcion_corta'],
                data['descripcion_larga'],
                data['mision'],
                competencias_json,
                puesto_id
            ))
            conn.commit()
            if cur.rowcount == 0:
                return jsonify({"error": "Puesto no encontrado para actualizar"}), 404
        await utils.orquestador_reevaluar_puesto_modificado(data['puesto'])
        return jsonify({"mensaje": "Puesto actualizado con éxito"}), 200
    except mysql.connector.Error as e:
        print(f"Error al actualizar el puesto: {e}")
        conn.rollback()
        return jsonify({"error": "Error interno del servidor al actualizar"}), 500
    finally:
        if conn and conn.is_connected():
            conn.close()

@app.route('/api/puesto/<path:puesto_id>/ponderaciones', methods=['PUT'])
def update_ponderaciones(puesto_id):
    """Actualiza las ponderaciones para un puesto específico."""
    data = request.get_json()
    required_fields = ['pond_formacion', 'pond_experiencia', 'pond_soft_skill', 'pond_hard_skill']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Faltan datos de ponderación"}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

    try:
        with conn.cursor() as cur:
            sql = """
                UPDATE PUESTOS_PREDEFINIDOS SET
                POND_FORMACION = %s,
                POND_EXPERIENCIA = %s,
                POND_SOFT_SKILL = %s,
                POND_HARD_SKILL = %s
                WHERE PUESTO = %s;
            """
            cur.execute(sql, (
                data['pond_formacion'],
                data['pond_experiencia'],
                data['pond_soft_skill'],
                data['pond_hard_skill'],
                puesto_id
            ))
            conn.commit()
            if cur.rowcount == 0:
                return jsonify({"error": "Puesto no encontrado"}), 404
        return jsonify({"mensaje": "Ponderaciones actualizadas con éxito"}), 200
    except mysql.connector.Error as e:
        print(f"Error al actualizar ponderaciones: {e}")
        conn.rollback()
        return jsonify({"error": "Error interno del servidor"}), 500
    finally:
        if conn and conn.is_connected():
            conn.close()


@app.route('/api/puesto/<path:puesto_id>/vacante', methods=['POST'])
def update_vacante_status(puesto_id):
    """Actualiza el estado de la vacante para un puesto (0 o 1)."""
    data = request.get_json()
    new_status = data.get('vacante')

    if new_status not in [0, 1]:
        return jsonify({"error": "El estado de la vacante debe ser 0 o 1"}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

    try:
        with conn.cursor() as cur:
            sql = "UPDATE PUESTOS_PREDEFINIDOS SET VACANTE = %s WHERE PUESTO = %s;"
            cur.execute(sql, (new_status, puesto_id))
            conn.commit()
            if cur.rowcount == 0:
                return jsonify({"error": "Puesto no encontrado"}), 404
        return jsonify({"mensaje": f"Vacante para '{puesto_id}' actualizada a {new_status}"}), 200
    except mysql.connector.Error as e:
        print(f"Error al actualizar la vacante: {e}")
        conn.rollback()
        return jsonify({"error": "Error interno del servidor al actualizar la vacante"}), 500
    finally:
        if conn and conn.is_connected():
            conn.close()


@app.route('/api/vacante/<path:puesto_id>/candidatos', methods=['GET'])
def get_vacante_candidatos(puesto_id):
    """
    Recupera la lista de candidatos para una vacante, calculando
    la puntuación final en base a las ponderaciones del puesto.
    """
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500
    
    try:
        with conn.cursor(dictionary=True) as cur:
            sql_scoring = """
                SELECT 
                    s.ID_CANDIDATO, 
                    c.nombre_completo, 
                    c.ciudad_residencia,
                    s.APTO,
                    (
                        pp.POND_FORMACION * (s.SCORE_FORMACION * 10) +
                        pp.POND_EXPERIENCIA * (s.SCORE_EXPERIENCIA * 10) +
                        pp.POND_SOFT_SKILL * (s.SCORE_SOFT_SKILL * 10) +
                        pp.POND_HARD_SKILL * (s.SCORE_HARD_SKILL * 10)
                    ) AS calculated_score
                FROM SCORING s
                JOIN CANDIDATOS c ON s.ID_CANDIDATO = c.ID_CANDIDATO
                JOIN PUESTOS_PREDEFINIDOS pp ON s.PUESTO = pp.PUESTO
                WHERE s.PUESTO = %s
                ORDER BY calculated_score DESC;
            """
            cur.execute(sql_scoring, (puesto_id,))
            candidatos = cur.fetchall()

            ranked_candidatos = [
                {
                    "id": cand["ID_CANDIDATO"],
                    "nombreCompleto": cand["nombre_completo"],
                    "localidad": cand["ciudad_residencia"],
                    "score": round(cand["calculated_score"]) if cand["calculated_score"] is not None else 0,
                    "apto": cand["APTO"]
                }
                for cand in candidatos
            ]
            return jsonify(ranked_candidatos)

    except mysql.connector.Error as e:
        print(f"Error al ejecutar la consulta de candidatos: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500
    finally:
        if conn and conn.is_connected():
            conn.close()

def parse_json_field(data):
    """Parsea un campo de texto que debería contener JSON, con manejo de errores."""
    if not data or not isinstance(data, str):
        return []
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return []

@app.route('/api/candidato/<int:candidato_id>/reporte/<path:puesto_id>', methods=['GET'])
def get_candidato_report(candidato_id, puesto_id):
    """
    Recupera el informe detallado de un candidato para un puesto específico.
    """
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500
        
    try:
        report = {}
        # MODIFICACIÓN: Se usa un cursor con buffer para evitar errores de 'Unread result'.
        with conn.cursor(dictionary=True, buffered=True) as cur:
            # 0. Obtener scores, justificación, preguntas y si es APTO
            sql_score = """
                SELECT SCORE, Justificacion, PREGUNTAS_TECNICAS, PREGUNTAS_RRHH, PREGUNTAS_MANAGER, APTO,
                       SCORE_FORMACION, SCORE_EXPERIENCIA, SCORE_SOFT_SKILL, SCORE_HARD_SKILL
                FROM SCORING 
                WHERE ID_CANDIDATO = %s AND PUESTO = %s;
            """
            cur.execute(sql_score, (candidato_id, puesto_id))
            score_data = cur.fetchone()

            if score_data:
                # Recalcular el score total para asegurar consistencia
                sql_pond = "SELECT POND_FORMACION, POND_EXPERIENCIA, POND_SOFT_SKILL, POND_HARD_SKILL FROM PUESTOS_PREDEFINIDOS WHERE PUESTO = %s;"
                cur.execute(sql_pond, (puesto_id,))
                pond_data = cur.fetchone()
                
                total_score = 0
                if pond_data:
                    total_score = (
                        (float(pond_data.get('POND_FORMACION', 0) or 0) * (float(score_data.get('SCORE_FORMACION', 0) or 0) * 10)) +
                        (float(pond_data.get('POND_EXPERIENCIA', 0) or 0) * (float(score_data.get('SCORE_EXPERIENCIA', 0) or 0) * 10)) +
                        (float(pond_data.get('POND_SOFT_SKILL', 0) or 0) * (float(score_data.get('SCORE_SOFT_SKILL', 0) or 0) * 10)) +
                        (float(pond_data.get('POND_HARD_SKILL', 0) or 0) * (float(score_data.get('SCORE_HARD_SKILL', 0) or 0) * 10))
                    )
                
                report['score'] = round(total_score)
                report['apto'] = score_data['APTO']
                report['score_formacion'] = float(score_data.get('SCORE_FORMACION', 0) or 0)
                report['score_experiencia'] = float(score_data.get('SCORE_EXPERIENCIA', 0) or 0)
                report['score_soft_skill'] = float(score_data.get('SCORE_SOFT_SKILL', 0) or 0)
                report['score_hard_skill'] = float(score_data.get('SCORE_HARD_SKILL', 0) or 0)
            else:
                 report.update({ 'score': None, 'apto': None, 'score_formacion': 0, 'score_experiencia': 0, 'score_soft_skill': 0, 'score_hard_skill': 0})

            justificaciones = []
            if score_data and score_data.get('Justificacion') and isinstance(score_data['Justificacion'], str):
                justificacion_str = score_data['Justificacion']
                matches = re.findall(r'-\s*(.*?):\s*(.*?)(?=\s*-\s*[^:]+:|$)', justificacion_str, re.DOTALL)
                for match in matches:
                    evaluador = match[0].strip()
                    texto = match[1].strip()
                    if evaluador and texto:
                        justificaciones.append({'evaluador': evaluador, 'texto': texto})
            
            report['justificacion'] = justificaciones
            
            report['preguntas_entrevista'] = {
                'tecnicas': parse_json_field(score_data.get('PREGUNTAS_TECNICAS')) if score_data else [],
                'rrhh': parse_json_field(score_data.get('PREGUNTAS_RRHH')) if score_data else [],
                'manager': parse_json_field(score_data.get('PREGUNTAS_MANAGER')) if score_data else []
            }

            # 1. Obtener datos personales del candidato (incluyendo referencias)
            sql_personal = """
                SELECT 
                    nombre_completo, correo_electronico, numero_telefono,
                    fecha_de_nacimiento, ciudad_residencia, enlace_perfil,
                    Otros, REF_INTERNAS, REF_EXTERNAS
                FROM CANDIDATOS WHERE ID_CANDIDATO = %s;
            """
            cur.execute(sql_personal, (candidato_id,))
            personal_data = cur.fetchone()
            if not personal_data:
                return jsonify({"error": "Candidato no encontrado"}), 404
            
            report['nombre'] = personal_data['nombre_completo']
            report['email'] = personal_data['correo_electronico']
            report['telefono'] = personal_data['numero_telefono']
            report['fecha_nacimiento'] = str(personal_data['fecha_de_nacimiento']) if personal_data.get('fecha_de_nacimiento') else None
            report['ciudad'] = personal_data['ciudad_residencia']
            report['linkedin'] = personal_data['enlace_perfil']
            report['ref_internas'] = personal_data['REF_INTERNAS']
            report['ref_externas'] = personal_data['REF_EXTERNAS']

            otros_json = {}
            if personal_data.get('Otros'):
                try:
                    otros_json = json.loads(personal_data['Otros'])
                except (json.JSONDecodeError, TypeError):
                    print(f"Advertencia: El campo 'Otros' para el candidato {candidato_id} no es un JSON válido.")

            report['formacion'] = otros_json.get('formacion', [])
            report['miscelanea_formacion'] = otros_json.get('miscelanea', '')
            report['trayectoria_profesional'] = otros_json.get('trayectoria_profesional', [])
            report['idiomas'] = otros_json.get('idiomas', [])

            # 2. Obtener Hard Skills
            sql_hard = """
                SELECT vhs.VALORACION, chs.HARD_SKILL, chs.ID_HARD_SKILL
                FROM VALORACION_HARD_SKILL vhs
                JOIN CAT_HARD_SKILL chs ON vhs.ID_HARD_SKILL = chs.ID_HARD_SKILL AND vhs.PUESTO = chs.PUESTO
                WHERE vhs.ID_CANDIDATO = %s AND vhs.PUESTO = %s AND vhs.MARCA_IA = 0;
            """
            cur.execute(sql_hard, (candidato_id, puesto_id))
            report['hard_skills'] = cur.fetchall()

            # 3. Obtener Soft Skills
            sql_soft = """
                SELECT vss.VALORACION, css.SOFT_SKILL, css.ID_SOFT_SKILL
                FROM VALORACION_SOFT_SKILL vss
                JOIN CAT_SOFT_SKILL css ON vss.ID_SOFT_SKILL = css.ID_SOFT_SKILL
                WHERE vss.ID_CANDIDATO = %s AND vss.MARCA_IA = 0;
            """
            cur.execute(sql_soft, (candidato_id,))
            report['soft_skills'] = cur.fetchall()

            # 4. Obtener Valoración de Perfil y Observaciones
            sql_otros = "SELECT VAL_PERFIL, OBSERVACIONES FROM CANDIDATO_PUESTO_OTROS WHERE ID_CANDIDATO = %s AND PUESTO = %s;"
            cur.execute(sql_otros, (candidato_id, puesto_id))
            otros_data = cur.fetchone()
            report['valoracion_perfil'] = otros_data['VAL_PERFIL'] if otros_data else ''
            report['observaciones'] = otros_data['OBSERVACIONES'] if otros_data else ''

        return jsonify(report)
        
    except mysql.connector.Error as e:
        print(f"Error al construir el informe del candidato: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500
    finally:
        if conn and conn.is_connected():
            conn.close()

@app.route('/api/candidatos/count', methods=['GET'])
def get_candidatos_count():
    """Recupera el número total de candidatos."""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500
    
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(ID_CANDIDATO) FROM CANDIDATOS;")
            count = cur.fetchone()[0]
        return jsonify({"total": count})
    except mysql.connector.Error as e:
        print(f"Error al contar candidatos: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500
    finally:
        if conn and conn.is_connected():
            conn.close()

# --- NUEVAS RUTAS PARA GUARDAR DATOS DEL INFORME ---

@app.route('/api/candidato/<int:candidato_id>/reporte/<path:puesto_id>', methods=['PUT'])
def save_candidato_report(candidato_id, puesto_id):
    """Guarda todos los datos modificables del informe de un candidato."""
    data = request.get_json()
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

    try:
        with conn.cursor() as cur:
            # 1. Actualizar APTO en SCORING
            if 'apto' in data and data['apto'] != 'no_definido':
                cur.execute("UPDATE SCORING SET APTO = %s WHERE ID_CANDIDATO = %s AND PUESTO = %s;",
                            (data['apto'], candidato_id, puesto_id))

            # 2. Actualizar datos personales y JSON 'Otros' en CANDIDATOS
            if 'personal' in data:
                personal = data['personal']
                otros_json = json.dumps({
                    "formacion": personal.get('formacion', []),
                    "trayectoria_profesional": personal.get('trayectoria_profesional', []),
                    "idiomas": personal.get('idiomas', []),
                    "miscelanea": personal.get('miscelanea', '')
                })
                cur.execute("""
                    UPDATE CANDIDATOS SET
                        nombre_completo = %s, correo_electronico = %s, numero_telefono = %s,
                        fecha_de_nacimiento = %s, ciudad_residencia = %s, enlace_perfil = %s,
                        REF_INTERNAS = %s, REF_EXTERNAS = %s, Otros = %s
                    WHERE ID_CANDIDATO = %s;
                """, (
                    personal.get('nombre'), personal.get('email'), personal.get('telefono'),
                    personal.get('fecha_nacimiento'), personal.get('ciudad'), personal.get('linkedin'),
                    personal.get('ref_internas'), personal.get('ref_externas'), otros_json,
                    candidato_id
                ))
            
            # 3. Actualizar/Insertar en CANDIDATO_PUESTO_OTROS
            if 'otros_puesto' in data:
                otros = data['otros_puesto']
                cur.execute("""
                    INSERT INTO CANDIDATO_PUESTO_OTROS (ID_CANDIDATO, PUESTO, VAL_PERFIL, OBSERVACIONES)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE VAL_PERFIL = VALUES(VAL_PERFIL), OBSERVACIONES = VALUES(OBSERVACIONES);
                """, (candidato_id, puesto_id, otros.get('valoracion_perfil'), otros.get('observaciones')))
            
            # 4. Actualizar VALORACION_SOFT_SKILL
            if 'soft_skills' in data:
                for skill in data['soft_skills']:
                    cur.execute("""
                        UPDATE VALORACION_SOFT_SKILL SET VALORACION = %s
                        WHERE ID_CANDIDATO = %s AND ID_SOFT_SKILL = %s AND MARCA_IA = 0;
                    """, (skill['VALORACION'], candidato_id, skill['ID_SOFT_SKILL']))

            # 5. Actualizar VALORACION_HARD_SKILL
            if 'hard_skills' in data:
                for skill in data['hard_skills']:
                    cur.execute("""
                        UPDATE VALORACION_HARD_SKILL SET VALORACION = %s
                        WHERE ID_CANDIDATO = %s AND PUESTO = %s AND ID_HARD_SKILL = %s AND MARCA_IA = 0;
                    """, (skill['VALORACION'], candidato_id, puesto_id, skill['ID_HARD_SKILL']))

            conn.commit()
            return jsonify({"mensaje": "Informe guardado con éxito"}), 200

    except mysql.connector.Error as e:
        conn.rollback()
        print(f"Error al guardar el informe del candidato: {e}")
        return jsonify({"error": "Error interno del servidor al guardar el informe"}), 500
    finally:
        if conn and conn.is_connected():
            conn.close()

if __name__ == '__main__':
    app.run(debug=True)

