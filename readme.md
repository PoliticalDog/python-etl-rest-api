Para poder ejecutar se recomienda instalar los requirements con el comando:
pip install -r requirements.txt

# stack
Python
VS code 
git --> repositorio remoto estandar 
docker --> Para practica de dockers y entrega profesional, ademas de aseguirar que funcione la base correctamente en otra maquina
Mysql --> Se elegio porque tengo mas experiencia y me siento comodo
FastApi --> Es  el framework mas comun para usar api rest y para practicar
Uvicorn --> servidor para probar la api
Swagger UI --> Deja probar apis sin programar un fronted completo

# Sección 1: Procesamiento y transferencia de datos
# Se creo un entonro virtual con env
python -m venv venv
venv\Scripts\activate

# se instalo las bicliotecas y herramientas
pip install pandas mysql-connector-python python-dotenv

# Se genera el requirements
pip freeze > requirements.txt

# Docker levantamiento 

docker run -d `
  --name pt_mysql `
  -e MYSQL_ROOT_PASSWORD=rootpass `
  -e MYSQL_DATABASE=pt_db `
  -e MYSQL_USER=pt_user `
  -e MYSQL_PASSWORD=pt_pass `
  -p 3307:3306 `
  -v pt_mysql_data:/var/lib/mysql `
  mysql:8.0

Se uso el puerto 3307 ya que el 3306 estandar de mysql lo estoy usando en mi local.

# Conectar la instancia de mysql en el docker (comprobacion)
docker exec -it pt_mysql mysql -u pt_user -p

# Iniciar docker y ejecutar los scripts de creacion y poblacion de tablas
Para esta seccion se creo la carpeta "sql" donde se guardaron dos scripts para crear las tablas y relaciones de la db como la vista que se pide.
* 01_schema.sql
* 02_view.sql

# Ejecutar el script mysql de creacion de tablas y relaciones en el docker (powershell)
docker exec -i pt_mysql mysql -u pt_user -ppt_pass pt_db < sql\01_schema.sql

# Crear vista mysql en el docker (powershell)
docker exec -i pt_mysql mysql -u pt_user -ppt_pass pt_db < sql\02_view.sql

# Carga de datos ETL

# Para poder visualiazar que traia el csv se uso un archivo de jupyter para jugar con el dataframe
  lectura_prueba_csv.ipynb

en donde se analiza los tipos de datos que hay, ademas de verificar cuantos campos nan y nat hay para no romper el esquema en campos que dicen no nulos, en este caso si hay habra que rellenar con promedios 

# Se analizo el csv con un archivo jupyter y se creo la carpeta "elt" en donde se guardaran los scripts que almacenaran la lectura, transformacion y carga
* lectura_prueba_csv --> prueba de jupyter para anlisis de los datos
* etl/03_transform_and_load.py --> contiene todo el scrypot de limpieza y carga a mysql

# Resumen de dificultades tecnicas

1. El primer error que halle fue al momento de cargar a la base mysql en campos que no podian recibir nulos, ya que al leer el csv no verifique que todos las filas tvieran valores, por lo que tuve que validar esa parte

2. Tanto Id y company Id daba error ya que el tamalñop del esquema era de 24 y en df venian de 40, mi solucion fue editar el schema 

3. No estoy seguro si fue error mio o del dataset original pero un amount era infinito lo que rompia la carga, la solucion mandarlo a critical detectandolo con nummpoy el inf y cambiando a nan para su separacion

4. En amount me volvio a dar error ya que el esquema se puede 16,2, y hay registris que superan ese tamaño de 16, por lo que los que superen se mandan a df_critical

# Flujo ETL
1. Como primer paso se lee el csv y se manipulara un total de 3 df para mantener los datos mas limpios y completos, teniendo en si:
  df_original → datos originales sin modificacion
  df → datos transformados listos para insercion
  df_critical → registros criticos (sin id) para revision futura

2. Primero como limpieza se cambio los nombres de dos columnas para que coincidan con la db y no confundirnos de las columnas: 
  name --> company_name
  paid_at  --> updated_at

3. Forzar o cambiar tipos de datos
  amount → forzar a 2 decimales
  updated_at → datetime para insertarlo como timestamp
  created_at → datetime para insertarlo como timestamp

4. Normalizacion
Para evitar errores todos las cadenas se pasaran a minusculas y sin espacios, para evitar errores:
  id
  company_id
  status

5. Eliminar los datos criticos (sin Id, company_id, amount, status, created_at) de df y copiarlos a df_critical, ya que se rompe la regla de negocios y no hay forma de rellenar 

5.1 Rellenar los nulos para no romper la futura carga en el esquema mysql
Aqui se analizo desde jupyter manualemnte las filas que tiene nulos para entender los errores y las reglas de negocio, por lo la forma de validacion que se llego es la siguiente: 

  id            --> X Eliminados de df y copiados a df_critical (no es posible rellenar sin romper las reglas de negocio)
  company_name  --> Si es nulo, se rellena usando el primer nombre valido encontrado por el mismo company_id; si no existe, se asigna "unknown"
  company_id    --> X Eliminados de df y se pasa df_critical, igual que id (es un valor estructural)
  amount        --> X en el df no hay nan, pero si hubiera se pasa df_critical ya que no podemos determinar que sea 0 y romer las cuentas
  status        --> X No hay forma de validar su status
  created_at    --> X Si no hay fecha de creacion se excluye, ya que no hay forma de verioficar la fecha real
  updated_at    --> si puede recibir null

6. Guardar df y df_critical como historial antes de la carga y si hay error en la carga de mysql poder estudiar
  df --> df_clean.csv
  df_critical --> df_critical.csv

# Cargar en ambas tablas ya limpias
7. conmstruir los df para cada tabla
* companies_df
* charges_df

8. Coencatr a bd mysql y cargar
8.1 Cagar companies y evitar duplicados en company
8.2 cargar charges

Se ejecuta el script con:
python etl/03_transform_and_load.py

Reusltados del script:
Total original: 10000
Total clean: 9986
Total critical: 14
Companies insertadas: 5
Charges insertadas/actualizadas: 9986
Conexión a la base de datos cerrada

8.3 Validacion de datos cargados
  -- Total de registros cargados
  SELECT COUNT(*) FROM charges;

  -- Total por compañia
  SELECT c.company_name, COUNT(*)
  FROM charges ch
  JOIN companies c ON ch.company_id = c.company_id
  GROUP BY c.company_name;

  -- Validar montos negativos
  SELECT *
  FROM charges
  WHERE amount < 0;


10. Se ejecuta la vista del archivo:
  sql 02_view.sql, donde se opuede filtrar despues por fecha

  ejemplo de consulta desde Mysql docker:

  SELECT *
  FROM daily_company_totals
  WHERE transaction_date = '2019-03-16';

  SELECT *
  FROM daily_company_totals
  WHERE transaction_date BETWEEN '2019-03-16' AND '2022-05-31';


11. Se crea el diagrama del schema, desde el docker
  docker exec -i pt_mysql mysql -u pt_user -ppt_pass -e "DESCRIBE companies;" pt_db

  docker exec -i pt_mysql mysql -u pt_user -ppt_pass -e "DESCRIBE charges;" pt_db

# Sección 2: Creación de una API

Me hicieron falta instalar las biblioetcas y se instalan en el entorno con:
pip install fastapi
pip install "uvicorn[standard]"

Probar api:
uvicorn api.main:app --reload

navegador:
  http://127.0.0.1:8000/docs

* reglas y uso:
se despliega la pestaña de "default" que es donde se hara las pruebas
# Post extract
* post extract --> se presiona "try out" y en el ejemplo se puede modificar el numero de 0 - 100
* validaciones, si se coloca un numero fuera del intervalo arorja error 400, si se quiere reptir un numero arroja error 400

# Get missing 
Se ejecuta y calcula el numerop flatante, solo funciona si se extrajo un solo numero de la lista, de ser mas de 1 dara error

s=(n(n+1))/2​
faltante = suma_esperada - suma_actual

# Post reset+
Reseta la lista para seguir validando



# Preparacion para subir al git
se crreo el gitignore
