# Finanzas Autónomo

Gestión de facturas/gastos, tesorería y cálculo de IVA/IRPF (trimestral y
anual) para autónomos en España.

## Histórico de lo hecho hasta el momento

1. **Setup inicial**: backend FastAPI + PostgreSQL, frontend React + Vite,
   motor fiscal puro (`tax_calculator.py`) con sus tests, auth por JWT.
2. **Documentos (facturas y gastos)**: alta manual de ingresos (facturas
   emitidas) y gastos (facturas recibidas), cada uno con fecha, número de
   factura, NIF/nombre del pagador y del cobrador, base imponible, IVA% e
   IRPF%. Cada documento creado queda registrado en su tabla (`invoices` /
   `expenses`), asociado al usuario que lo creó.
3. **Impuestos con datos reales + sección Renta**: se resolvió el cálculo
   acumulado real de los modelos 130 trimestrales (antes eran `0` fijos) a
   partir de las facturas/gastos reales, y se añadió la sección **Renta**:
   los 4 modelos 130 del año encadenados más la estimación del modelo 100
   anual calculada a partir de ellos. En Impuestos se puede consultar
   cualquier año/trimestre pasado.
4. **UI modernizada**: CSS global mínimo (sin dependencias nuevas) —
   tipografía `system-ui`, paleta neutra con acento índigo, tarjetas,
   pestañas y tablas con un estilo consistente en toda la app.
5. **Preparación para desplegar online**: registro de usuarios desde el
   frontend (antes solo existía en la API), URL de la API y orígenes CORS
   configurables por variable de entorno, `SECRET_KEY` con aviso si se deja
   el valor por defecto, y migraciones de Alembic que se ejecutan solas al
   arrancar el contenedor (antes no había ninguna migración generada).

## Cómo funciona el proyecto

### A nivel usuario

- **Login / Crear cuenta**: cualquiera puede registrarse con su correo y
  contraseña. No hace falta invitación ni aprobación.
- **Documentos**: pestañas "Ingreso" (una factura que emites y cobras) y
  "Gasto" (una factura que recibes y pagas). Cada uno queda en su propio
  listado.
- **Impuestos**: eliges año y trimestre y ves el IVA (modelo 303) y el pago
  fraccionado de IRPF (modelo 130) de ese periodo, calculados con tus
  documentos reales.
- **Renta**: eliges un año y ves los 4 modelos 130 de ese año (encadenados,
  no cada uno por separado) y la estimación de la declaración anual
  (modelo 100): cuánto queda por pagar o a devolver.
- **Privacidad**: cada usuario solo ve sus propias facturas y gastos — todo
  se filtra siempre por el usuario que hizo login, nunca hay una vista que
  mezcle datos de varios usuarios.

### A nivel programador

**Backend** (`backend/app/`):

```
app/
├── main.py               FastAPI app, CORS, registro de routers
├── core/
│   ├── config.py         Settings (env vars): DATABASE_URL, SECRET_KEY, CORS_ORIGINS...
│   ├── security.py       hash/verify de contraseñas (bcrypt), JWT
│   └── deps.py           get_current_user (del JWT) / get_current_db_user (fila de User)
├── db/session.py         engine, SessionLocal, Base
├── models/models.py      User, Invoice, Expense (SQLAlchemy)
├── schemas/               Pydantic: InvoiceCreate/Out, ExpenseCreate/Out
├── api/
│   ├── auth.py           /api/auth/login, /register
│   ├── invoices.py       /api/invoices/  (crear y listar, filtrado por owner_id)
│   ├── expenses.py       /api/expenses/  (idem)
│   └── taxes.py          /api/taxes/iva, /modelo130, /renta — orquesta datos reales
├── services/
│   └── tax_calculator.py  Motor fiscal puro (sin DB): IVA, modelo 130, modelo 100
└── tests/                 Tests del motor de cálculo
```

- **Modelo de datos**: en `Invoice` (ingreso), el *pagador* es el cliente
  (`cliente_nombre`/`cliente_nif`) y el *cobrador* eres tú, el emisor
  (`emisor_nombre`/`emisor_nif`). En `Expense` (gasto), el *cobrador* es el
  proveedor (`proveedor_nombre`/`proveedor_nif`) y el *pagador* eres tú
  (`pagador_nombre`/`pagador_nif`). Ambos modelos son independientes a
  propósito (no un único modelo "Documento") para poder llevar por separado
  el histórico de ingresos y gastos de cara a la Renta y los trimestrales.
- **Motor fiscal** (`services/tax_calculator.py`): funciones puras, sin
  tocar la base de datos, totalmente testeadas. `api/taxes.py` es la capa
  que agrega las facturas/gastos reales de la BD y se los pasa a estas
  funciones:
  - `calcular_iva_trimestral`: modelo 303 con prorrata si hay ventas
    exentas mezcladas con sujetas.
  - `calcular_modelo_130`: pago fraccionado trimestral. `api/taxes.py`
    tiene `_modelo130_acumulado()`, que recorre los trimestres 1..N del
    año encadenando rendimiento neto, retenciones y pagos ya ingresados
    reales (no placeholders).
  - `calcular_renta_anual`: modelo 100, usa como pagos fraccionados la
    suma real de los 4 modelos 130 del año (vía la misma función).
- **Auth**: JWT (`python-jose`) con contraseñas en bcrypt. Hay un campo
  `role` en `User` (`owner` / `team` / `gestor`) pensado para el futuro rol
  de solo-lectura, pero hoy todos los endpoints solo comprueban que hay un
  usuario autenticado y filtran por su `owner_id`.
- **Migraciones**: Alembic, con una única migración baseline
  (`esquema inicial`) que crea las tres tablas desde cero. El `Dockerfile`
  ejecuta `alembic upgrade head` antes de arrancar `uvicorn`, así que una
  base de datos nueva (por ejemplo en Railway) se migra sola.

**Frontend** (`frontend/src/`):

```
src/
├── main.jsx              Punto de entrada, importa index.css
├── index.css             Estilos globales (variables, tarjetas, tabs, tablas...)
├── App.jsx                Rutas y navegación (React Router)
├── api/client.js          axios con baseURL = VITE_API_URL, añade el JWT a cada request
└── pages/
    ├── Home.jsx
    ├── Login.jsx          Login y registro (pestañas)
    ├── DocumentsPage.jsx  Alta de ingresos/gastos + listados
    ├── TaxesPage.jsx      IVA + modelo 130 por año/trimestre
    └── RentaPage.jsx      Modelo 130 (x4) + modelo 100 por año
```

Sin Redux ni librería de estado: cada página pide sus datos con `axios` al
montar y guarda el resultado en `useState`. El token JWT vive en
`localStorage` y se añade automáticamente a cada petición desde
`api/client.js`.

## Estructura

```
finanzas-app/
├── backend/        FastAPI + PostgreSQL (ver detalle arriba)
└── frontend/       React + Vite (ver detalle arriba)
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

alembic upgrade head             # crea las tablas
uvicorn app.main:app --reload    # http://localhost:8000
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
cp .env.example .env             # VITE_API_URL, por defecto http://localhost:8000
npm run dev                      # http://localhost:5173
```

## Abrir en VS Code

```bash
code finanzas-app
```

Extensiones recomendadas: Python, Pylance, ESLint, Prettier.

## Guía de despliegue (Railway)

### 1. Backend + base de datos

1. Ve a [railway.app](https://railway.app), crea cuenta (con GitHub es lo
   más rápido) y "New Project" → "Deploy from GitHub repo" → selecciona tu
   repo.
2. Railway detectará el `Dockerfile`. En la configuración del servicio,
   pon **Root Directory = `backend`** (para que use `backend/Dockerfile`
   como contexto).
3. Añade un servicio de base de datos: "New" → "Database" → "PostgreSQL".
   Railway te da un `DATABASE_URL` automáticamente.
4. En el servicio del backend, variables de entorno:
   - `DATABASE_URL` → referencia la del servicio Postgres (Railway te deja
     enlazarla directamente, `${{Postgres.DATABASE_URL}}`), pero cambia el
     prefijo a `postgresql+psycopg2://` si Railway lo da como
     `postgresql://` (SQLAlchemy lo necesita).
   - `SECRET_KEY` → genera algo aleatorio (p.ej. `openssl rand -hex 32`),
     nunca dejes el valor por defecto.
   - `CORS_ORIGINS` → la URL del frontend una vez la tengas (paso
     siguiente); de momento puedes poner `*` temporalmente y ajustarlo
     después.
5. Deploy. Al arrancar, el contenedor ejecuta `alembic upgrade head` solo
   (ya lo dejé configurado) — crea las tablas automáticamente en la base
   de datos nueva. Verifica en los logs que dice
   `Running upgrade -> ... esquema inicial`.
6. Railway te da una URL pública tipo `https://tu-backend.up.railway.app`.
   Pruébala: `https://tu-backend.up.railway.app/api/health` debe responder
   `{"status":"ok"}`.

### 2. Frontend

1. Puedes usar el mismo Railway (otro servicio, "Static Site" apuntando a
   `frontend/`, build command `npm run build`, output `dist`) o algo más
   simple como Vercel o Netlify (arrastran y sueltan un repo React sin
   fricción).
2. Variable de entorno del build: `VITE_API_URL=https://tu-backend.up.railway.app`.
3. Una vez tengas la URL del frontend (p.ej. `https://finanzas.vercel.app`),
   vuelve al backend en Railway y pon
   `CORS_ORIGINS=https://finanzas.vercel.app`.

### 3. Cómo lo usan tus amigos

- Entran en la URL del frontend, pestaña "Crear cuenta" en Login, se
  registran con su correo — cada uno solo ve sus propias facturas/gastos
  (ya lo verifiqué: aislamiento por usuario funciona).
- Aviso de privacidad honesto que puedes darles: tú, como administrador
  del servidor, tienes acceso técnico a la base de datos (no hay cifrado
  de extremo a extremo), pero la app no tiene ninguna pantalla ni
  herramienta para que tú veas sus datos desde dentro — cada endpoint
  filtra siempre por su propio usuario.

### 4. Despliegue continuo (auto-deploy)

Sí, por defecto ambos están conectados directamente a tu repo de GitHub y
se despliegan solos en cada `push` a la rama que usaste para conectar
(normalmente `main`):

- **Railway**: detecta el nuevo commit, reconstruye la imagen Docker y la
  despliega. Como el `Dockerfile` ejecuta `alembic upgrade head` antes de
  arrancar, si en el futuro añades una migración nueva (una columna, una
  tabla...) se aplicará sola a la base de datos de Railway en cada
  redeploy — no tienes que hacer nada manual para eso.
- **Vercel**: detecta el commit, corre `npm run build` en `frontend/` con
  las variables de entorno que ya configuraste, y publica el resultado.
  Cada push a `main` es un "Production Deployment"; si haces push a otra
  rama o abres un Pull Request, Vercel también crea una **Preview
  Deployment** con una URL distinta (útil para probar cambios antes de que
  lleguen a la URL que usan tus amigos).

Dos cosas a vigilar cuando actualices:

1. Si cambias algo en `models/models.py`, tienes que generar la migración
   de Alembic **antes** de hacer push (`alembic revision --autogenerate`)
   y comprobarla en local — Railway solo aplica las migraciones que ya
   existen en el repo, no las genera por ti.
2. Puedes desactivar el auto-deploy en cualquiera de los dos si algún día
   quieres controlar manualmente cuándo sale un cambio (en Railway:
   Settings → Source, hay un toggle de "Auto Deploy"; en Vercel: Settings →
   Git).

## Próximos pasos sugeridos

1. Editar y borrar facturas/gastos (hoy solo se pueden crear y listar).
2. Integrar OCR para extraer datos automáticamente de PDFs/imágenes de
   facturas (`archivo_url` ya existe en los modelos, pendiente de subida
   real y detección).
3. Ajustar la escala de IRPF anual (`TRAMOS_IRPF` en `tax_calculator.py`)
   por comunidad autónoma — hoy es una escala combinada orientativa.
4. Rol `gestor`: vista de solo lectura + exportación a su software (A3,
   Sage...). El campo `role` ya existe en `User`, falta aplicarlo en los
   endpoints.
5. Si el proyecto pasa de "feedback con amigos" a uso real con datos
   sensibles de terceros, valorar cifrado de extremo a extremo para que
   ni con acceso a la base de datos se puedan leer los documentos de cada
   usuario.
