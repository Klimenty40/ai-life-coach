from backend.db import save_event, aggregate_daily_metrics
from backend.db import get_weekly_metrics
from datetime import datetime, timedelta, timezone

# Подставьте свой реальный user_id
uid = 1081881720

# Добавляем данные за вчера и позавчера
for days_ago in (2, 1):
    ts = datetime.now(timezone.utc) - timedelta(days=days_ago)
    save_event(uid, "sleep", 400 + days_ago*10, ts=ts)
    save_event(uid, "screen", 200 + days_ago*5, ts=ts)
    save_event(uid, "steps", 5000 + days_ago*500, ts=ts)
    aggregate_daily_metrics(target_date=ts.date())

# Проверяем get_weekly_metrics
week = get_weekly_metrics(uid, datetime.now(timezone.utc).date())
for m in week:
    print(f"{m.date}: sleep={m.total_sleep}, screen={m.total_screen}, steps={m.total_steps}")
