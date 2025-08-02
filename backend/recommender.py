# backend/recommender.py
import os
import openai
from datetime import date
from backend.db import DailyMetric, get_daily_metrics_for_date
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

async def generate_recommendations(metric: DailyMetric) -> str:
    prompt = f"""
У пользователя {metric.user_id} по состоянию на {metric.date.isoformat()}:
- Сон: {int(metric.total_sleep)} мин
- Экран: {int(metric.total_screen)} мин
- Шаги: {int(metric.total_steps)} шт

Дайте 3 коротких конкретных рекомендаций, как улучшить эти показатели завтра.
Ответ оформите нумерованным списком.
"""
    # новый метод для openai>=1.0.0:
    resp = openai.chat.completions.create(
        model="o4-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0.7,
    )
    return resp.choices[0].message.content.strip()
