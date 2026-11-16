"""Seed Uzbekistan universities for autocomplete catalog."""

from django.core.management.base import BaseCommand

from main.models import Institution

# (name_ru, name_en, name_uz, city, region)
UZ_UNIVERSITIES = [
    # ── Ташкент: ключевые ──
    (
        "УМЭД — Университет мировой экономики и дипломатии",
        "UWED — University of World Economy and Diplomacy",
        "JIDU — Jahon iqtisodiyoti va diplomatiya universiteti",
        "Ташкент", "город Ташкент",
    ),
    (
        "ТГЭУ — Ташкентский государственный экономический университет",
        "TSUE — Tashkent State University of Economics",
        "TDIU — Toshkent davlat iqtisodiyot universiteti",
        "Ташкент", "город Ташкент",
    ),
    (
        "ТМА — Ташкентская медицинская академия",
        "TMA — Tashkent Medical Academy",
        "TTA — Toshkent tibbiyot akademiyasi",
        "Ташкент", "город Ташкент",
    ),
    (
        "1-ТГМИ — Первый Ташкентский государственный медицинский институт",
        "1st TSMI — First Tashkent State Medical Institute",
        "1-TDTI — Birinchi Toshkent davlat tibbiyot instituti",
        "Ташкент", "город Ташкент",
    ),
    (
        "2-ТГМИ — Второй Ташкентский государственный медицинский институт",
        "2nd TSMI — Second Tashkent State Medical Institute",
        "2-TDTI — Ikkinchi Toshkent davlat tibbiyot instituti",
        "Ташкент", "город Ташкент",
    ),
    (
        "ТГСтИ — Ташкентский государственный стоматологический институт",
        "TSDI — Tashkent State Dental Institute",
        "TDSMI — Toshkent davlat stomatologiya instituti",
        "Ташкент", "город Ташкент",
    ),
    (
        "ТГПМИ — Ташкентский государственный педиатрический медицинский институт",
        "TSPMI — Tashkent State Pediatric Medical Institute",
        "TDPTI — Toshkent davlat pediatriya tibbiyot instituti",
        "Ташкент", "город Ташкент",
    ),
    (
        "НУУз — Национальный университет Узбекистана им. Мирзо Улугбека",
        "NUUz — National University of Uzbekistan named after Mirzo Ulugbek",
        "O'zMU — O'zbekiston Milliy universiteti",
        "Ташкент", "город Ташкент",
    ),
    (
        "ТГТУ — Ташкентский государственный технический университет",
        "TSTU — Tashkent State Technical University",
        "TDTU — Toshkent davlat texnika universiteti",
        "Ташкент", "город Ташкент",
    ),
    (
        "ТГПУ — Ташкентский государственный педагогический университет",
        "TSPU — Tashkent State Pedagogical University",
        "TDPU — Toshkent davlat pedagogika universiteti",
        "Ташкент", "город Ташкент",
    ),
    (
        "ТГЮУ — Ташкентский государственный юридический университет",
        "TSLU — Tashkent State Law University",
        "TDYU — Toshkent davlat yuridik universiteti",
        "Ташкент", "город Ташкент",
    ),
    (
        "ТУИТ — Ташкентский университет информационных технологий",
        "TUIT — Tashkent University of Information Technologies",
        "TATU — Toshkent axborot texnologiyalari universiteti",
        "Ташкент", "город Ташкент",
    ),
    (
        "ТАУ — Ташкентский архитектурно-строительный университет",
        "TASU — Tashkent Architecture and Civil Engineering University",
        "TQTU — Toshkent qurilish-me'morchilik universiteti",
        "Ташкент", "город Ташкент",
    ),
    (
        "ТГАУ — Ташкентский государственный аграрный университет",
        "TSAU — Tashkent State Agrarian University",
        "TDAU — Toshkent davlat agrar universiteti",
        "Ташкент", "город Ташкент",
    ),
    (
        "ТГТрУ — Ташкентский государственный транспортный университет",
        "TSTU — Tashkent State Transport University",
        "TDTU — Toshkent davlat transport universiteti",
        "Ташкент", "город Ташкент",
    ),
    (
        "ТГИИ — Ташкентский государственный институт востоковедения",
        "TSOI — Tashkent State Institute of Oriental Studies",
        "TSHI — Toshkent sharqshunoslik instituti",
        "Ташкент", "город Ташкент",
    ),
    (
        "ТИИМСХ — Национальный исследовательский университет «ТИИМСХ»",
        "TIIAME — National Research University (Irrigation and Agrotechnology)",
        "TIIAME — Milliy tadqiqot universiteti",
        "Ташкент", "город Ташкент",
    ),
    (
        "УзГУЯЛ — Узбекский государственный университет языков и литературы",
        "UzSULL — Uzbek State University of Languages and Literature",
        "O'zDTIL — O'zbekiston davlat til va adabiyot universiteti",
        "Ташкент", "город Ташкент",
    ),
    (
        "Ташкентский финансовый институт",
        "Tashkent Institute of Finance",
        "Toshkent moliya instituti",
        "Ташкент", "город Ташкент",
    ),
    (
        "Ташкентский институт механики и машиностроения",
        "Tashkent Institute of Mechanics and Engineering",
        "Toshkent mexanika va mashinasozlik instituti",
        "Ташкент", "город Ташкент",
    ),
    (
        "Ташкентский химико-технологический институт",
        "Tashkent Chemical Technology Institute",
        "Toshkent kimyo-texnologiya instituti",
        "Ташкент", "город Ташкент",
    ),
    (
        "Ташкентский институт инженеров железнодорожного транспорта",
        "Tashkent Railway Engineering Institute",
        "Toshkent temir yo'l muhandislari instituti",
        "Ташкент", "город Ташкент",
    ),
    (
        "Ташкентский институт текстильной и лёгкой промышленности",
        "Tashkent Institute of Textile and Light Industry",
        "Toshkent to'qimachilik va engil sanoat instituti",
        "Ташкент", "город Ташкент",
    ),
    (
        "Ташкентский государственный институт культуры",
        "Tashkent State Institute of Culture",
        "Toshkent davlat madaniyat instituti",
        "Ташкент", "город Ташкент",
    ),
    (
        "Национальный институт художеств и дизайна им. К. Бехзода",
        "National Institute of Fine Arts and Design named after K. Bekhzod",
        "K. Behzod nomidagi Milliy badiiy san'at va dizayn instituti",
        "Ташкент", "город Ташкент",
    ),
    (
        "УзГИФК — Узбекский государственный институт физической культуры",
        "UzSIPC — Uzbek State Institute of Physical Culture",
        "O'zDJTI — O'zbekiston davlat jismoniy tarbiya instituti",
        "Ташкент", "город Ташкент",
    ),
    (
        "Университет журналистики и массовых коммуникаций Узбекистана",
        "University of Journalism and Mass Communications of Uzbekistan",
        "O'zbekiston jurnalistika va ommaviy kommunikatsiyalar universiteti",
        "Ташкент", "город Ташкент",
    ),
    (
        "Академия МВД Республики Узбекистан",
        "Academy of the Ministry of Internal Affairs of Uzbekistan",
        "O'zbekiston Respublikasi IIV Akademiyasi",
        "Ташкент", "город Ташкент",
    ),
    # ── Международные (Ташкент) ──
    (
        "WIUT — Вестминстерский международный университет в Ташкенте",
        "WIUT — Westminster International University in Tashkent",
        "WIUT — Toshkentdagi Westminster xalqaro universiteti",
        "Ташкент", "город Ташкент",
    ),
    (
        "TTPU — Туринский политехнический университет в Ташкенте",
        "TTPU — Turin Polytechnic University in Tashkent",
        "TTPU — Toshkentdagi Turin politexnika universiteti",
        "Ташкент", "город Ташкент",
    ),
    (
        "INHA — INHA University in Tashkent",
        "INHA — INHA University in Tashkent",
        "INHA — Toshkentdagi INHA universiteti",
        "Ташкент", "город Ташкент",
    ),
    (
        "MDIS — Management Development Institute of Singapore in Tashkent",
        "MDIS — Management Development Institute of Singapore in Tashkent",
        "MDIS — Toshkentdagi Singapur menejment taraqqiyot instituti",
        "Ташкент", "город Ташкент",
    ),
    (
        "NUU — New Uzbekistan University",
        "NUU — New Uzbekistan University",
        "YaO'U — Yangi O'zbekiston universiteti",
        "Ташкент", "город Ташкент",
    ),
    (
        "IUT — Международный университет в Ташкенте",
        "IUT — International University of Tashkent",
        "TXU — Toshkent xalqaro universiteti",
        "Ташкент", "город Ташкент",
    ),
    (
        "Kimyo International University in Tashkent",
        "Kimyo International University in Tashkent",
        "Toshkentdagi Kimyo xalqaro universiteti",
        "Ташкент", "город Ташкент",
    ),
    (
        "Central Asian University",
        "Central Asian University",
        "Markaziy Osiyo universiteti",
        "Ташкент", "город Ташкент",
    ),
    (
        "Amity University in Tashkent",
        "Amity University in Tashkent",
        "Toshkentdagi Amity universiteti",
        "Ташкент", "город Ташкент",
    ),
    (
        "Webster University in Tashkent",
        "Webster University in Tashkent",
        "Toshkentdagi Webster universiteti",
        "Ташкент", "город Ташкент",
    ),
    (
        "Team University",
        "Team University",
        "Team universiteti",
        "Ташкент", "город Ташкент",
    ),
    (
        "Cambridge International University",
        "Cambridge International University",
        "Kembrij xalqaro universiteti",
        "Ташкент", "город Ташкент",
    ),
    (
        "Digital University Tashkent",
        "Digital University Tashkent",
        "Toshkent raqamli universiteti",
        "Ташкент", "город Ташкент",
    ),
    (
        "PDP University",
        "PDP University",
        "PDP universiteti",
        "Ташкент", "город Ташкент",
    ),
    # ── Медицинские (регионы) ──
    (
        "СамГМУ — Самаркандский государственный медицинский университет",
        "SamSMU — Samarkand State Medical University",
        "SamDTU — Samarqand davlat tibbiyot universiteti",
        "Самарканд", "Самаркандская область",
    ),
    (
        "АГМИ — Андижанский государственный медицинский институт",
        "AnSMI — Andijan State Medical Institute",
        "ADTI — Andijon davlat tibbiyot instituti",
        "Андижан", "Андижанская область",
    ),
    (
        "БГМИ — Бухарский государственный медицинский институт",
        "BuSMI — Bukhara State Medical Institute",
        "BDTI — Buxoro davlat tibbiyot instituti",
        "Бухара", "Бухарская область",
    ),
    (
        "ФГМИ — Ферганский медицинский институт",
        "FerMI — Fergana Medical Institute",
        "FDTI — Farg'ona davlat tibbiyot instituti",
        "Фергана", "Ферганская область",
    ),
    (
        "НамГМИ — Наманганский государственный медицинский институт",
        "NamSMI — Namangan State Medical Institute",
        "NDTI — Namangan davlat tibbiyot instituti",
        "Наманган", "Наманганская область",
    ),
    (
        "КГМИ — Кашкадарьинский медицинский институт",
        "KashMI — Kashkadarya Medical Institute",
        "QMTI — Qashqadaryo tibbiyot instituti",
        "Карши", "Кашкадарьинская область",
    ),
    (
        "СурГМИ — Сурхандарьинский медицинский институт",
        "SurMI — Surkhandarya Medical Institute",
        "SMTI — Surxondaryo tibbiyot instituti",
        "Термез", "Сурхандарьинская область",
    ),
    (
        "Хорезмский медицинский институт",
        "Khorezm Medical Institute",
        "Xorazm tibbiyot instituti",
        "Ургенч", "Хорезмская область",
    ),
    (
        "Навоийский медицинский институт",
        "Navoi Medical Institute",
        "Navoiy tibbiyot instituti",
        "Навои", "Навоийская область",
    ),
    (
        "Каракалпакский медицинский институт",
        "Karakalpak Medical Institute",
        "Qoraqalpog'iston tibbiyot instituti",
        "Нукус", "Республика Каракалпакстан",
    ),
    (
        "Джизакский медицинский институт",
        "Jizzakh Medical Institute",
        "Jizzax tibbiyot instituti",
        "Джизак", "Джизакская область",
    ),
    (
        "Сырдарьинский медицинский институт",
        "Syrdarya Medical Institute",
        "Sirdaryo tibbiyot instituti",
        "Гулистан", "Сырдарьинская область",
    ),
    # ── Государственные (регионы) ──
    (
        "СамГУ — Самаркандский государственный университет",
        "SamSU — Samarkand State University",
        "SamDU — Samarqand davlat universiteti",
        "Самарканд", "Самаркандская область",
    ),
    (
        "Самаркандский государственный институт иностранных языков",
        "Samarkand State Institute of Foreign Languages",
        "Samarqand davlat xorijiy tillar instituti",
        "Самарканд", "Самаркандская область",
    ),
    (
        "Самаркандский государственный архитектурно-строительный институт",
        "Samarkand State Institute of Architecture and Civil Engineering",
        "Samarqand davlat me'morchilik-qurilish instituti",
        "Самарканд", "Самаркандская область",
    ),
    (
        "Самаркандский институт экономики и сервиса",
        "Samarkand Institute of Economics and Service",
        "Samarqand iqtisodiyot va servis instituti",
        "Самарканд", "Самаркандская область",
    ),
    (
        "БГУ — Бухарский государственный университет",
        "BuSU — Bukhara State University",
        "BDU — Buxoro davlat universiteti",
        "Бухара", "Бухарская область",
    ),
    (
        "Бухарский инженерно-технологический институт",
        "Bukhara Engineering Technology Institute",
        "Buxoro muhandislik-texnologiya instituti",
        "Бухара", "Бухарская область",
    ),
    (
        "ФГУ — Ферганский государственный университет",
        "FerSU — Fergana State University",
        "FDU — Farg'ona davlat universiteti",
        "Фергана", "Ферганская область",
    ),
    (
        "Ферганский политехнический институт",
        "Fergana Polytechnic Institute",
        "Farg'ona politexnika instituti",
        "Фергана", "Ферганская область",
    ),
    (
        "Кокандский государственный педагогический институт",
        "Kokand State Pedagogical Institute",
        "Qo'qon davlat pedagogika instituti",
        "Коканд", "Ферганская область",
    ),
    (
        "Маргиланский государственный университет",
        "Margilan State University",
        "Marg'ilon davlat universiteti",
        "Маргилан", "Ферганская область",
    ),
    (
        "АГУ — Андижанский государственный университет",
        "AnSU — Andijan State University",
        "ADU — Andijon davlat universiteti",
        "Андижан", "Андижанская область",
    ),
    (
        "Андижанский машиностроительный институт",
        "Andijan Machine-Building Institute",
        "Andijon mashinasozlik instituti",
        "Андижан", "Андижанская область",
    ),
    (
        "НамГУ — Наманганский государственный университет",
        "NamSU — Namangan State University",
        "NDU — Namangan davlat universiteti",
        "Наманган", "Наманганская область",
    ),
    (
        "Наманганский инженерно-строительный институт",
        "Namangan Engineering-Construction Institute",
        "Namangan muhandislik-qurilish instituti",
        "Наманган", "Наманганская область",
    ),
    (
        "Наманганский инженерно-технологический институт",
        "Namangan Engineering Technology Institute",
        "Namangan muhandislik-texnologiya instituti",
        "Наманган", "Наманганская область",
    ),
    (
        "КГУ — Каршинский государственный университет",
        "KarSU — Karshi State University",
        "QDU — Qarshi davlat universiteti",
        "Карши", "Кашкадарьинская область",
    ),
    (
        "Каршинский инженерно-экономический институт",
        "Karshi Engineering-Economics Institute",
        "Qarshi muhandislik-iqtisodiyot instituti",
        "Карши", "Кашкадарьинская область",
    ),
    (
        "Шахрисабзский педагогический институт",
        "Shakhrisabz Pedagogical Institute",
        "Shahrisabz pedagogika instituti",
        "Шахрисабз", "Кашкадарьинская область",
    ),
    (
        "ТерГУ — Термезский государственный университет",
        "TerSU — Termez State University",
        "TDU — Termiz davlat universiteti",
        "Термез", "Сурхандарьинская область",
    ),
    (
        "УрГУ — Ургенчский государственный университет",
        "UrSU — Urgench State University",
        "UDU — Urganch davlat universiteti",
        "Ургенч", "Хорезмская область",
    ),
    (
        "ДжизГПУ — Джизакский государственный педагогический университет",
        "JizSPU — Jizzakh State Pedagogical University",
        "JDPU — Jizzax davlat pedagogika universiteti",
        "Джизак", "Джизакская область",
    ),
    (
        "ГулГУ — Гулистанский государственный университет",
        "GulSU — Gulistan State University",
        "GDU — Guliston davlat universiteti",
        "Гулистан", "Сырдарьинская область",
    ),
    (
        "НавГУ — Навоийский государственный университет",
        "NavSU — Navoi State University",
        "NDU — Navoiy davlat universiteti",
        "Навои", "Навоийская область",
    ),
    (
        "Навоийский государственный горный институт",
        "Navoi State Mining Institute",
        "Navoiy davlat konchilik instituti",
        "Навои", "Навоийская область",
    ),
    (
        "КарГУ — Каракалпакский государственный университет им. Бердаха",
        "KarSU — Karakalpak State University named after Berdakh",
        "QDU — Qoraqalpog'iston davlat universiteti",
        "Нукус", "Республика Каракалпакстан",
    ),
    (
        "Нукусский государственный педагогический институт",
        "Nukus State Pedagogical Institute",
        "Nukus davlat pedagogika instituti",
        "Нукус", "Республика Каракалпакстан",
    ),
    (
        "ЧирГПУ — Чирчикский государственный педагогический университет",
        "ChirSPU — Chirchiq State Pedagogical University",
        "ChirDPU — Chirchiq davlat pedagogika universiteti",
        "Чирчик", "Ташкентская область",
    ),
]


class Command(BaseCommand):
    help = "Seed Uzbekistan university catalog (verified)"

    def handle(self, *args, **options):
        created = 0
        updated = 0
        for name_ru, name_en, name_uz, city, region in UZ_UNIVERSITIES:
            obj, was_created = Institution.objects.get_or_create(
                type=Institution.TYPE_UNIVERSITY,
                name=name_ru,
                city=city,
                defaults={
                    "name_en": name_en,
                    "name_uz": name_uz,
                    "region": region,
                    "country": "UZ",
                    "is_verified": True,
                },
            )
            if was_created:
                created += 1
            else:
                changed = False
                for field, val in [
                    ("name_en", name_en),
                    ("name_uz", name_uz),
                    ("region", region),
                ]:
                    if getattr(obj, field) != val:
                        setattr(obj, field, val)
                        changed = True
                if obj.country != "UZ":
                    obj.country = "UZ"
                    changed = True
                if not obj.is_verified:
                    obj.is_verified = True
                    changed = True
                if changed:
                    obj.save(update_fields=["name_en", "name_uz", "region", "country", "is_verified"])
                    updated += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"UZ universities: created={created}, updated={updated}, total={len(UZ_UNIVERSITIES)}"
            )
        )
