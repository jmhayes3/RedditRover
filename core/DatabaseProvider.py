import logging
import sqlite3
from pkg_resources import resource_filename


class DatabaseProvider:
    logger = None   # Logger
    db = None       # Reference to DB session
    cur = None      # Reference to DB cursor

    def __init__(self):
        self.logger = logging.getLogger("database")
        self.db = sqlite3.connect(
            resource_filename("core.config", "storage.db"),
            check_same_thread=False,
            isolation_level=None
        )
        self.cur = self.db.cursor()
        self.database_init()

    def __del__(self):
        self.db.close()
        self.logger.warning("DB connection has been closed.")

    def database_init(self):
        if not self.__database_check_if_exists('storage'):
            self.cur.execute(
                'CREATE TABLE IF NOT EXISTS storage (thing_id STR(10), bot_module STR(50), timestamp datetime)'
            )
            self.logger.info("Table 'storage' had to be generated.")

        if not self.__database_check_if_exists('update_threads'):
            self.cur.execute(
                'CREATE TABLE IF NOT EXISTS update_threads '
                '(thing_id STR(10) NOT NULL, bot_module INT(5), created DATETIME, '
                'lifetime DATETIME, last_updated DATETIME, interval INT(5))'
            )

        if not self.__database_check_if_exists('modules'):
            self.cur.execute(
                'CREATE TABLE IF NOT EXISTS modules '
                '(module_name STR(50))'
            )

    def __database_check_if_exists(self, table_name):
        """Helper method, Internal check if a table exists, refrain from using it."""
        self.cur.execute('SELECT name FROM sqlite_master WHERE type="table" AND name=(?)', (table_name,))
        return self.cur.fetchone()

    def insert_into_storage(self, thing_id, module):
        """Stores a certain thing (comment or submission) into the storage, which is for session consistency."""
        self.cur.execute('INSERT INTO storage VALUES ((?), (SELECT _ROWID_ FROM modules WHERE module_name=(?)), '
                         'CURRENT_TIMESTAMP)', (thing_id, module))

    def get_all_storage(self):
        """Returns all elements inside the bot storage."""
        self.__error_if_not_exists(module)
        self.cur.execute("""SELECT thing_id, module_name, timestamp FROM storage
                            INNER JOIN modules
                            ON storage.bot_module = modules._ROWID_""")
        return self.cur.fetchall()

    def get_thing_from_storage(self, thing_id, module):
        self.__error_if_not_exists(module)
        self.cur.execute("""SELECT thing_id, module_name, timestamp FROM storage
                            WHERE thing_id = (?)
                            AND module_name = (SELECT _ROWID_ FROM modules WHERE module_name=(?))
                            MAX 1""",
                         (thing_id, module,))
        return self.cur.fetchone()

    def delete_from_storage(self, min_timestamp):
        """Deletes _all_ items which are older than a certain timestamp"""
        self.cur.execute("DELETE FROM storage WHERE timestamp <= datetime((?), 'unixepoch')", (min_timestamp,))

    def select_from_storage(self, older_than_timestamp):
        """:param older_than_timestamp: Select all elements in the storage that are older than this timestamp."""
        self.cur.execute("SELECT * FROM storage WHERE timestamp <= datetime((?), 'unixepoch')", (older_than_timestamp,))
        return self.cur.fetchall()

    def insert_into_update(self, thing_id, module, lifetime, interval):
        """Inserts a thing (comment or submission) into the update-table, which calls a module for update-actions."""
        self.__error_if_not_exists(module)
        self.cur.execute("""
                        INSERT INTO update_threads (thing_id, bot_module, created, lifetime, last_updated, interval)
                            VALUES (
                                (?),
                                (SELECT _ROWID_ FROM modules WHERE module_name=(?)),
                                CURRENT_TIMESTAMP,
                                datetime('now', '+' || (?) || ' seconds'),
                                CURRENT_TIMESTAMP,
                                (?))
                         """,
                         (thing_id, module, lifetime, interval,))

    def get_all_update(self):
        """Returns all elements inside the update_threads table"""
        self.__error_if_not_exists(module)
        self.cur.execute("""SELECT thing_id, module_name, created, lifetime, last_updated, interval
                            FROM update_threads
                            INNER JOIN modules
                            ON update_threads.bot_module = modules._ROWID_
                            ORDER BY last_updated ASC""")
        return self.cur.fetchall()

    def __select_to_update(self, module):
        """Helper method, refrain from using it."""
        self.__error_if_not_exists(module)
        self.cur.execute("""SELECT thing_id, module_name, created, lifetime, last_updated, interval
                            FROM update_threads
                            INNER JOIN modules
                            ON update_threads.bot_module = modules._ROWID_
                            WHERE modules.module_name = (?)
                            AND CURRENT_TIMESTAMP > (datetime(update_threads.last_updated,
                                                                '+' || update_threads.interval || ' seconds'))
                            ORDER BY last_updated ASC""",
                         (module,))

    def get_latest_to_update(self, module):
        """Returns a single thing (comment or submission) for a module."""
        self.__select_to_update(module)
        return self.cur.fetchone()

    def get_all_to_update(self, module):
        """Returns _all_ things (comments or submissions) for a module."""
        self.__select_to_update(module)
        self.cur.fetchall()

    def update_timestamp_in_update(self, thing_id, module):
        """Updates the timestamp when a thing was updated last."""
        self.__error_if_not_exists(module)
        self.cur.execute("""UPDATE update_threads
                            SET last_updated=CURRENT_TIMESTAMP
                            WHERE thing_id=(?)
                            AND bot_module = (SELECT _ROWID_ FROM modules WHERE module_name = (?))""",
                         (thing_id, module))

    def delete_from_update(self, thing_id, module):
        """Deletes _all_ things (comments or submissions) for a module when it outlived its lifetime."""
        self.__error_if_not_exists(module)
        self.cur.execute("""DELETE FROM update_threads
                            WHERE thing_id=(?)
                            AND bot_module = (SELECT _ROWID_ FROM modules WHERE module_name = (?))
                            AND CURRENT_TIMESTAMP > lifetime""", (thing_id, module))

    def register_module(self, module):
        """Registers a module (or notifies you if it has been already registered)."""
        if self.__check_if_module_exists(module):
            self.logger.error("Module is already registered.")
            return
        self.logger.debug("Module {} has been registered.".format(module))
        self.cur.execute('INSERT INTO modules VALUES ((?))', (module,))

    def __check_if_module_exists(self, module):
        """Helper method to determine if a module has been already registered. Refrain from using it."""
        self.cur.execute('SELECT COUNT(*) FROM modules WHERE module_name = (?)', (module,))
        if self.cur.fetchone()[0] == 0:
            return False
        if self.cur.fetchone()[1] == 1:
            return True
        if self.cur.fetchone()[1] > 1:
            raise ValueError("A module was registered multiple times and is therefore inconsistent. Call for help.")

    def __error_if_not_exists(self, module):
        """Helper method for throwing a concrete error if a module has not been registered, yet a critical database
           task should have been accomplished."""
        if not self.__check_if_module_exists(module):
            raise LookupError('The module where this operation comes from is not registered!')

    def get_all_modules(self):
        """Returns all modules that have been registered."""
        self.cur.execute('SELECT _ROWID_, module_name FROM modules')
        return self.cur.fetchall()

    def clean_up_database(self, older_than_unixtime):
        """Cleans up the database, meaning that everything older than the session time and all threads that should
           be updated and outlived their lifetime will be deleted."""
        self.cur.execute("""DELETE FROM storage WHERE timestamp < datetime((?), 'unixepoch')""", (older_than_unixtime,))
        self.cur.execute("""DELETE FROM update_threads WHERE CURRENT_TIMESTAMP > lifetime""")

    def wipe_module(self, module):
        """Wipes a module entirely across from all tables."""
        self.cur.execute("""DELETE FROM storage
                            WHERE bot_module = (SELECT _ROWID_ FROM modules WHERE module_name = (?))""", (module,))
        self.cur.execute("""DELETE FROM update_threads
                            WHERE bot_module = (SELECT _ROWID_ FROM modules WHERE module_name = (?))""", (module,))
        self.cur.execute("""DELETE FROM modules WHERE module_name = (?)""", (module,))


if __name__ == "__main__":
    db = DatabaseProvider()
    thing_id = "t2_c384fd"
    module = "MassdropBot"
#   Commands that work:
#   >> Storage
#   db.insert_into_storage(thing_id, module)
#   print(db.get_all_storage())
#   print(db.select_from_storage(int(time())))
#
#   >> Module Register
#   db.register_module(module)
#   print(db.get_all_modules())
#
#   >> update_threads
#   db.insert_into_update(thing_id, module, 600, 15)
#   print(db.get_latest_to_update('MassdropBot'))
#   print(db.get_all_update())
#   db.update_timestamp_in_update(thing_id, module)
#   db.delete_from_update(thing_id, module)
#
#   >> Cleanup
#   db.clean_up_database(int(time()) - 30)
#   db.wipe_module(module)
#
#   >> Printing out the current state of all tables
    print(db.get_all_update())
    print(db.get_all_storage())
    print(db.get_all_modules())