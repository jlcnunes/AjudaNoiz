import mysql.connector

Config = {
    'user': 'ajudanoizapp_admin',
    'password': '@ss1st3nc14S3gvra!',
    'host': 'localhost',
    'database': 'ajudanoizapp_db'
}

def executar_autoteste():
    connection = mysql.connector.connect(**Config)
    cursor = connection.cursor()

    try:
       print("Iniciando autoteste...")
       connection.start_transaction()

       CREATE 

