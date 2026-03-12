import psycopg2

conn = psycopg2.connect(
    dbname="options_db",
    user="quant_user",
    password="strong_password",
    host="144.91.73.49",
    port="5432"
)

cursor = conn.cursor()
cursor.execute("SELECT * FROM underlyings;")
print(cursor.fetchall())