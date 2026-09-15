"""uz ↔ ru medical synonym groups for query expansion (spec §7).

Each group lists spellings of one concept in Uzbek Latin, Uzbek Cyrillic-ish and Russian.
Matching is case-insensitive and apostrophe-insensitive (see `services.normalise`).
Editors can extend the list here; a CMS-managed list is a hardening item (TODO_HARDENING).
"""

from __future__ import annotations

SYNONYM_GROUPS: list[list[str]] = [
    ["saraton", "rak", "рак", "onkologiya", "онкология", "oʻsma", "опухоль"],
    ["koʻkrak", "koʻkrak bezi", "грудь", "молочная железа", "молочной железы", "рмж", "kbs"],
    ["bachadon boʻyni", "шейка матки", "шейки матки", "ршм", "bbs"],
    ["skrining", "скрининг", "tekshiruv", "обследование", "profilaktik koʻrik"],
    ["mammografiya", "маммография"],
    ["utt", "ultratovush", "узи", "ультразвук"],
    ["hpv", "впч", "papilloma", "папиллома"],
    ["belgi", "belgilar", "simptom", "симптом", "симптомы", "признак", "признаки"],
    ["xavf", "риск", "xavf omillari", "факторы риска"],
    ["davolash", "лечение", "terapiya", "терапия"],
    ["kimyoterapiya", "химиотерапия", "ximioterapiya"],
    ["nur terapiyasi", "лучевая терапия", "radioterapiya", "радиотерапия"],
    ["shifokor", "врач", "doktor", "доктор", "onkolog", "онколог"],
    ["bola", "bolalar", "ребёнок", "ребенок", "дети", "детский"],
    ["ayol", "ayollar", "женщина", "женщины", "женский"],
    ["leykoz", "лейкоз", "leykemiya", "лейкемия"],
    ["limfoma", "лимфома"],
    ["neyroblastoma", "нейробластома"],
    ["sarkoma", "саркома"],
    ["biopsiya", "биопсия"],
    ["diagnostika", "диагностика", "tashxis", "диагноз"],
    ["reabilitatsiya", "реабилитация", "tiklanish", "восстановление"],
    ["psixolog", "психолог", "psixologik yordam", "психологическая помощь"],
    ["poliklinika", "поликлиника", "shifoxona", "больница", "klinika", "клиника"],
    ["bepul", "бесплатно", "бесплатный"],
    ["qayerga murojaat", "куда обратиться", "manzil", "адрес"],
    ["oila", "семья", "ota-ona", "родители"],
    ["oʻz-oʻzini tekshirish", "самообследование"],
    ["genetik", "генетический", "irsiy", "наследственный"],
    ["remissiya", "ремиссия"],
]
