# Use PyMySQL as the MySQL driver when mysqlclient is not installed (easy on Windows).
try:
    import MySQLdb  # noqa: F401  (mysqlclient present -> nothing to do)
except ImportError:
    try:
        import pymysql

        pymysql.version_info = (2, 2, 1, "final", 0)  # satisfy Django's minimum mysqlclient version check
        pymysql.install_as_MySQLdb()
    except ImportError:
        pass
