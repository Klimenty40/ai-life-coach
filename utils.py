
import re
from typing import Optional


def parse_time_to_minutes(text: str) -> float:
    """
    Преобразует строку в минуты. Поддерживается:
     - "7h15m" или "7h15" 
     - "7:15"
     - "7.25"  (где дробная часть – это часы)
    """
    s = text.strip().lower()

    # формат 7h15m или 7h15
    m = re.match(r'^(?:(?P<h>\d+)(?:h))?(?P<m>\d+)(?:m)?$', s)
    if m:
        hours = int(m.group('h') or 0)
        mins = int(m.group('m'))
        return hours * 60 + mins

    # формат 7:15
    m = re.match(r'^(?P<h>\d+):(?P<m>\d{1,2})$', s)
    if m:
        return int(m.group('h')) * 60 + int(m.group('m'))

    # формат 7.25 (где .25 части часа)
    m = re.match(r'^(?P<val>\d+(?:\.\d+)?)$', s)
    if m:
        return float(m.group('val')) * 60

    raise ValueError(
        f"Неподдерживаемый формат времени '{text}'.\n"
        "Используйте, например: '7h15m', '7:15' или '7.25'."
    )


def format_minutes_to_human(minutes: float) -> str:
    """
    Преобразует число минут в читаемый формат, например:
     - 135  → "2h15m"
     -  45  → "45m"
    """
    mins = int(minutes)
    hours, m = divmod(mins, 60)
    if hours:
        return f"{hours}h{m:02d}m"
    return f"{m}m"


def safe_int(text: str) -> Optional[int]:
    """
    Пытается перевести строку в int, возвращает None при неудаче.
    Обычно используется для обработки /steps.
    """
    try:
        return int(text.strip())
    except (ValueError, AttributeError):
        return None
