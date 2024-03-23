import os


database_uri = (os.environ.get('DATABASE_URI') is None and
                'sqlite+aiosqlite:///./sql_app.sqlite' or os.environ.get('DATABASE_URI'))


__all__ = ['utils', 'database_uri',]
