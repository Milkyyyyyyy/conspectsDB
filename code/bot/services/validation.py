from dataclasses import dataclass
import re
from typing import Pattern, Optional

@dataclass
class Validator:
    pattern: Pattern
    message: str

    def check(self, text: str) -> bool:
        """Просто булево — совпадает ли полностью."""
        return bool(self.pattern.fullmatch(text))

    def validate(self, text: str) -> tuple[bool, Optional[str]]:
        """Возвращает (True, None) если OK, или (False, message) если нет."""
        ok = self.check(text)
        return (True, None) if ok else (False, self.message)

class Validators:
    def __init__(self):
        self._map: dict[str, Validator] = {}

    def add(self, name: str, pattern: str | Pattern, message: str, flags=0):
        pat = pattern if isinstance(pattern, re.Pattern) else re.compile(pattern, flags)
        self._map[name] = Validator(pat, message)

    def __getattr__(self, name: str) -> Validator:
        try:
            return self._map[name]
        except KeyError as e:
            raise AttributeError(f"No validator named {name!r}") from e

    def __getitem__(self, name: str) -> Validator:
        return self._map[name]

validators = Validators()
validators.add('name',
			   r"^[А-Яа-яA-Za-z\-]{2,30}$",
			   "<b>Некорректное имя.</b>\n"
			   "Оно должно содержать <b>только кириллицу или латиницу буквы</b> (от 2 до 30 букв).\n")
validators.add('surname',
			   r"^[А-Яа-яA-Za-z\-]{2,30}$",
			   "<b>Некорректная фамилия.</b>\n"
			   "Она должно содержать <b>только буквы</b> (от 2 до 30).\n")
validators.add('group',
			   r"^[А-Яа-я]{1,10}-\d{1,3}[А-Яа-я]?$",
			   "<b>Некорректный формат группы</b>\n"
			   "Ожидается что-то вроде <i>'ПИбд-12'</i> или <i>'МОАИСбд-11'</i>\n")

