import psycopg2
from psycopg2 import extras


class CaseDB:
    def __init__(self, dbname, user, password, host="localhost", port="5432"):
        self.dbname = dbname
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.conn = None

    def connect(self):
        try:
            self.conn = psycopg2.connect(
                dbname=self.dbname,
                user=self.user,
                password=self.password,
                host=self.host,
                port=self.port
            )
            print("Conexión a PostgreSQL establecida con éxito.")
        except Exception as e:
            print(f"Error al conectar a PostgreSQL: {e}")
            self.conn = None

    def close(self):
        """Cierra la conexión a la base de datos."""
        if self.conn:
            self.conn.close()
            print("Conexión a PostgreSQL cerrada.")

    def fetch_data(self, query, params=None, fetch_one=False):
        """Ejecuta una consulta SELECT y devuelve los resultados como diccionarios."""
        if not self.conn:
            self.connect()
            if not self.conn:
                return []
        try:
            with self.conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                cur.execute(query, params)
                if fetch_one:
                    return cur.fetchone()
                return cur.fetchall()
        except Exception as e:
            print(f"Error al ejecutar la consulta: {e}")
            return []

    def execute_transaction(self, query, params=None):
        """Ejecuta una transacción (INSERT/UPDATE/DELETE) y realiza commit."""
        if not self.conn:
            self.connect()
            if not self.conn:
                return False
        try:
            with self.conn.cursor() as cur:
                cur.execute(query, params)
                self.conn.commit()
                if query.strip().upper().startswith('INSERT'):
                    return cur.fetchone()[0] if cur.rowcount > 0 else True
                return True
        except Exception as e:
            print(f"Error en la transacción: {e}")
            self.conn.rollback()
            return False

    # --- Métodos de Consulta ---

    def get_carga_temporal(self):
        """Obtiene todos los registros de la tabla carga_temporal."""
        query = """
            SELECT
                ano_registro,
                id_producto,
                titulo,
                tipo_producto,
                fecha_inicio,
                fecha_termino,
                institucion,
                nombre_estudiante,
                tipo_responsable,
                responsable,
                colaboradores
            FROM carga_temporal
            ORDER BY ano_registro DESC;
        """
        return self.fetch_data(query)

    def get_all_tesis(self):
        """
        Obtiene todas las tesis con sus datos relacionados.
        Usa STRING_AGG para colapsar múltiples colaboradores en una sola fila
        y evitar duplicados por tesis.
        """
        query = """
            SELECT
                t.id_producto,
                t.ano_registro,
                t.titulo,
                t.tipo_producto,
                TO_CHAR(t.fecha_inicio, 'DD/MM/YYYY') AS fecha_inicio,
                TO_CHAR(t.fecha_final,  'DD/MM/YYYY') AS fecha_final,
                t.institucion,
                MAX(e.nombre_estudiante)                        AS nombre_estudiante,
                MAX(r.tipo_responsable)                         AS tipo_responsable,
                MAX(r.nombre_responsable)                       AS nombre_responsable,
                STRING_AGG(DISTINCT c.nombre_colaborador, ', ') AS nombre_colaborador
            FROM tesis t
            LEFT JOIN tesis_estudiante  te ON t.id_producto    = te.id_producto
            LEFT JOIN estudiante         e  ON te.id_estudiante = e.id_estudiante
            LEFT JOIN tesis_responsable  tr ON t.id_producto    = tr.id_producto
            LEFT JOIN responsable        r  ON tr.id_responsable= r.id_responsable
            LEFT JOIN tesis_colaborador  tc ON t.id_producto    = tc.id_producto
            LEFT JOIN colaborador        c  ON tc.id_colaborador= c.id_colaborador
            GROUP BY
                t.id_producto,
                t.ano_registro,
                t.titulo,
                t.tipo_producto,
                t.fecha_inicio,
                t.fecha_final,
                t.institucion
            ORDER BY t.ano_registro DESC;
        """
        return self.fetch_data(query)

    def get_tesis_by_id(self, id_producto):
        """Obtiene una tesis específica por su ID."""
        query = """
            SELECT
                t.id_producto,
                t.ano_registro,
                t.titulo,
                t.tipo_producto,
                TO_CHAR(t.fecha_inicio, 'DD/MM/YYYY') AS fecha_inicio,
                TO_CHAR(t.fecha_final,  'DD/MM/YYYY') AS fecha_final,
                t.institucion,
                MAX(e.nombre_estudiante)                        AS nombre_estudiante,
                MAX(r.tipo_responsable)                         AS tipo_responsable,
                MAX(r.nombre_responsable)                       AS nombre_responsable,
                STRING_AGG(DISTINCT c.nombre_colaborador, ', ') AS nombre_colaborador
            FROM tesis t
            LEFT JOIN tesis_estudiante  te ON t.id_producto    = te.id_producto
            LEFT JOIN estudiante         e  ON te.id_estudiante = e.id_estudiante
            LEFT JOIN tesis_responsable  tr ON t.id_producto    = tr.id_producto
            LEFT JOIN responsable        r  ON tr.id_responsable= r.id_responsable
            LEFT JOIN tesis_colaborador  tc ON t.id_producto    = tc.id_producto
            LEFT JOIN colaborador        c  ON tc.id_colaborador= c.id_colaborador
            WHERE t.id_producto = %s
            GROUP BY
                t.id_producto,
                t.ano_registro,
                t.titulo,
                t.tipo_producto,
                t.fecha_inicio,
                t.fecha_final,
                t.institucion;
        """
        return self.fetch_data(query, params=(id_producto,), fetch_one=True)

    # --- Métodos para Poblar Formularios ---

    def get_form_options(self):
        """Obtiene todos los listados para los desplegables del formulario."""
        options = {}
        options['estudiantes']   = self.fetch_data(
            "SELECT id_estudiante, nombre_estudiante FROM estudiante ORDER BY nombre_estudiante;"
        )
        options['responsables']  = self.fetch_data(
            "SELECT id_responsable, nombre_responsable, tipo_responsable FROM responsable ORDER BY nombre_responsable;"
        )
        options['colaboradores'] = self.fetch_data(
            "SELECT id_colaborador, nombre_colaborador FROM colaborador ORDER BY nombre_colaborador;"
        )
        options['tipo_producto'] = self.fetch_data(
            "SELECT DISTINCT tipo_producto FROM tesis ORDER BY tipo_producto;"
        )
        options['instituciones'] = self.fetch_data(
            "SELECT DISTINCT institucion FROM tesis ORDER BY institucion;"
        )
        return options

    # --- Métodos de Registro ---

    def _get_or_create_estudiante(self, nombre):
        """Busca un estudiante por nombre o lo crea si no existe. Retorna su ID."""
        row = self.fetch_data(
            "SELECT id_estudiante FROM estudiante WHERE nombre_estudiante = %s LIMIT 1;",
            (nombre,), fetch_one=True
        )
        if row:
            return row['id_estudiante']
        return self.execute_transaction(
            "INSERT INTO public.estudiante (nombre_estudiante) VALUES (%s) RETURNING id_estudiante;",
            (nombre,)
        )

    def _get_or_create_responsable(self, nombre):
        """Busca un responsable por nombre o lo crea si no existe. Retorna su ID."""
        row = self.fetch_data(
            "SELECT id_responsable FROM responsable WHERE nombre_responsable = %s LIMIT 1;",
            (nombre,), fetch_one=True
        )
        if row:
            return row['id_responsable']
        return self.execute_transaction(
            "INSERT INTO public.responsable (nombre_responsable) VALUES (%s) RETURNING id_responsable;",
            (nombre,)
        )

    def _get_or_create_colaborador(self, nombre):
        """Busca un colaborador por nombre o lo crea si no existe. Retorna su ID."""
        row = self.fetch_data(
            "SELECT id_colaborador FROM colaborador WHERE nombre_colaborador = %s LIMIT 1;",
            (nombre,), fetch_one=True
        )
        if row:
            return row['id_colaborador']
        return self.execute_transaction(
            "INSERT INTO public.colaborador (nombre_colaborador) VALUES (%s) RETURNING id_colaborador;",
            (nombre,)
        )

    def register_new_tesis(self, data):
        """
        Inserta una nueva tesis y sus relaciones.

        'data' debe ser un diccionario con las claves:
            ano_registro, titulo, tipo_producto, fecha_inicio,
            fecha_final, institucion, id_estudiante (nombre),
            id_responsable (nombre), id_colaborador (nombre, opcional)
        """
        query_tesis = """
            INSERT INTO public.tesis (
                ano_registro, titulo, tipo_producto,
                fecha_inicio, fecha_final, institucion
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id_producto;
        """
        id_producto = self.execute_transaction(query_tesis, (
            data['ano_registro'], data['titulo'], data['tipo_producto'],
            data['fecha_inicio'], data['fecha_final'], data['institucion'],
        ))

        if not isinstance(id_producto, int):
            print("Error: no se pudo insertar la tesis.")
            return None

        id_est = self._get_or_create_estudiante(data['id_estudiante'])
        self.execute_transaction(
            "INSERT INTO public.tesis_estudiante (id_producto, id_estudiante) VALUES (%s, %s);",
            (id_producto, id_est)
        )

        id_resp = self._get_or_create_responsable(data['id_responsable'])
        self.execute_transaction(
            "INSERT INTO public.tesis_responsable (id_producto, id_responsable) VALUES (%s, %s);",
            (id_producto, id_resp)
        )

        if data.get('id_colaborador'):
            id_col = self._get_or_create_colaborador(data['id_colaborador'])
            self.execute_transaction(
                "INSERT INTO public.tesis_colaborador (id_producto, id_colaborador) VALUES (%s, %s);",
                (id_producto, id_col)
            )

        return id_producto

    def register_new_estudiante(self, nombre_estudiante):
        """Inserta un nuevo estudiante y devuelve su ID."""
        query = "INSERT INTO public.estudiante (nombre_estudiante) VALUES (%s) RETURNING id_estudiante;"
        return self.execute_transaction(query, (nombre_estudiante,))

    def register_new_responsable(self, nombre_responsable, tipo_responsable):
        """Inserta un nuevo responsable y devuelve su ID."""
        query = "INSERT INTO public.responsable (nombre_responsable, tipo_responsable) VALUES (%s, %s) RETURNING id_responsable;"
        return self.execute_transaction(query, (nombre_responsable, tipo_responsable))

    def register_new_colaborador(self, nombre_colaborador):
        """Inserta un nuevo colaborador y devuelve su ID."""
        query = "INSERT INTO public.colaborador (nombre_colaborador) VALUES (%s) RETURNING id_colaborador;"
        return self.execute_transaction(query, (nombre_colaborador,))
