from datetime import datetime, date, timezone, timedelta
from typing import Optional, List

from sqlmodel import SQLModel, Field, create_engine, Session, select

# ─── Database setup ───────────────────────────────────────────────────────────

engine = create_engine("sqlite:///data.db", echo=False)

def init_db() -> None:
    """
    Создаёт все таблицы моделей, если их нет.
    """
    SQLModel.metadata.create_all(engine)


# ─── Models ───────────────────────────────────────────────────────────────────

class RawEvent(SQLModel, table=True):
    """Сырые события от пользователя: сон, экранное время, шаги."""
    id:       Optional[int] = Field(default=None, primary_key=True)
    user_id:  int
    event:    str      # 'sleep' | 'screen' | 'steps'
    value:    float    # минуты для сна/экрана, количество шагов
    ts:       datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp события в UTC"
    )


class DailyMetric(SQLModel, table=True):
    """Агрегированные ежедневные итоги по каждому пользователю."""
    id:           Optional[int] = Field(default=None, primary_key=True)
    user_id:      int
    date:         date          # дата агрегации
    total_sleep:  float = Field(default=0.0)
    total_screen: float = Field(default=0.0)
    total_steps:  float = Field(default=0.0)
    mood: Optional[int] = Field(default=None, description="1…4, последнее значение за день")

class UserSettings(SQLModel, table=True):
    """Настройки пользователя: время рассылки, пропуск выходных, лимит запросов."""
    user_id:             int            = Field(default=None, primary_key=True)
    report_hour:         int            = Field(default=8)
    report_min:          int            = Field(default=0)
    skip_weekends:       bool           = Field(default=False)
    last_report_request: Optional[date] = None


class Feedback(SQLModel, table=True):
    """Отзывы пользователей (👍/👎) по рекомендациям."""
    id:         Optional[int] = Field(default=None, primary_key=True)
    user_id:    int
    date:       date          # дата отчёта, к которому привязан фидбэк
    positive:   bool

class UserProfile(SQLModel, table=True):
    user_id: int = Field(primary_key=True, index=True)
    sex: str  # "male" / "female"
    height_cm: int
    weight_kg: int
    age_group: str  # "18-25" ...
    goal: str  # "lose" / "gain" / "maintain"
    imt: float | None

# ─── Settings CRUD ────────────────────────────────────────────────────────────

def get_settings(user_id: int) -> UserSettings:
    """
    Возвращает настройки пользователя, создавая их по умолчанию, если нет.
    """
    with Session(engine) as sess:
        settings = sess.get(UserSettings, user_id)
        if settings is None:
            settings = UserSettings(user_id=user_id)
            sess.add(settings)
            sess.commit()
            sess.refresh(settings)
        return settings


def update_settings(
    user_id: int,
    hour: Optional[int] = None,
    minute: Optional[int] = None,
    skip_weekends: Optional[bool] = None
) -> None:
    """
    Обновляет поля в UserSettings.
    """
    with Session(engine) as sess:
        settings = get_settings(user_id)
        if hour is not None:
            settings.report_hour = hour
        if minute is not None:
            settings.report_min = minute
        if skip_weekends is not None:
            settings.skip_weekends = skip_weekends
        sess.add(settings)
        sess.commit()


def get_last_report_request(user_id: int) -> Optional[date]:
    """
    Возвращает дату последнего запроса ежедневного отчёта.
    """
    settings = get_settings(user_id)
    return settings.last_report_request


def set_last_report_request(user_id: int, req_date: date) -> None:
    """
    Сохраняет дату запроса ежедневного отчёта.
    """
    with Session(engine) as sess:
        settings = sess.get(UserSettings, user_id)
        settings.last_report_request = req_date
        sess.add(settings)
        sess.commit()


# ─── Event CRUD ───────────────────────────────────────────────────────────────

def save_event(user_id: int, event: str, value: float) -> None:
    """
    Сохраняет новое событие и сразу обновляет DailyMetric за сегодня.
    """
    ts = datetime.now(timezone.utc)
    today = ts.date()

    with Session(engine) as sess:
        # 1) Сохраняем сырое событие
        raw = RawEvent(user_id=user_id, event=event, value=value, ts=ts)
        sess.add(raw)
        sess.commit()

        # 2) Получаем или создаём агрегат за сегодня
        stmt = select(DailyMetric).where(
            DailyMetric.user_id == user_id,
            DailyMetric.date == today
        )
        dm = sess.exec(stmt).first()
        if dm is None:
            dm = DailyMetric(user_id=user_id, date=today)

        # 3) Инкрементируем нужное поле
        if event == "sleep":
            dm.total_sleep += value
        elif event == "screen":
            dm.total_screen += value
        elif event == "steps":
            dm.total_steps += value

        # 3. Записываем только последний ввод (перезаписываем предыдущее значение)

        if event == "sleep":
            dm.total_sleep = value
        elif event == "screen":
            dm.total_screen = value
        elif event == "steps":
            dm.total_steps = value
        elif event == "mood":
            dm.mood = int(value)

        # 4) Сохраняем агрегат
        sess.add(dm)
        sess.commit()


def save_feedback(user_id: int, target_date: date, positive: bool) -> None:
    """
    Сохраняет отзыв пользователя по дате отчёта.
    """
    fb = Feedback(user_id=user_id, date=target_date, positive=positive)
    with Session(engine) as sess:
        sess.add(fb)
        sess.commit()

# ─── Функция для создания или обновления профиля ────────────────────────
def create_profile(profile: dict) -> UserProfile:
    """
    profile должен содержать ключи:
      user_id, sex, height_cm, weight_kg, age_group, goal
    Вычисляет imt, сохраняет в БД и возвращает объект UserProfile.
    """
    # 1) Рассчитываем ИМТ
    h_m = profile["height_cm"] / 100.0
    imt = profile["weight_kg"] / (h_m * h_m)

    # 2) Готовим данные
    up = UserProfile(
        user_id    = profile["user_id"],
        sex        = profile["sex"],
        height_cm  = profile["height_cm"],
        weight_kg  = profile["weight_kg"],
        age_group  = profile["age_group"],
        goal       = profile["goal"],
        imt        = imt,
    )

    # 3) Сохраняем (INSERT или UPDATE)
    with Session(engine) as session:
        existing = session.exec(
            select(UserProfile).where(UserProfile.user_id == up.user_id)
        ).first()
        if existing:
            # обновляем поля
            existing.sex       = up.sex
            existing.height_cm = up.height_cm
            existing.weight_kg = up.weight_kg
            existing.age_group = up.age_group
            existing.goal      = up.goal
            existing.imt       = up.imt
            session.add(existing)
            session.commit()
            return existing
        else:
            session.add(up)
            session.commit()
            session.refresh(up)
            return up
# ─── Metrics Queries ──────────────────────────────────────────────────────────

def get_daily_metrics_for_date(target_date: date) -> List[DailyMetric]:
    """
    Возвращает все записи DailyMetric за указанную дату.
    """
    with Session(engine) as sess:
        stmt = select(DailyMetric).where(DailyMetric.date == target_date)
        return sess.exec(stmt).all()


def get_weekly_metrics(user_id: int, end_date: date) -> List[DailyMetric]:
    """
    Возвращает список DailyMetric за 7-дневный период до end_date включительно.
    """
    start = end_date - timedelta(days=6)
    with Session(engine) as sess:
        stmt = (
            select(DailyMetric)
            .where(DailyMetric.user_id == user_id)
            .where(DailyMetric.date >= start)
            .where(DailyMetric.date <= end_date)
            .order_by(DailyMetric.date)
        )
        return sess.exec(stmt).all()

# def init_db(drop: bool = False):
#     """
#     Если drop=True — удаляет все таблицы и пересоздаёт.
#     Иначе — только создаёт отсутствующие.
#     """
#     from sqlmodel import SQLModel
#     if drop:
#         SQLModel.metadata.drop_all(engine)
#     SQLModel.metadata.create_all(engine)

def get_user_profile(user_id: int) -> UserProfile | None:
    with Session(engine) as session:
        return session.exec(
            select(UserProfile).where(UserProfile.user_id == user_id)
        ).first()