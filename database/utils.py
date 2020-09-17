import pymysql as sql
import constants


def get_connection():
    return sql.connect(host=constants.db_host,
                       user=constants.db_user,
                       passwd=constants.db_password,
                       db=constants.db,
                       autocommit=True)


async def get_async_pool():
    pool = await aiomysql.create_pool(
        host=constants.db_host,
        user=constants.db_user,
        password=constants.db_password,
        db=constants.db,
        autocommit=True
    )
    return pool


def any_is_empty(*args) -> bool:
    return any(bool(arg) is False for arg in args)
