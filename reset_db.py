from backend.db import engine, init_db
# удаляет старую схему (если она была)
from sqlmodel import SQLModel
SQLModel.metadata.drop_all(engine)
# создаёт все таблицы заново
init_db()
print("База сброшена и таблицы созданы")