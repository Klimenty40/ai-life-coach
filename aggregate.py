#!/usr/bin/env python3
from backend.db import init_db, aggregate_daily_metrics

if __name__ == "__main__":
    # Убедимся, что все таблицы созданы
    init_db()
    # Запускаем агрегацию
    print("Start aggregation for yesterday...")
    aggregate_daily_metrics()
    print("Done.")
