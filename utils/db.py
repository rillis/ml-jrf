from cfg import config
import mysql.connector, uuid

class DBConnection:
    def __init__(self, host=None, port=None, user=None, password=None, database=None):
        host = host or config.DB_HOST
        port = port or config.DB_PORT
        user = user or config.DB_USER
        password = password or config.DB_PASSWORD
        database = database or config.DB_DATABASE
        self.id = str(uuid.uuid4())[:8]

        try:
            self.conn = mysql.connector.connect(
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    database=database
                )
            
            if config.DEBUG: print(f'MYSQL ({self.id}): Conexão feita com {host}:{port}')
        except mysql.connector.Error as err:
            self.conn = None
            config.print_error(f'Connector Error:', err)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()
    
    def execute(self, sql, val=None):
        if self.conn is None:
            raise Exception("Banco não conectado")
        
        self.conn.ping(reconnect=True)
        cursor = self.conn.cursor()
        try:
            cursor.execute(sql, val) if val is not None else cursor.execute(sql)
            self.conn.commit()
        finally:
            cursor.close()

        if config.DEBUG: print(f'MYSQL ({self.id}): Execução feita: {sql}')
    
    def fetch(self, sql, val=None):
        if self.conn is None:
            raise Exception("Banco não conectado")
        
        self.conn.ping(reconnect=True)
        cursor = self.conn.cursor(dictionary=True)
        try:
            cursor.execute(sql, val) if val is not None else cursor.execute(sql)
            result = cursor.fetchall()
        finally:
            cursor.close()

        if config.DEBUG: print(f'MYSQL ({self.id}): Consulta feita: {sql}')
        return result
    
    def close(self):
        if self.conn:
            self.conn.close()
            if config.DEBUG: print(f'MYSQL ({self.id}): Conexão fechada')
    

        
