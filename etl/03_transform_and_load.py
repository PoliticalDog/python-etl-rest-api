import pandas as pd
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error
import os
import numpy as np

#cargar variables env
load_dotenv()

# rutina para conectar a la base de datos
def connect_to_database():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
    )

# main
def main():
    #leer csv y transformar datos
    try:
        # ruta del archivo csv
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        csv_path = os.path.join(base_dir, "data_prueba_técnica.csv")

        # 1. leer el archivo csv
        df_original = pd.read_csv(csv_path)

        # Copiar dataframe original a uno de curado
        df = df_original.copy()

        # 2. CAMBIAR NONMBRE DE COLUMNAS
        df.rename(columns={
            'name': 'company_name',
            'paid_at': 'updated_at',
        }, inplace=True)

        # 3. Forzar tipo de dato
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").round(2)
        df["updated_at"] = pd.to_datetime(df["updated_at"], errors='coerce')
        df["created_at"] = pd.to_datetime(df["created_at"], errors='coerce')

        # 4. normalizacion de texto y amount
        df["id"] = df["id"].astype("string").str.strip().str.lower()
        df["company_id"] = df["company_id"].astype("string").str.strip().str.lower()
        df["status"] = df["status"].astype(str).str.strip().str.lower()
        df["amount"] = df["amount"].replace([np.inf, -np.inf], pd.NA)
        max_amount = 99999999999999.99  # Forzar decimal con tamaño(16,2)
        df.loc[(df["amount"].notna()) & (df["amount"].abs() > max_amount), "amount"] = pd.NA
        
        # 5. Separar datos criticos a df_critcal para futura reviosion+
        # 5.1 relleno de nulos 
        mask_id_critical = df["id"].isna() | (df["id"] == "") | (df["id"] == "nan")
        mask_company_id_critical = df["company_id"].isna() | (df["company_id"] == "") | (df["company_id"] == "nan")
        mask_amount_critical = df["amount"].isna()
        mask_created_at_critical = df["created_at"].isna()
        mask_status_critical = (df["status"].isna() |(df["status"] == "") |(df["status"] == "nan"))

            # union de reglas críticas
        mask_any_critical = (
            mask_id_critical |
            mask_company_id_critical |
            mask_amount_critical |
            mask_created_at_critical |
            mask_status_critical
        )

            # Crear df_critical + motivos (solo para esas filas)
        df_critical = df.loc[mask_any_critical].copy()
        df_critical["_critical_reason"] = ""

        idx = df_critical.index  # índices de filas críticas

        df_critical.loc[idx.intersection(df.index[mask_id_critical]), "_critical_reason"] += "missing_id|"
        df_critical.loc[idx.intersection(df.index[mask_company_id_critical]), "_critical_reason"] += "missing_company_id|"
        df_critical.loc[idx.intersection(df.index[mask_amount_critical]), "_critical_reason"] += "invalid_amount|"
        df_critical.loc[idx.intersection(df.index[mask_created_at_critical]), "_critical_reason"] += "missing_created_at|"
        df_critical.loc[idx.intersection(df.index[mask_status_critical]), "_critical_reason"] += "missing_status|"

        df_critical["_critical_reason"] = df_critical["_critical_reason"].str.rstrip("|")

            # Filtrar df limpio (listo para inserción)
        df = df.loc[~mask_any_critical].copy()

        # Reglas permitidas 
            # company_name -->  company_id y "unknown"
        df["company_name"] = df["company_name"].replace({"": pd.NA, "nan": pd.NA, "<NA>": pd.NA})
        df["company_name"] = df["company_name"].fillna(
            df.groupby("company_id")["company_name"].transform("first")
        )
        df["company_name"] = df["company_name"].fillna("unknown")

        # 6 guardar los df
        print(f"Total original: {len(df_original)}")
        print(f"Total clean: {len(df)}")
        print(f"Total critical: {len(df_critical)}")

        df_clean_path = os.path.join(base_dir, "df_clean.csv")
        df_critical_path = os.path.join(base_dir, "df_critical.csv")

        df.to_csv(df_clean_path, index=False)
        df_critical.to_csv(df_critical_path, index=False)

    except Exception as e_limpieza:
        print(f"Error al abrir o transformar datos: {e_limpieza}")
        return

    # LOAD A CRAGA MYSQL
    # 7. construiir df para tabla companies y charges
    companies_df = df[["company_id", "company_name"]].drop_duplicates()
    charges_df = df[["id", "company_id", "amount", "status", "created_at", "updated_at"]].copy()
    
    # 8. carga a bd
    connection = None
    cursor = None
    try:
        connection = connect_to_database()
        cursor = connection.cursor()
        connection.autocommit = False

        # 8.1 Insertar companies evita duplicados
        cursor.executemany(
            """
            INSERT IGNORE INTO companies (company_id, company_name)
            VALUES (%s, %s)
            """,
            list(companies_df.itertuples(index=False, name=None))
        )

        # 8.2 Insertar/actualizar charges
        cursor.executemany(
            """
            INSERT INTO charges (id, company_id, amount, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            company_id = VALUES(company_id),
            amount = VALUES(amount),
            status = VALUES(status),
            created_at = VALUES(created_at),
            updated_at = VALUES(updated_at)
            """,
            [
                (
                    row.id,
                    row.company_id,
                    float(row.amount),
                    row.status,
                    row.created_at.to_pydatetime(),
                    None if pd.isna(row.updated_at) else row.updated_at.to_pydatetime(),
                )
                for row in charges_df.itertuples(index=False)
            ]
        )

        connection.commit()
        print(f"Companies insertadas: {len(companies_df)}")
        print(f"Charges insertadas/actualizadas: {len(charges_df)}")

    except Error as e:
        if connection:
            connection.rollback()
        print(f"Error al conectar o insertar datos en la base de datos: {e}")

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
        print("Conexión a la base de datos cerrada")


if __name__ == "__main__":
    main()