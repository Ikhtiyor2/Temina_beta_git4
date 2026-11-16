"""Uzbekistan geo reference: regions (viloyatlar) and cities for autocomplete."""

from __future__ import annotations

# 14 administrative units (12 viloyats + Karakalpakstan + Tashkent city)
# name = Russian (canonical, stored on Player), nameEn / nameUz = display
UZ_REGIONS: list[dict[str, str]] = [
    {
        "id": "tashkent-city",
        "name": "город Ташкент",
        "nameEn": "Tashkent city",
        "nameUz": "Toshkent shahri",
    },
    {
        "id": "tashkent",
        "name": "Ташкентская область",
        "nameEn": "Tashkent region",
        "nameUz": "Toshkent viloyati",
    },
    {
        "id": "andijan",
        "name": "Андижанская область",
        "nameEn": "Andijan region",
        "nameUz": "Andijon viloyati",
    },
    {
        "id": "bukhara",
        "name": "Бухарская область",
        "nameEn": "Bukhara region",
        "nameUz": "Buxoro viloyati",
    },
    {
        "id": "fergana",
        "name": "Ферганская область",
        "nameEn": "Fergana region",
        "nameUz": "Fargʻona viloyati",
    },
    {
        "id": "jizzakh",
        "name": "Джизакская область",
        "nameEn": "Jizzakh region",
        "nameUz": "Jizzax viloyati",
    },
    {
        "id": "kashkadarya",
        "name": "Кашкадарьинская область",
        "nameEn": "Kashkadarya region",
        "nameUz": "Qashqadaryo viloyati",
    },
    {
        "id": "khorezm",
        "name": "Хорезмская область",
        "nameEn": "Khorezm region",
        "nameUz": "Xorazm viloyati",
    },
    {
        "id": "namangan",
        "name": "Наманганская область",
        "nameEn": "Namangan region",
        "nameUz": "Namangan viloyati",
    },
    {
        "id": "navoiy",
        "name": "Навоийская область",
        "nameEn": "Navoiy region",
        "nameUz": "Navoiy viloyati",
    },
    {
        "id": "karakalpakstan",
        "name": "Республика Каракалпакстан",
        "nameEn": "Republic of Karakalpakstan",
        "nameUz": "Qoraqalpogʻiston Respublikasi",
    },
    {
        "id": "samarkand",
        "name": "Самаркандская область",
        "nameEn": "Samarkand region",
        "nameUz": "Samarqand viloyati",
    },
    {
        "id": "sirdarya",
        "name": "Сырдарьинская область",
        "nameEn": "Syrdarya region",
        "nameUz": "Sirdaryo viloyati",
    },
    {
        "id": "surkhandarya",
        "name": "Сурхандарьинская область",
        "nameEn": "Surkhandarya region",
        "nameUz": "Surxondaryo viloyati",
    },
]

# Major / oblast-level cities keyed by region id
# name = Russian (canonical), nameEn / nameUz = display
UZ_CITIES: list[dict[str, str]] = [
    # город Ташкент
    {"name": "Ташкент", "nameEn": "Tashkent", "nameUz": "Toshkent", "regionId": "tashkent-city"},
    # Ташкентская область
    {"name": "Чирчик", "nameEn": "Chirchiq", "nameUz": "Chirchiq", "regionId": "tashkent"},
    {"name": "Ангрен", "nameEn": "Angren", "nameUz": "Angren", "regionId": "tashkent"},
    {"name": "Алмалык", "nameEn": "Almalyk", "nameUz": "Olmaliq", "regionId": "tashkent"},
    {"name": "Бекабад", "nameEn": "Bekabad", "nameUz": "Bekobod", "regionId": "tashkent"},
    {"name": "Янгиюль", "nameEn": "Yangiyul", "nameUz": "Yangiyoʻl", "regionId": "tashkent"},
    {"name": "Нурафшон", "nameEn": "Nurafshon", "nameUz": "Nurafshon", "regionId": "tashkent"},
    {"name": "Ахангаран", "nameEn": "Akhangaran", "nameUz": "Ohangaron", "regionId": "tashkent"},
    # Андижанская
    {"name": "Андижан", "nameEn": "Andijan", "nameUz": "Andijon", "regionId": "andijan"},
    {"name": "Асака", "nameEn": "Asaka", "nameUz": "Asaka", "regionId": "andijan"},
    {"name": "Ханабад", "nameEn": "Khanabad", "nameUz": "Xonobod", "regionId": "andijan"},
    {"name": "Шахрихан", "nameEn": "Shahrikhan", "nameUz": "Shahrixon", "regionId": "andijan"},
    # Бухарская
    {"name": "Бухара", "nameEn": "Bukhara", "nameUz": "Buxoro", "regionId": "bukhara"},
    {"name": "Каган", "nameEn": "Kagan", "nameUz": "Kogon", "regionId": "bukhara"},
    {"name": "Гиждуван", "nameEn": "Gijduvan", "nameUz": "Gʻijduvon", "regionId": "bukhara"},
    {"name": "Каракуль", "nameEn": "Karakul", "nameUz": "Qorakoʻl", "regionId": "bukhara"},
    # Ферганская
    {"name": "Фергана", "nameEn": "Fergana", "nameUz": "Fargʻona", "regionId": "fergana"},
    {"name": "Коканд", "nameEn": "Kokand", "nameUz": "Qoʻqon", "regionId": "fergana"},
    {"name": "Маргилан", "nameEn": "Margilan", "nameUz": "Margʻilon", "regionId": "fergana"},
    {"name": "Кувасай", "nameEn": "Kuvasay", "nameUz": "Quvasoy", "regionId": "fergana"},
    {"name": "Кува", "nameEn": "Kuva", "nameUz": "Quva", "regionId": "fergana"},
    # Джизакская
    {"name": "Джизак", "nameEn": "Jizzakh", "nameUz": "Jizzax", "regionId": "jizzakh"},
    {"name": "Гагарин", "nameEn": "Gagarin", "nameUz": "Gagarin", "regionId": "jizzakh"},
    {"name": "Пахтакор", "nameEn": "Pakhtakor", "nameUz": "Paxtakor", "regionId": "jizzakh"},
    # Кашкадарьинская
    {"name": "Карши", "nameEn": "Karshi", "nameUz": "Qarshi", "regionId": "kashkadarya"},
    {"name": "Шахрисабз", "nameEn": "Shakhrisabz", "nameUz": "Shahrisabz", "regionId": "kashkadarya"},
    {"name": "Китоб", "nameEn": "Kitab", "nameUz": "Kitob", "regionId": "kashkadarya"},
    {"name": "Мубарек", "nameEn": "Mubarek", "nameUz": "Muborak", "regionId": "kashkadarya"},
    # Хорезмская
    {"name": "Ургенч", "nameEn": "Urgench", "nameUz": "Urganch", "regionId": "khorezm"},
    {"name": "Хива", "nameEn": "Khiva", "nameUz": "Xiva", "regionId": "khorezm"},
    {"name": "Питнак", "nameEn": "Pitnak", "nameUz": "Pitnak", "regionId": "khorezm"},
    # Наманганская
    {"name": "Наманган", "nameEn": "Namangan", "nameUz": "Namangan", "regionId": "namangan"},
    {"name": "Чуст", "nameEn": "Chust", "nameUz": "Chust", "regionId": "namangan"},
    {"name": "Касансай", "nameEn": "Kasansay", "nameUz": "Kosonsoy", "regionId": "namangan"},
    {"name": "Пап", "nameEn": "Pap", "nameUz": "Pop", "regionId": "namangan"},
    # Навоийская
    {"name": "Навои", "nameEn": "Navoiy", "nameUz": "Navoiy", "regionId": "navoiy"},
    {"name": "Зарафшан", "nameEn": "Zarafshan", "nameUz": "Zarafshon", "regionId": "navoiy"},
    {"name": "Учкудук", "nameEn": "Uchquduq", "nameUz": "Uchquduq", "regionId": "navoiy"},
    {"name": "Кызылтепа", "nameEn": "Kyzyltepa", "nameUz": "Qiziltepa", "regionId": "navoiy"},
    # Каракалпакстан
    {"name": "Нукус", "nameEn": "Nukus", "nameUz": "Nukus", "regionId": "karakalpakstan"},
    {"name": "Кунград", "nameEn": "Kungrad", "nameUz": "Qoʻngʻirot", "regionId": "karakalpakstan"},
    {"name": "Тахиаташ", "nameEn": "Takhiatash", "nameUz": "Taxiatosh", "regionId": "karakalpakstan"},
    {"name": "Ходжейли", "nameEn": "Khodjeyli", "nameUz": "Xoʻjayli", "regionId": "karakalpakstan"},
    {"name": "Муйнак", "nameEn": "Muynak", "nameUz": "Moʻynoq", "regionId": "karakalpakstan"},
    # Самаркандская
    {"name": "Самарканд", "nameEn": "Samarkand", "nameUz": "Samarqand", "regionId": "samarkand"},
    {"name": "Каттакурган", "nameEn": "Kattakurgan", "nameUz": "Kattaqoʻrgʻon", "regionId": "samarkand"},
    {"name": "Ургут", "nameEn": "Urgut", "nameUz": "Urgut", "regionId": "samarkand"},
    {"name": "Акташ", "nameEn": "Aktash", "nameUz": "Oqtosh", "regionId": "samarkand"},
    # Сырдарьинская
    {"name": "Гулистан", "nameEn": "Gulistan", "nameUz": "Guliston", "regionId": "sirdarya"},
    {"name": "Янгиер", "nameEn": "Yangiyer", "nameUz": "Yangiyer", "regionId": "sirdarya"},
    {"name": "Ширин", "nameEn": "Shirin", "nameUz": "Shirin", "regionId": "sirdarya"},
    # Сурхандарьинская
    {"name": "Термез", "nameEn": "Termez", "nameUz": "Termiz", "regionId": "surkhandarya"},
    {"name": "Денау", "nameEn": "Denau", "nameUz": "Denov", "regionId": "surkhandarya"},
    {"name": "Шерабад", "nameEn": "Sherabad", "nameUz": "Sherobod", "regionId": "surkhandarya"},
]


def _pick(lang: str, ru: str, en: str = "", uz: str = "") -> str:
    """Pick display string; accept en / en-US / uz-Latn etc."""
    key = (lang or "ru").strip().lower()
    if key.startswith("en") and en:
        return en
    if key.startswith("uz") and uz:
        return uz
    return ru


def _region_by_id(region_id: str) -> dict[str, str] | None:
    rid = (region_id or "").strip().lower()
    for r in UZ_REGIONS:
        if r["id"] == rid:
            return r
    return None


def localize_region(region: dict[str, str], lang: str) -> dict[str, str]:
    return {
        "id": region["id"],
        "name": _pick(lang, region["name"], region.get("nameEn", ""), region.get("nameUz", "")),
        "nameRu": region["name"],
    }


def localize_city(city: dict[str, str], lang: str) -> dict[str, str]:
    region = _region_by_id(city["regionId"]) or {"name": "", "nameEn": "", "nameUz": ""}
    return {
        "name": _pick(lang, city["name"], city.get("nameEn", ""), city.get("nameUz", "")),
        "nameRu": city["name"],
        "region": _pick(lang, region["name"], region.get("nameEn", ""), region.get("nameUz", "")),
        "regionRu": region.get("name", ""),
        "regionId": city["regionId"],
    }


def list_regions(*, q: str = "", lang: str = "ru") -> list[dict[str, str]]:
    needle = (q or "").strip().lower()
    out: list[dict[str, str]] = []
    for r in UZ_REGIONS:
        item = localize_region(r, lang)
        if not needle:
            out.append(item)
            continue
        hay = " ".join(
            [
                item["name"],
                item["nameRu"],
                r.get("nameEn", ""),
                r.get("nameUz", ""),
                r["id"],
            ]
        ).lower()
        if needle in hay:
            out.append(item)
    return out


def list_cities(*, region: str = "", region_id: str = "", q: str = "", lang: str = "ru") -> list[dict[str, str]]:
    needle = (q or "").strip().lower()
    region_needle = (region or "").strip().lower()
    rid = (region_id or "").strip().lower()
    out: list[dict[str, str]] = []
    for city in UZ_CITIES:
        if rid and city["regionId"] != rid:
            continue
        item = localize_city(city, lang)
        if region_needle:
            region_hay = " ".join([item["region"], item["regionRu"]]).lower()
            if region_needle not in region_hay:
                continue
        if needle:
            city_hay = " ".join(
                [
                    item["name"],
                    item["nameRu"],
                    city.get("nameEn", ""),
                    city.get("nameUz", ""),
                ]
            ).lower()
            if needle not in city_hay:
                continue
        out.append(item)
    return out
