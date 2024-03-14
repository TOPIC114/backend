# backend
the backend of services

Require fastapi, sqlalchemy and uvicorn to run this program,use:
```bash
pip install fastapi sqlalchemy uvicorn alembic
```
to rebuild the environment after clone this repo,then switch to the virtural environment!

you can use miniconda3 or anaconda,btw!

# Database migration (or init)

### *Windows*
run
```bash
migration.bat
```
to migrate database.

### *\*NIX* 

run
```bash
./migration.sh
```
to migrate database.