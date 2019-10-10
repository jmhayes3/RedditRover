import atexit

from core.redditrover import RedditRover
from core.db import shutdown_session, init_db, db_session
from core.models import *


if __name__ == "__main__":
    # Remove session when the program exits.
    atexit.register(shutdown_session)

    init_db()

    # new_module = Module(name="rover")
    # new_module2 = Module(name="rover2")
    # db_session.add(new_module)
    # db_session.add(new_module2)
    # db_session.commit()

    # Start.
    rr = RedditRover()
