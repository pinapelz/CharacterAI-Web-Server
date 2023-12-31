import mysql.connector
from mysql.connector import Error, errorcode
import sshtunnel

sshtunnel.SSH_TIMEOUT = 5.0
sshtunnel.TUNNEL_TIMEOUT = 5.0

class SQLHandler:
    def __init__(self, host_name: str, user_name: str, user_password: str, database_name: str = None, ssh_host: str = None, ssh_username: str = None, ssh_password: str = None, ssh_remote_bind: str = None):
        self.host_name = host_name
        self.username = user_name
        self.password = user_password
        self.database_name = database_name
        if ssh_host is None or ssh_username is None or ssh_password is None:
            self.connection = self._create_server_connection(
                host_name, user_name, user_password)
        else:
            self.connection = self._create_ssh_server_connection(
                ssh_host, ssh_username, ssh_password, ssh_remote_bind, host_name, user_name, user_password)
        if database_name is not None:
            self._load_database(database_name)

    def _create_server_connection(self, host_name: str, user_name: str, user_password: str) -> mysql.connector:
        connection = None
        try:
            connection = mysql.connector.connect(host=host_name, user=user_name, passwd=user_password, charset="utf8mb4")
            print("MySQL Database connection successful")
        except Error as err:
            print(f"Error: '{err}'")
        return connection

    def _create_ssh_server_connection(self, ssh_host:str, ssh_username: str, ssh_password: str, remote_bind:str, host_name: str, user_name: str, user_password: str) -> mysql.connector:
        connection = None
        try:
            self._tunnel = sshtunnel.SSHTunnelForwarder(
                (ssh_host),
                ssh_username=ssh_username,
                ssh_password=ssh_password,
                remote_bind_address=(remote_bind, 3306),
            )
            self._tunnel.start()
            print("SSH connection successful")
            connection = mysql.connector.connect(
                host=host_name,
                user=user_name,
                passwd=user_password,
                port=self._tunnel.local_bind_port,
                database=self.database_name,
            )
            print("MySQL Database connection successful")
        except Error as err:
            print(f"Error: '{err}'")
        if connection is None:
            print("Connection failed")
            exit(1)
        return connection

    def get_connection(self):
        return self.connection

    def _create_database(self, cursor: str, database_name: str):
        try:
            cursor.execute(
                f"CREATE DATABASE {database_name} DEFAULT CHARACTER SET 'utf8'")
        except Error as err:
            print(f"Failed creating database: {err}")
            exit(1)

    def _load_database(self, database_name: str):
        try:
            cursor = self.connection.cursor(buffered=True)
        except Error as err:
            print(f"Failed to load database: {err}")
            exit(1)
        try:
            cursor.execute(f"USE {database_name}")
            print(f"Database {database_name} loaded successfully")
        except Error as err:
            print(f"Database {database_name} does not exist")
            if err.errno == errorcode.ER_BAD_DB_ERROR:
                self._create_database(cursor, database_name)
                print(f"Database {database_name} created successfully")
                self.connection.database = database_name
            else:
                print(err)
                exit(1)

    def create_table(self, name: str, column: str):
        cursor = self.connection.cursor(buffered=True)
        try:
            cursor.execute(f"CREATE TABLE {name} ({column})")
            print(f"Table {name} created successfully")
        except Error as err:
            print(err)

    def insert_row(self, table_name: str, column: str, data: tuple):
        cursor = self.connection.cursor(buffered=True)
        try:
            placeholders = ', '.join(['%s'] * len(data))
            query = f"INSERT INTO {table_name} ({column}) VALUES ({placeholders})"
            cursor.execute(query, data)
            self.connection.commit()
            print("Data Inserted:", data)
        except Error as err:
            print("Error inserting data")
            print(err)
            if err not in ("Duplicate entry", "Duplicate entry for key 'PRIMARY'"):
                return False
        return True

    def close_connection(self):
        if self.connection.is_connected():
            if hasattr(self, '_tunnel'):
                self._tunnel.stop()
            self.connection.close()
            print("MySQL connection is closed")


    def clear_table(self, name: str):
        cursor = self.connection.cursor(buffered=True)
        try:
            cursor.execute(f"DELETE FROM {name}")
            self.connection.commit()
            print("Table cleared successfully")
        except Error as err:
            print("Error clearing table")
            print(err)

    def reset_auto_increment(self, name: str):
        cursor = self.connection.cursor(buffered=True)
        try:
            cursor.execute(f"ALTER TABLE {name} AUTO_INCREMENT = 1")
            self.connection.commit()
            print("Table reset successfully")
        except Error as err:
            print("Error resetting table")
            print(err)

    def copy_rows_to_new_table(self, name: str, new_name: str, column: str):
        cursor = self.connection.cursor(buffered=True)
        try:
            cursor.execute(
                f"INSERT INTO {new_name} ({column}) SELECT {column} FROM {name}")
            cursor.execute(
                f"ALTER TABLE {new_name} MODIFY COLUMN id INT AUTO_INCREMENT")
            self.connection.commit()
            print("Rows copied successfully")
        except Error as err:
            print("Error copying rows")
            print(err)

    def drop_table(self, name: str):
        cursor = self.connection.cursor(buffered=True)
        try:
            cursor.execute(f"DROP TABLE {name}")
            self.connection.commit()
            print("Table dropped successfully")
        except Error as err:
            print("Error dropping table")
            print(err)

    def check_row_exists(self, table_name: str, column_name: str, value: str):
        """
        Checks if a row exists in a table
        """
        cursor = self.connection.cursor(buffered=True)
        try:
            cursor.execute(f"SELECT * FROM {table_name} WHERE {column_name} = '{value}'")
            result = cursor.fetchone()
            if result:
                return True
            else:
                return False
        except Error as err:
            print("Error checking row")
            print(err)

    def update_row(self, name: str, column_name: str, search_val: str, replace_col:str, new_value: str):
        """
        Updates a row in a table
        """
        cursor = self.connection.cursor(buffered=True)
        try:
            cursor.execute(f"UPDATE {name} SET {replace_col} = '{new_value}' WHERE {column_name} = '{search_val}'")
            self.connection.commit()
            print("Row updated successfully")
        except Error as err:
            print("Error updating row")
            print(err)

    def execute_query(self, query: str):
        cursor = self.connection.cursor(buffered=True)
        try:
            cursor.execute(query)
            result = cursor.fetchall()
            return result
        except Error as err:
            print("Error executing query")
            print(err)

    def get_query_result(self, query: str):
        cursor = self.connection.cursor(buffered=True)
        try:
            cursor.execute(query)
            result = cursor.fetchall()
            return result
        except Error as err:
            print("Error executing query")
            print(err)

    def delete_row(self, name: str, column: str, data: tuple):
        cursor = self.connection.cursor()
        try:
            query = f"DELETE FROM {name} WHERE {column} = %s"
            cursor.execute(query, data)
            self.connection.commit()
            print("Data Deleted:", data)
        except Error as err:
            print("Error deleting data")
            print(err)
            return False
        return True

    def get_rows(self, table_name: str, column: str, value: str):
        cursor = self.connection.cursor(buffered=True)
        try:
            query = f"SELECT * FROM {table_name} WHERE {column} = %s"
            cursor.execute(query, (value,))
            result = cursor.fetchall()
            return result
        except Error as err:
            print("Error getting row")
            print(err)

    def get_random_row(self,table_name: str, limit: int = 1):
        cursor = self.connection.cursor(buffered=True)
        try:
            cursor.execute(f"SELECT * FROM {table_name} ORDER BY RAND() LIMIT {str(limit)}")
            result = cursor.fetchall()
            return result
        except Error as err:
            print("Error getting random row")
            print(err)

    def search_video_row(self, table_name: str, keywords: list, limit: int = 1, offset: int = 0):
        cursor = self.connection.cursor(buffered=True)
        query = f"SELECT * FROM {table_name} WHERE 1=1"
        keyword_conditions = []

        for keyword in keywords:
            keyword_condition = f"LOWER(title) LIKE %s"
            formatted_keyword = f"%{keyword.lower()}%"
            keyword_conditions.append((keyword_condition, formatted_keyword))
        if keyword_conditions:
            query += " AND " + " AND ".join([condition[0] for condition in keyword_conditions])

        query += " LIMIT %s OFFSET %s"

        try:
            cursor.execute(query, ([condition[1] for condition in keyword_conditions] + [limit, offset]))
            result = cursor.fetchall()
            return result
        except Error as err:
            print("Error searching video row")
            print(err)



