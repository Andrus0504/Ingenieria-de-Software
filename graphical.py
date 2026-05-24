import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from database import CaseDB


class TesisApp(tk.Tk):
    def __init__(self, db_connector):
        super().__init__()
        self.title("Sistema de Gestión de Tesis")
        self.geometry("1400x700")

        self.db = db_connector

        self.frames = {}
        self._create_main_menu()
        self._create_pages()
        self.show_frame("SearchPage")

    def _create_main_menu(self):
        """Crea la barra de navegación lateral."""
        menu_frame = tk.Frame(self, bg="#333", width=200)
        menu_frame.pack(side="left", fill="y")

        tk.Label(
            menu_frame, text="Sistema de Tesis",
            fg="white", bg="#333", font=("Arial", 14, "bold")
        ).pack(pady=20, padx=10)

        btn_style = dict(
            background="#302e2e", foreground="#ffffff",
            activebackground="#ffffff", activeforeground="#000000",
            highlightthickness=1, highlightbackground="#ffffff",
            highlightcolor="#000000", width=13, height=1,
            border=0, cursor="hand1"
        )

        tk.Button(
            menu_frame, text="🔍 Consultar Tesis",
            command=lambda: self.show_frame("SearchPage"), **btn_style
        ).pack(fill="x", pady=5, padx=10)

        tk.Button(
            menu_frame, text="➕ Registrar Tesis",
            command=lambda: self.show_frame("RegisterPage"), **btn_style
        ).pack(fill="x", pady=5, padx=10)

    def _create_pages(self):
        """Crea y registra los frames (páginas) de la aplicación."""
        container = tk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        for F in (SearchPage, RegisterPage, SuccessPage):
            page_name = F.__name__
            frame = F(parent=container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

    def show_frame(self, page_name, data=None):
        """Muestra el frame solicitado y lo trae al frente."""
        frame = self.frames[page_name]
        frame.tkraise()

        if page_name == "SuccessPage":
            frame.set_tesis_id(data)
        elif page_name == "SearchPage":
            frame.load_tesis_data()


# ─────────────────────────────────────────────
# PÁGINA: Consulta
# ─────────────────────────────────────────────
class SearchPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.panel_visible = False
        self.all_data = []  # Cache de todos los datos para filtrar

        # ── Encabezado: título | barra de búsqueda | botón tablas ──
        header = tk.Frame(self)
        header.pack(fill="x", pady=(10, 0), padx=10)

        tk.Label(header, text="Consulta de Tesis", font=("Arial", 18, "bold")).pack(side="left")

        tk.Button(
            header, text="☰ Tablas",
            font=("Arial", 10), cursor="hand1",
            command=self._toggle_panel
        ).pack(side="right", padx=(5, 0))

        # Barra de búsqueda (a la izquierda del botón Tablas)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self._on_search)
        search_frame = tk.Frame(header)
        search_frame.pack(side="right", padx=5)
        tk.Label(search_frame, text="🔍", font=("Arial", 11)).pack(side="left")
        tk.Entry(search_frame, textvariable=self.search_var, width=30,
                 font=("Arial", 10)).pack(side="left", padx=(2, 0))
        tk.Button(search_frame, text="✕", font=("Arial", 9), cursor="hand1",
                  command=lambda: self.search_var.set("")).pack(side="left", padx=2)

        # ── Contenedor principal ──
        self.main_frame = tk.Frame(self)
        self.main_frame.pack(fill="both", expand=True)

        # Tabla principal (ocupa todo el espacio)
        self.table_frame = tk.Frame(self.main_frame)
        self.table_frame.pack(fill="both", expand=True)
        self._create_results_table()

        # Panel desplegable (se superpone con place, oculto al inicio)
        self.side_panel = tk.Frame(self.main_frame, bg="#f0f0f0", relief="solid", bd=1)
        self._create_side_panel()

    # ── Panel lateral ──────────────────────────

    def _toggle_panel(self):
        """Muestra u oculta el panel desplegable hacia abajo."""
        if self.panel_visible:
            self.side_panel.place_forget()
            self.panel_visible = False
        else:
            # Posiciona el panel debajo del botón, ancho completo, altura fija
            self.side_panel.place(relx=0, rely=0, relwidth=1, height=280)
            self.side_panel.lift()
            self.panel_visible = True
            self._load_side_panel_data()

    def _create_side_panel(self):
        """Construye el panel lateral con un Notebook de pestañas."""
        tk.Label(
            self.side_panel, text="Tablas auxiliares",
            font=("Arial", 12, "bold"), bg="#f0f0f0"
        ).pack(pady=(10, 5))

        self.notebook = ttk.Notebook(self.side_panel)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)

        # Pestaña Tesis
        self.tab_tesis = tk.Frame(self.notebook)
        self.notebook.add(self.tab_tesis, text="Tesis")
        self.tree_tesis_aux = self._make_mini_tree(
            self.tab_tesis, ("ID", "Año", "Título", "Tipo", "Institución"), (50, 50, 180, 100, 120)
        )

        # Pestaña Estudiantes
        self.tab_estudiantes = tk.Frame(self.notebook)
        self.notebook.add(self.tab_estudiantes, text="Estudiantes")
        self.tree_est = self._make_mini_tree(
            self.tab_estudiantes, ("ID", "Nombre"), (60, 240)
        )

        # Pestaña Responsables
        self.tab_responsables = tk.Frame(self.notebook)
        self.notebook.add(self.tab_responsables, text="Responsables")
        self.tree_resp = self._make_mini_tree(
            self.tab_responsables, ("ID", "Nombre", "Tipo"), (50, 150, 110)
        )

        # Pestaña Colaboradores
        self.tab_colaboradores = tk.Frame(self.notebook)
        self.notebook.add(self.tab_colaboradores, text="Colaboradores")
        self.tree_col = self._make_mini_tree(
            self.tab_colaboradores, ("ID", "Nombre"), (60, 240)
        )

        # Pestaña tesis_estudiante
        self.tab_te = tk.Frame(self.notebook)
        self.notebook.add(self.tab_te, text="Tesis-Estudiante")
        self.tree_te = self._make_mini_tree(
            self.tab_te, ("ID Tesis", "ID Estudiante"), (100, 120)
        )

        # Pestaña tesis_responsable
        self.tab_tr = tk.Frame(self.notebook)
        self.notebook.add(self.tab_tr, text="Tesis-Responsable")
        self.tree_tr = self._make_mini_tree(
            self.tab_tr, ("ID Tesis", "ID Responsable"), (100, 120)
        )

        # Pestaña tesis_colaborador
        self.tab_tc = tk.Frame(self.notebook)
        self.notebook.add(self.tab_tc, text="Tesis-Colaborador")
        self.tree_tc = self._make_mini_tree(
            self.tab_tc, ("ID Tesis", "ID Colaborador"), (100, 120)
        )

    def _make_mini_tree(self, parent, columns, widths):
        """Crea un Treeview compacto con scrollbar."""
        frame = tk.Frame(parent)
        frame.pack(fill="both", expand=True)

        tree = ttk.Treeview(frame, columns=columns, show="headings", height=20)
        for col, w in zip(columns, widths):
            tree.heading(col, text=col)
            tree.column(col, width=w)

        sb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        return tree

    def _load_side_panel_data(self):
        """Carga los datos de todas las tablas auxiliares desde la DB."""
        def reload(tree, query, keys):
            for i in tree.get_children():
                tree.delete(i)
            try:
                for row in self.controller.db.fetch_data(query):
                    tree.insert("", "end", values=tuple(row.get(k) or "—" for k in keys))
            except Exception as e:
                print(f"Error cargando tabla: {e}")

        reload(self.tree_tesis_aux,
               "SELECT id_producto, ano_registro, titulo, tipo_producto, institucion FROM tesis ORDER BY ano_registro DESC;",
               ["id_producto", "ano_registro", "titulo", "tipo_producto", "institucion"])

        reload(self.tree_est,
               "SELECT id_estudiante, nombre_estudiante FROM estudiante ORDER BY nombre_estudiante;",
               ["id_estudiante", "nombre_estudiante"])

        reload(self.tree_resp,
               "SELECT id_responsable, nombre_responsable, tipo_responsable FROM responsable ORDER BY nombre_responsable;",
               ["id_responsable", "nombre_responsable", "tipo_responsable"])

        reload(self.tree_col,
               "SELECT id_colaborador, nombre_colaborador FROM colaborador ORDER BY nombre_colaborador;",
               ["id_colaborador", "nombre_colaborador"])

        reload(self.tree_te,
               "SELECT id_producto, id_estudiante FROM tesis_estudiante ORDER BY id_producto;",
               ["id_producto", "id_estudiante"])

        reload(self.tree_tr,
               "SELECT id_producto, id_responsable FROM tesis_responsable ORDER BY id_producto;",
               ["id_producto", "id_responsable"])

        reload(self.tree_tc,
               "SELECT id_producto, id_colaborador FROM tesis_colaborador ORDER BY id_producto;",
               ["id_producto", "id_colaborador"])

    # ── Tabla principal ────────────────────────

    def _create_results_table(self):
        """Crea la tabla Treeview con columnas de tesis."""
        columns = ("ID", "AÑO", "TITULO", "TIPO", "FECHA_INICIO", "FECHA_FINAL",
                   "INSTITUCION", "ESTUDIANTE", "TIPO_RESP", "RESPONSABLE", "COLABORADOR")

        self.tree = ttk.Treeview(self.table_frame, columns=columns, show="headings")

        headers = {
            "ID":           ("ID Producto",     80),
            "AÑO":          ("Año",              60),
            "TITULO":       ("Título",           200),
            "TIPO":         ("Tipo",             120),
            "FECHA_INICIO": ("Fecha Inicio",     100),
            "FECHA_FINAL":  ("Fecha Final",      100),
            "INSTITUCION":  ("Institución",      130),
            "ESTUDIANTE":   ("Estudiante",       130),
            "TIPO_RESP":    ("Tipo Responsable", 120),
            "RESPONSABLE":  ("Responsable",      130),
            "COLABORADOR":  ("Colaborador",      130),
        }
        for col, (text, width) in headers.items():
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width)

        scrollbar_y = ttk.Scrollbar(self.table_frame, orient="vertical",  command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(self.table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        # El orden importa: scrollbar_x primero (bottom), luego scrollbar_y (right), luego tree
        scrollbar_x.pack(side="bottom", fill="x")
        scrollbar_y.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

    def _row_values(self, row):
        """Convierte una fila de DB a tupla de valores para el Treeview."""
        return (
            row.get('id_producto')        or "—",
            row.get('ano_registro')       or "—",
            row.get('titulo')             or "—",
            row.get('tipo_producto')      or "—",
            row.get('fecha_inicio')       or "—",
            row.get('fecha_final')        or "—",
            row.get('institucion')        or "—",
            row.get('nombre_estudiante')  or "—",
            row.get('tipo_responsable')   or "—",
            row.get('nombre_responsable') or "—",
            row.get('nombre_colaborador') or "—",
        )

    def _on_search(self, *args):
        """Filtra la tabla principal en tiempo real según el texto de búsqueda."""
        query = self.search_var.get().strip().lower()
        for i in self.tree.get_children():
            self.tree.delete(i)
        for row in self.all_data:
            values = self._row_values(row)
            if not query or any(query in str(v).lower() for v in values):
                self.tree.insert("", "end", values=values)

    def load_tesis_data(self):
        """Carga los datos de tesis desde la DB de forma segura."""
        for i in self.tree.get_children():
            self.tree.delete(i)

        try:
            self.all_data = self.controller.db.get_all_tesis()
        except Exception as e:
            messagebox.showerror("Error DB", f"No se pudieron cargar las tesis: {e}")
            return

        if not self.all_data:
            return

        self.search_var.set("")  # Limpiar búsqueda al recargar
        for row in self.all_data:
            self.tree.insert("", "end", values=self._row_values(row))


# ─────────────────────────────────────────────
# PÁGINA: Registro
# ─────────────────────────────────────────────
class RegisterPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.options = {}

        tk.Label(self, text="Registro de Nueva Tesis", font=("Arial", 18, "bold")).pack(pady=10)

        form_frame = tk.Frame(self)
        form_frame.pack(pady=10, padx=30, fill="x")

        self.form_fields = self._create_form_fields(form_frame)

        button_frame = tk.Frame(self)
        button_frame.pack(pady=15)
        ttk.Button(
            button_frame, text="✖ Cancelar",
            command=lambda: self.controller.show_frame("SearchPage")
        ).pack(side="left", padx=10)
        ttk.Button(
            button_frame, text="💾 Guardar Tesis",
            command=self.submit_tesis
        ).pack(side="left", padx=10)

    def _create_form_fields(self, parent):
        fields = {}

        def entry_row(row, label, key):
            tk.Label(parent, text=label, anchor="w").grid(row=row, column=0, padx=5, pady=5, sticky="w")
            entry = tk.Entry(parent, width=45)
            entry.grid(row=row, column=1, padx=5, pady=5, sticky="w")
            fields[key] = entry

        entry_row(0, "Año de registro",             'ano_registro')
        entry_row(1, "Título",                       'titulo')
        entry_row(2, "Tipo de producto",             'tipo_producto')
        entry_row(3, "Fecha de inicio (YYYY-MM-DD)", 'fecha_inicio')
        entry_row(4, "Fecha final (YYYY-MM-DD)",     'fecha_final')
        entry_row(5, "Institución",                  'institucion')
        entry_row(6, "Estudiante",                   'id_estudiante')
        entry_row(7, "Responsable",                  'id_responsable')
        entry_row(8, "Colaborador (opcional)",       'id_colaborador')

        return fields

    def submit_tesis(self):
        """Valida y envía el formulario para registrar una nueva tesis."""
        data = {}
        try:
            data['ano_registro']   = int(self.form_fields['ano_registro'].get())
            data['titulo']         = self.form_fields['titulo'].get().strip()
            data['fecha_inicio']   = self.form_fields['fecha_inicio'].get().strip()
            data['fecha_final']    = self.form_fields['fecha_final'].get().strip()
            data['tipo_producto']  = self.form_fields['tipo_producto'].get().strip()
            data['institucion']    = self.form_fields['institucion'].get().strip()
            data['id_estudiante']  = self.form_fields['id_estudiante'].get().strip()
            data['id_responsable'] = self.form_fields['id_responsable'].get().strip()
            data['id_colaborador'] = self.form_fields['id_colaborador'].get().strip() or None

            if not data['titulo']:
                raise ValueError("El título no puede estar vacío.")
            if not data['tipo_producto']:
                raise ValueError("El tipo de producto no puede estar vacío.")
            if not data['institucion']:
                raise ValueError("La institución no puede estar vacía.")
            if not data['id_estudiante']:
                raise ValueError("El nombre del estudiante no puede estar vacío.")
            if not data['id_responsable']:
                raise ValueError("El nombre del responsable no puede estar vacío.")
            if data['ano_registro'] < 1900:
                raise ValueError("El año de registro no es válido.")

        except ValueError as e:
            messagebox.showerror("Error de Validación", str(e))
            return
        except Exception as e:
            messagebox.showerror("Error", f"Datos inválidos: {e}")
            return

        new_id = self.controller.db.register_new_tesis(data)

        if new_id:
            self.controller.show_frame("SuccessPage", new_id)
        else:
            messagebox.showerror("Error de Registro", "No se pudo completar el registro de la tesis.")


# ─────────────────────────────────────────────
# PÁGINA: Éxito
# ─────────────────────────────────────────────
class SuccessPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.tesis_id = tk.StringVar(value="---")

        tk.Label(self, text="¡Tesis registrada con éxito!", font=("Arial", 24, "bold"), fg="green").pack(pady=40)
        tk.Label(self, text="ID de producto asignado:", font=("Arial", 16)).pack(pady=5)
        tk.Label(self, textvariable=self.tesis_id, font=("Arial", 20, "bold"), fg="#333").pack(pady=5)

        button_frame = tk.Frame(self)
        button_frame.pack(pady=30)

        ttk.Button(
            button_frame, text="➕ Registrar otra tesis",
            command=lambda: self.controller.show_frame("RegisterPage")
        ).pack(side="left", padx=10)
        ttk.Button(
            button_frame, text="🔍 Volver al inicio",
            command=lambda: self.controller.show_frame("SearchPage")
        ).pack(side="left", padx=10)

    def set_tesis_id(self, new_id):
        """Actualiza el ID de la tesis recién registrada."""
        self.tesis_id.set(str(new_id))
