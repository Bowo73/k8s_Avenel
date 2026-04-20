import pandas as pd
from sqlalchemy import create_engine
import pymysql
import os

DB_HOST = os.getenv("DB_HOST")
DB_PORT = 3306
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_DATABASE = os.getenv("DB_DATABASE")

csv_to_use = [
    {
        "table_name": "stars",
        "csv_path": "/tmp/hyg_v42.csv"
    },
    {
        "table_name": "cities",
        "csv_path": "/tmp/worldcities.csv"
    }
]

db_engine = create_engine(
    f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_DATABASE}",
    echo=False
)
for csv in csv_to_use:
    df = pd.read_csv(csv["csv_path"])

    df.to_sql(
        csv["table_name"],
        con=db_engine,
        if_exists="replace",
        index=False,
        chunksize=1000,
        method="multi"
    )
