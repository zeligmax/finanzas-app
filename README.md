# Finanzas Autónomo

Proyecto inicial: gestión de facturas/gastos, tesorería y cálculo de IVA/IRPF
(trimestral y anual) para autónomos en España.

## Estructura

```
finanzas-app/
├── backend/        FastAPI + PostgreSQL
│   └── app/
│       ├── services/tax_calculator.py   ← lógica fiscal validada
│       ├── api/                         ← endpoints (auth, taxes)
│       ├── models/                      ← User, Invoice, Expense
│       └── tests/                       ← tests del motor de cálculo
└── frontend/       React + Vite
```

## Arrancar el backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # en Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # edita DATABASE_URL y SECRET_KEY

# Necesitas PostgreSQL corriendo y la base de datos creada:
# createdb finanzas

uvicorn app.main:app --reload   # http://localhost:8000
```

Documentación interactiva de la API: http://localhost:8000/docs

### Ejecutar los tests del motor de cálculo

```bash
cd backend
pytest app/tests/ -v
```

## Arrancar el frontend

```bash
cd frontend
npm install
npm run dev                     # http://localhost:5173
```

## Abrir en VS Code

```bash
code finanzas-app
```

Extensiones recomendadas: Python, Pylance, ESLint, Prettier.

## Próximos pasos sugeridos

1. Crear las migraciones de base de datos (Alembic) a partir de `models/models.py`.
2. Endpoints CRUD para subir y editar facturas/gastos.
3. Integrar OCR para extraer datos automáticamente de PDFs de facturas.
4. Acumular trimestres anteriores reales en `api/taxes.py` (ahora mismo están
   en `0` como placeholder — están marcados con `# TODO`).
5. Pantallas de login y subida de documentos en el frontend.
6. Rol `gestor`: vista de solo lectura + exportación a su software (A3, Sage...).
