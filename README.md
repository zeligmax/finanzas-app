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

6. **Validación de NIF/CIF y cómputos totales**: aviso (sin bloquear) si un
   NIF/CIF/NIE no supera el dígito de control, tarjeta "Cómputo total de
   impuestos" en Impuestos y Renta, y caja lateral de resumen de la Renta en
   Impuestos.
7. **Usuario y IRPF en el peor caso**: sección Usuario (nombre, NIF/CIF y
   cuota de autónomos mensual). Renta descuenta la cuota de autónomos y
   calcula el IRPF con la escala de la comunidad autónoma más cara, mostrando
   el porcentaje medio. El mínimo personal se descuenta de la cuota (no de la
   base) y la cuota de autónomos también cuenta en los modelos 130. Se
   corrigió que Impuestos mostrara siempre "a compensar" en el IVA.

8. **Editar y borrar documentos**: cada ingreso y gasto tiene ahora botones
   Editar (recarga el formulario con sus datos y guarda los cambios) y Borrar
   (con confirmación). Los cálculos de Impuestos y Renta se actualizan solos
   al cambiar o eliminar un documento.
9. **Acceso de gestores (solo lectura)**: un usuario puede dar acceso a su
   gestor mediante un código de invitación de un solo uso. El gestor, con una
   cuenta de tipo gestor, canjea el código y ve —sin poder modificar nada— los
   documentos, impuestos y Renta de ese cliente, hasta que el cliente lo
   revoque. Antes se investigó qué software usan las gestorías y cómo se
   relacionan con Hacienda (ver "Gestorías y Administración").
10. **Lectura automática de facturas (OCR)**: en Documentos se puede subir un
    PDF o una imagen de una factura, en castellano, catalán o inglés, y la app
    rellena el formulario con lo que lee (número, fecha, NIF/nombre del emisor
    y del cliente, base, IVA, IRPF y total) para que el usuario lo revise antes
    de guardar. Se decidió OCR local con Tesseract, sin enviar las facturas a
    ningún servicio externo, y sin guardar el archivo (ver "Lectura de facturas
    (OCR)" para cómo funciona y sus límites).

## Cómo funciona el proyecto

### A nivel usuario

- **Login / Crear cuenta**: cualquiera puede registrarse con su correo y
  contraseña. No hace falta invitación ni aprobación.
- **Documentos**: pestañas "Ingreso" (una factura que emites y cobras) y
  "Gasto" (una factura que recibes y pagas). Cada uno queda en su propio
  listado, desde donde puedes editarlo o borrarlo. Encima hay "Leer una
  factura": subes un PDF o una imagen (hasta 8 MB) y se rellena el formulario;
  siempre debes revisar los datos y completar lo que falte (por ejemplo la
  categoría de un gasto) antes de guardar.
- **Usuario**: tu nombre, NIF/CIF y la cuota de autónomos media mensual, que
  se descuenta como gasto en los cálculos de IRPF.
- **Impuestos**: eliges año y trimestre y ves el IVA (modelo 303) y el pago
  fraccionado de IRPF (modelo 130) de ese periodo, calculados con tus
  documentos reales, el cómputo total a abonar y un resumen de la Renta.
- **Renta**: eliges un año y ves los 4 modelos 130 de ese año (encadenados,
  no cada uno por separado) y la estimación de la declaración anual
  (modelo 100) con el porcentaje medio de IRPF: cuánto queda por pagar o a
  devolver.
- **Gestor**: en esa sección generas un código de invitación (caduca a los 7
  días y solo sirve una vez) y se lo pasas a tu gestor. Puedes cancelarlo o
  revocar el acceso cuando quieras.
- **Si eres gestor** (casilla al crear la cuenta): en Clientes canjeas el
  código de cada cliente y eliges a quién consultar. Todo lo ves en solo
  lectura, con un aviso visible de a quién estás viendo.
- **Privacidad**: cada usuario solo ve sus propias facturas y gastos. La única
  excepción es un gestor al que tú hayas dado acceso, que puedes quitar en
  cualquier momento.

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
├── models/models.py      User, Invoice, Expense, GestorAccess (SQLAlchemy)
├── schemas/               Pydantic: Invoice, Expense y perfil de usuario
├── api/
│   ├── auth.py           /api/auth/login, /register
│   ├── users.py          /api/users/me (perfil: nombre, NIF/CIF, cuota de autónomos)
│   ├── access.py         /api/access (invitaciones del dueño) y /api/gestor (canje y clientes)
│   ├── extract.py        POST /api/documents/extract: lee una factura y propone los campos
│   ├── invoices.py       /api/invoices/  (listar, crear, PUT y DELETE por id; siempre por owner_id)
│   ├── expenses.py       /api/expenses/  (idem)
│   └── taxes.py          /api/taxes/iva, /modelo130, /renta — orquesta datos reales
├── services/
│   ├── tax_calculator.py  Motor fiscal puro (sin DB): IVA, modelo 130, modelo 100
│   ├── ocr.py             Lee PDF (capa de texto) e imágenes (Tesseract) y devuelve texto
│   ├── invoice_parser.py  Texto de una factura -> campos (número, fecha, NIF, importes...)
│   └── nif.py             Validación del dígito de control de NIF/CIF/NIE
└── tests/                 Tests del motor fiscal y del analizador de facturas
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
- **Editar/borrar**: `PUT` y `DELETE` en `/api/invoices/{id}` y
  `/api/expenses/{id}` buscan el documento por id **y** por `owner_id`. Si no
  existe o es de otro usuario devuelven 404 (no 403), para no revelar que el
  id existe. `PUT` reemplaza todos los campos editables (mismo esquema que el
  alta).
- **Acceso de gestores**: tabla `gestor_access` (dueño, gestor, código,
  estado `pendiente`/`aceptado`, caducidad). Se vincula con un **código de un
  solo uso** y no por correo, porque la app no verifica correos y cualquiera
  podría registrarse con el correo del gestor. La dependencia
  `get_target_owner` (`core/deps.py`) decide de quién son los datos que se
  leen: el propio usuario o, si es gestor con acceso aceptado, el `cliente_id`
  que pasa por parámetro. **Solo se usa en endpoints de lectura** (listados y
  cálculos de impuestos); los de escritura usan siempre `get_current_db_user`,
  así un gestor no puede modificar datos de un cliente. Cualquier caso no
  permitido responde 404.
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
├── hooks/useResumenAnual.js  Carga IVA anual + modelos 130 + Renta (Impuestos y Renta)
├── utils/nif.js           Validación del dígito de control de NIF/CIF/NIE
└── pages/
    ├── Home.jsx
    ├── Login.jsx          Login y registro (pestañas)
    ├── UserPage.jsx       Datos del usuario y cuota de autónomos
    ├── AccesoPage.jsx     (dueño) invitaciones y accesos de gestores
    ├── ClientesPage.jsx   (gestor) canjear códigos y elegir cliente
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

### OCR en local (Tesseract)

Los **PDF con texto** se leen sin instalar nada. Para leer **imágenes y PDF
escaneados** hace falta Tesseract con los idiomas castellano, catalán e inglés:

- **Con Docker** (lo más fácil): `docker compose up web` usa la imagen del
  backend, que ya lo trae instalado.
- **Directamente en Windows**: instala Tesseract (por ejemplo
  `winget install UB-Mannheim.TesseractOCR`), descarga `spa.traineddata` y
  `cat.traineddata` de [tessdata_fast](https://github.com/tesseract-ocr/tessdata_fast)
  a su carpeta `tessdata`, y si no está en el PATH pon su ruta en
  `TESSERACT_CMD` (en `backend/.env`).
- **Sin Tesseract**: la app funciona igual y, al subir una imagen, avisa de que
  el servidor no tiene OCR.

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

## Gestorías y Administración (investigación, sept. 2026)

Resultado de investigar cómo trabajan las gestorías, para decidir qué exportar.
Es una fotografía de esa fecha: conviene revisarla antes de implementar.

**Software de las gestorías**: el estándar es **a3** (Wolters Kluwer:
a3asesor, a3innuva). Después Sage (Despachos, Sage 50), Holded, Contaplus y
Monitor Informática. No hay cuotas de mercado públicas fiables. a3 importa por
Excel con plantillas o por su fichero de enlace `SUENLACE.DAT` (ASCII; su
especificación, "Enlace Contable - Descripción de Registros", no es pública);
Sage importa CSV/Excel con un mapeo de columnas. Apps para autónomos como
Quipu dan acceso a la gestoría con un usuario extra y exportan a Excel/CSV.

**Relación con Hacienda**: la gestoría presenta los modelos como colaborador
social (certificado electrónico + autorización del cliente) o con
apoderamiento en la Sede. Nuestra app **no presenta nada ante Hacienda**. La
AEAT ofrece Pre303, Pre130 y Renta WEB, que rellenan los modelos 303, 130 y la
Renta al importar un **Excel oficial (XLSX)** de libros registro.

**Formato oficial de libros registro (AEAT)**: un único XLSX (máx. 4 MB) con
las hojas `EXPEDIDAS_INGRESOS` y `RECIBIDAS_GASTOS` (y opcional
`BIENES-INVERSIÓN`), sin fraccionar por trimestre (del 1 de enero al fin del
trimestre). Nombre del fichero: ejercicio + NIF + tipo (`T` = unificado
IVA+IRPF) + nombre. La hoja de ingresos tiene 36 columnas y la de gastos 42
(diseño en `LSI.xlsx`). a3 también exporta este formato. Hay un servicio de
validación de ficheros en la Sede.

**Lo que nos falta para generarlo**: epígrafe del IAE, tipo de factura, código
de concepto de gasto (hoy la categoría es texto libre), clave de operación, y
la cuota de autónomos como gasto.

**Verifactu y factura electrónica**: según las fuentes consultadas, Verifactu
es obligatorio para el software de facturación desde el 1 de enero de 2027
(sociedades) y el 1 de julio de 2027 (resto, incluidos autónomos), tras el
Real Decreto-ley 15/2025. La factura electrónica B2B (Ley Crea y Crece, Real
Decreto 238/2026) se aplicará de forma escalonada. Afectan a quien **emite**
facturas: nuestra app solo las registra, así que no aplican mientras no
añadamos emisión.

**Plan de exportaciones** (pendiente): 1) Excel oficial AEAT de libros
unificados, 2) Excel/CSV limpio para las plantillas de a3 y Sage, 3) PDF
resumen, 4) `SUENLACE.DAT` solo si la gestoría lo pide. Antes de decidir el
punto 4 hay que preguntar a la gestoría real qué software usa.

Fuentes: [Formatos electrónicos de los libros registro (AEAT, PDF)](https://sede.agenciatributaria.gob.es/static_files/Sede/Tema/IVA/Fact_registro/Libros_registro/Formato_Electronico_Comun_Libros_Registro_IVA_IRPF.pdf),
[Diseños de registro LSI.xlsx](https://sede.agenciatributaria.gob.es/static_files/AEAT/LSI.xlsx),
[Pre130: importación de libros](https://sede.agenciatributaria.gob.es/Sede/ayuda/consultas-informaticas/presentacion-declaraciones-ayuda-tecnica/modelo-130/pre130-colectivo-importacion.html),
[Colaboración social (AEAT)](https://sede.agenciatributaria.gob.es/Sede/colaborar-agencia-tributaria/colaboracion-social-presentacion-declaraciones/preguntas-frecuentes-sobre-colaboracion-social.html).

## Lectura de facturas (OCR)

`POST /api/documents/extract` recibe un archivo y devuelve **propuestas** de
campos; no guarda nada (ni el archivo ni el documento). La lectura se hace en
tu propio servidor: las facturas no se envían a servicios de terceros.

**Cómo funciona**
1. `ocr.py` detecta el tipo por el contenido del archivo. Un **PDF con texto**
   se lee directamente de su capa de texto (exacto, sin OCR). Una **imagen** o
   un **PDF escaneado** pasa por Tesseract (`spa+cat+eng`), con reintento con
   preprocesado más agresivo (mediana + umbral de Otsu) y corrección de
   orientación si la primera lectura es pobre.
2. Del OCR se construyen tres textos a partir de las coordenadas de cada
   palabra: por **columnas** (para que el emisor y el cliente, si están uno al
   lado del otro, no se mezclen), por **bloques** (orden de Tesseract) y por
   **filas** (para que cada etiqueta quede junto a su importe).
3. `invoice_parser.py` extrae los campos por reglas (etiquetas y patrones en
   los tres idiomas). El NIF/CIF se valida con su dígito de control y, si el
   OCR lo ha leído mal (Z↔2, B↔8...), se prueba la corrección típica y solo se
   acepta la que supera el dígito de control. Se deduce si es **ingreso o
   gasto** comparando con el NIF del usuario. Los importes se cuadran
   (base + IVA − IRPF = total) y cualquier duda sale como **aviso**.
4. El frontend rellena el formulario y muestra los avisos y el texto leído.

**Precisión medida** (facturas de muestra generadas para las pruebas, en PDF,
en imagen limpia y en imagen "escaneada" con ruido y giro):
- Facturas con las que se desarrolló el analizador: 99 % de los campos.
- Facturas nuevas, con otros formatos y vocabulario, **medidas antes de
  ajustar nada: 90 %**. Tras corregir los fallos que salieron (y que eran
  generales, no de esas facturas) llegó al 98 %, pero ese lote ya no cuenta
  como independiente.

  El número que cabe esperar con facturas reales es, por tanto, algo inferior
  al 98 %: por eso el resultado es siempre una propuesta que hay que revisar.

**Límites conocidos**
- Una factura con **varios tipos de IVA** se marca con un aviso y se dejan en
  blanco base e IVA (cada documento admite un solo tipo).
- Las fechas numéricas se interpretan como día/mes/año; una factura
  estadounidense con mes/día/año se leería mal.
- Los identificadores fiscales de otros países se detectan con la etiqueta
  VAT/Tax ID pero no se pueden validar.
- Las imágenes muy borrosas, con mucho ruido o fotografiadas de lado dan
  lecturas poco fiables: se avisa por la confianza del OCR, y en el peor caso
  no se devuelve ningún dato en vez de inventarlo. El PDF original siempre da
  mejor resultado que una foto.
- No se lee escritura a mano.
- La **categoría** de un gasto no viene en la factura: la escribe el usuario.

**Protecciones**: máximo 8 MB y 3 páginas por archivo, tipo de archivo
comprobado por su contenido, máximo 20 lecturas cada 10 minutos por usuario
(en memoria, se reinicia con el servidor) y las cuentas de gestor no pueden
usarlo. El `Dockerfile` instala Tesseract, así que la imagen es más grande y
el primer despliegue tarda más.

## Mantenimiento anual

Las escalas hay que actualizarlas cada año, en `ESCALAS_AUTONOMICAS` de
`tax_calculator.py`.

Matices del cálculo del IRPF que no hay que olvidar al tocarlo:

- **Mínimo personal** (`MINIMO_PERSONAL_DEFAULT`): no se resta de la base
  liquidable. Se calcula el impuesto de toda la base y después se descuenta
  el impuesto que corresponde al mínimo con la misma escala
  (`cuota = escala(base) − escala(mínimo)`). Restarlo de la base ahorra el
  tipo del último tramo y subestima el impuesto (unos 755 € con un
  rendimiento de 35.550 €). Además, el mínimo real varía con la edad y las
  circunstancias familiares; hoy se usa el general de 5.550 €.
- **Cuota de autónomos**: es gasto deducible tanto en la Renta (×12) como en
  cada modelo 130 (×3 por trimestre). Cualquier cálculo nuevo que use el
  rendimiento neto debe incluirla, o los trimestrales y la Renta dejarán de
  ser coherentes entre sí.
- **Peor caso**: la cuota se calcula con la comunidad autónoma más cara para
  cada beneficio (máximo entre las escalas de `ESCALAS_AUTONOMICAS`), porque
  la estimación es orientativa y preferimos pagar de más que de menos.
  Navarra y País Vasco (régimen foral) no están incluidas.

## Próximos pasos sugeridos

1. Afinar el IRPF: mínimo personal según edad y circunstancias familiares, y
   contemplar Navarra y País Vasco (régimen foral), que hoy no están.
2. Exportaciones para la gestoría (el acceso de solo lectura ya está hecho):
   Excel oficial de libros registro de la AEAT, Excel/CSV para a3 y Sage y PDF
   resumen. Ver "Gestorías y Administración" para el plan y los campos que
   faltan (IAE, tipo de factura, concepto de gasto).
3. Mejorar la lectura de facturas (OCR): facturas con varios tipos de IVA
   (repartirlas en varias líneas), guardar el archivo original (`archivo_url`
   ya existe en los modelos; requiere almacenamiento persistente en Railway) y
   probar con facturas reales de usuarios para ampliar las reglas.
4. Si el proyecto pasa de "feedback con amigos" a uso real con datos
   sensibles de terceros, valorar cifrado de extremo a extremo para que
   ni con acceso a la base de datos se puedan leer los documentos de cada
   usuario.
