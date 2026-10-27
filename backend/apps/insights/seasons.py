"""Mavsum oylaridan joriy holatni aniqlash. Yil oshib o'tadigan mavsumlar (Qish: 12 -> 2) ham qo'llab-quvvatlanadi."""
import calendar
from dataclasses import dataclass
from datetime import date


@dataclass
class SeasonState:
    in_season: bool
    days_to_end: int | None  # mavsum ichida bo'lsa, tugashiga qolgan kunlar
    days_to_start: int | None  # mavsumdan tashqarida bo'lsa, keyingi boshlanishgacha

    def label(self, name: str) -> str:
        if self.in_season:
            return f"{name}: mavsum davom etmoqda, tugashiga {self.days_to_end} kun"
        return f"{name}: mavsumdan tashqari, boshlanishiga {self.days_to_start} kun"


def _months(start: int, end: int) -> list[int]:
    if start <= end:
        return list(range(start, end + 1))
    return list(range(start, 13)) + list(range(1, end + 1))


def season_state(start_month: int, end_month: int, today: date) -> SeasonState:
    months = _months(start_month, end_month)
    if today.month in months:
        # Joriy mavsum tugaydigan yil: yil oshib o'tsa va hozir boshlanish qismida bo'lsak, keyingi yil.
        end_year = today.year + (1 if start_month > end_month and today.month >= start_month else 0)
        end_date = date(end_year, end_month, calendar.monthrange(end_year, end_month)[1])
        return SeasonState(True, (end_date - today).days, None)
    start_year = today.year if start_month > today.month else today.year + 1
    return SeasonState(False, None, (date(start_year, start_month, 1) - today).days)
