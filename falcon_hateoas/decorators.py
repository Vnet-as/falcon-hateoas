def db_session(fn):
    def func(*args, **kwargs):
        sesmaker = args[0].sessionmaker
        session = sesmaker()
        fn(*args, dbsession=session, **kwargs)
        session.close()
    return func
