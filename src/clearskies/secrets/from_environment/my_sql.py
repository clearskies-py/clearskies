from clearskies import Configurable, decorators
import clearskies.configs
from clearskies.di import inject, InjectableProperties

class MySql(Configurable, InjectableProperties):
    hostname_environment_key = clearskies.configs.String(default="DATABASE_HOST")
    username_environment_key = clearskies.configs.String(default="DATABASE_USERNAME")
    password_environment_key = clearskies.configs.String(default="DATABASE_PASSWORD")
    database_environment_key = clearskies.configs.String(default="DATABASE_NAME")
    port_environment_key = clearskies.configs.String(default="DATABASE_PORT")
    default_port = clearskies.configs.Integer(default=3306)
    cert_path_environment_key = clearskies.configs.String(default="DATABASE_CERT_PATH")
    port_forwarding = clearskies.configs.Any(default=None)

    environment = inject.Environment()

    table_escape_character="`"
    column_escape_character="`"
    value_placeholder="%s"
    _cursor = None

    @decorators.parameters_to_properties
    def __init__(
        self,
        hostname_environment_key="DATABASE_HOST",
        username_environment_key="DATABASE_USERNAME",
        password_environment_key="DATABASE_PASSWORD",
        database_environment_key="DATABASE_NAME",
        port_environment_key="DATABASE_PORT",
        cert_path_environment_key="DATABASE_CERT_PATH",
        port_forwarding=None,
    ):
        pass

    @property
    def cursor(self):
        if not self._cursor:
            import pymysql

            # if self.port_forwarding:
            #     self.port_forwarding

            connection_kwargs = {
                "user": self.environment.get(self.username_environment_key),
                "password": self.environment.get(self.password_environment_key),
                "host": self.environment.get(self.hostname_environment_key),
                "database": self.environment.get(self.database_environment_key),
                "port": self.environment.get(self.port_environment_key, silent=True),
                "ssl_ca": self.environment.get(self.cert_path_environment_key, silent=True),
            }
            if not connection_kwargs["port"]:
                connection_kwargs["port"] = self.default_port

            self._cursor = pymysql.connect(
                **connection_kwargs
                ssl_ca=connection_details.get("ssl_ca", None),
                autocommit=True,
                connect_timeout=2,
                cursorclass=pymysql.cursors.DictCursor,
            )

        return self._cursor

    def column_equals_with_placeholder(self, column_name):
        return f"{self.column_escape_character}{column_name}={self.value_placeholder}"

    def as_sql_with_placeholders(self, table, column, operator, number_values=1):
        if number_values == 1:
            return f"{table}.{column} {operator} {self.value_placeholder}"

    def execute(self, sql, parameters):
        return self.cursor.execute(sql, parameters)
