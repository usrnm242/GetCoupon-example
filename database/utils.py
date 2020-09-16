import pymysql as sql
import constants


def get_connection():
    return sql.connect(host=constants.db_host,
                       user=constants.db_user,
                       passwd=constants.db_password,
                       db=constants.db,
                       autocommit=True)


def any_is_empty(*args) -> bool:
    return any(bool(arg) is False for arg in args)
