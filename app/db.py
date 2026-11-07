"""Pool de conexões MySQL."""
import threading

import mysql.connector
from mysql.connector import pooling

from app import config, log

_logger = log.get('db')
_pool = None
_lock = threading.Lock()


def _get_pool():
    global _pool
    if _pool is None:
        with _lock:
            if _pool is None:
                _pool = pooling.MySQLConnectionPool(
                    pool_name='ml-jrf',
                    pool_size=config.DB_POOL_SIZE,
                    pool_reset_session=True,
                    host=config.DB_HOST,
                    port=config.DB_PORT,
                    user=config.DB_USER,
                    password=config.DB_PASSWORD,
                    database=config.DB_DATABASE,
                    charset='utf8mb4',
                    autocommit=True,
                    connection_timeout=10,
                )
                _logger.debug(f'MySQL: pool criado para {config.DB_HOST}:{config.DB_PORT}')
    return _pool


def _connection():
    conn = _get_pool().get_connection()
    conn.ping(reconnect=True, attempts=2, delay=1)
    return conn


def execute(sql, params=None):
    """Executa um comando e devolve o número de linhas afetadas."""
    conn = _connection()
    try:
        cur = conn.cursor()
        try:
            cur.execute(sql, params)
            return cur.rowcount
        finally:
            cur.close()
    finally:
        conn.close()


def fetch(sql, params=None):
    conn = _connection()
    try:
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(sql, params)
            return cur.fetchall()
        finally:
            cur.close()
    finally:
        conn.close()


Error = mysql.connector.Error
