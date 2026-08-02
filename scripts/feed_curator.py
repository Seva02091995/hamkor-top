"""
feed_curator.py — AI-powered feed curator for Hamkor Top
Run daily to refresh docs/feed.json with curated career/IT content.
Uses a simple rotation of pre-written cards; can be extended with real AI API calls.
"""
import json
import random
import os

FEED_PATH = os.path.join(os.path.dirname(__file__), '..', 'docs', 'feed.json')

CURATED_CARDS = [
    {"badge":"📈 Тренд","t":{"ru":"IT-экспорт Узбекистана: курс на $1 млрд","uz":"O'zbekiston IT-eksporti: $1 mlrd ga yo'l","en":"Uzbekistan IT exports: heading to $1B"},"b":{"ru":"К 2025 году страна планирует экспорт IT-услуг на $1 млрд. Резидентов IT Park — более 3200. Спрос на разработчиков растёт на 42% в год.","uz":"2025 yilga borib mamlakat IT-xizmatlar eksportini $1 mlrd ga yetkazishni rejalashtirmoqda. IT Park rezidentlari 3200 dan ortiq. Dasturchilarga talab yiliga 42% o'smoqda.","en":"By 2025, the country plans $1B in IT service exports. IT Park residents: 3200+. Developer demand grows 42% annually."}},
    {"badge":"💰 Зарплаты","t":{"ru":"Зарплаты IT в Узбекистане: реальные цифры","uz":"O'zbekistonda IT maoshlari: haqiqiy raqamlar","en":"IT salaries in Uzbekistan: real numbers"},"b":{"ru":"ML-инженер: 15–40 млн сум. Data Scientist: 12–30 млн. DevOps: 14–30 млн. Рост реальных зарплат в 2026 — +9.5%.","uz":"ML-muhandis: 15–40 mln so'm. Data Scientist: 12–30 mln. DevOps: 14–30 mln. 2026-yilda real ish haqi +9.5% o'sdi.","en":"ML Engineer: 15–40M UZS. Data Scientist: 12–30M. DevOps: 14–30M. Real wage growth in 2026: +9.5%."}},
    {"badge":"🌐 Удалёнка","t":{"ru":"Digital Nomad: визы в Центральной Азии","uz":"Digital Nomad: Markaziy Osiyoda vizalar","en":"Digital Nomad: visas in Central Asia"},"b":{"ru":"Кыргызстан — до 10 лет для digital nomads. Казахстан — Neo Nomad Visa. Узбекистан вводит IT-визу. Идеально для удалёнщиков.","uz":"Qirg'iziston — digital nomadlar uchun 10 yilgacha. Qozog'iston — Neo Nomad Visa. O'zbekiston IT-viza joriy qilmoqda.","en":"Kyrgyzstan — up to 10 years for digital nomads. Kazakhstan — Neo Nomad Visa. Uzbekistan introduces IT visa."}},
    {"badge":"🚀 Стартапы","t":{"ru":"Как запустить стартап в Узбекистане","uz":"O'zbekistonda startapni qanday boshlash kerak","en":"How to launch a startup in Uzbekistan"},"b":{"ru":"IT Park: инкубация, менторы, юрподдержка. 13 венчурных фондов, $145M капитала. Astana Hub, nFactorial — гранты и акселерация.","uz":"IT Park: inkubatsiya, mentorlar, yuridik yordam. 13 venchur fond, $145M kapital. Astana Hub, nFactorial — grant va akseleratsiya.","en":"IT Park: incubation, mentors, legal support. 13 VC funds, $145M capital. Astana Hub, nFactorial — grants and acceleration."}},
    {"badge":"🎯 Навыки","t":{"ru":"Топ-3 навыка для IT-карьеры в 2026","uz":"2026-yilda IT-karyera uchun top-3 malaka","en":"Top 3 skills for IT career in 2026"},"b":{"ru":"1. AI/ML (Prompt Engineering). 2. Облачные технологии (AWS/Azure). 3. Кибербезопасность. Работодатели смотрят на практику, а не на диплом.","uz":"1. AI/ML (Prompt Engineering). 2. Bulut texnologiyalari (AWS/Azure). 3. Kiberxavfsizlik. Ish beruvchilar diplomga emas, amaliyotga qaraydi.","en":"1. AI/ML (Prompt Engineering). 2. Cloud (AWS/Azure). 3. Cybersecurity. Employers value practice over diplomas."}},
    {"badge":"🤝 Нетворкинг","t":{"ru":"70% вакансий закрываются по знакомству","uz":"70% vakansiyalar tanish orqali yopiladi","en":"70% of jobs are filled through networking"},"b":{"ru":"Ходите на митапы: ITOSH, Tech Summit, ICT Week. 10 новых контактов в день меняют карьеру быстрее, чем 100 откликов на hh.uz.","uz":"Mitinglarga boring: ITOSH, Tech Summit, ICT Week. Kuniga 10 ta yangi kontakt — 100 ta hh.uz otklikidan tezroq karyerani o'zgartiradi.","en":"Attend meetups: ITOSH, Tech Summit, ICT Week. 10 new contacts a day change your career faster than 100 hh.uz applications."}},
    {"badge":"📱 Фриланс","t":{"ru":"Где брать заказы фрилансеру из Узбекистана","uz":"O'zbekistonlik frilanser uchun buyurtmalar qayerdan olinadi","en":"Where to find freelance gigs from Uzbekistan"},"b":{"ru":"Локально: Myfreelance.uz, Mohirlar.uz. Глобально: Upwork, Kwork. Совет: начните с 3 маленьких проектов для портфолио, затем поднимайте ставку.","uz":"Mahalliy: Myfreelance.uz, Mohirlar.uz. Global: Upwork, Kwork. Maslahat: portfolio uchun 3 ta kichik loyihadan boshlang, keyin stavkani oshiring.","en":"Local: Myfreelance.uz, Mohirlar.uz. Global: Upwork, Kwork. Tip: start with 3 small projects for portfolio, then raise your rate."}},
    {"badge":"📊 Аналитика","t":{"ru":"Python, Flutter, AI — что учат в Узбекистане","uz":"Python, Flutter, AI — O'zbekistonda nima o'rganiladi","en":"Python, Flutter, AI — what Uzbekistan is learning"},"b":{"ru":"Самые популярные курсы: Python (38%), Flutter (22%), AI/ML (18%). IT Park запустил «Один миллион программистов» — бесплатное обучение основам.","uz":"Eng mashhur kurslar: Python (38%), Flutter (22%), AI/ML (18%). IT Park «Bir million dasturchi» loyihasini boshladi — bepul asosiy ta'lim.","en":"Most popular courses: Python (38%), Flutter (22%), AI/ML (18%). IT Park launched 'One Million Programmers' — free basic training."}},
    {"badge":"🏆 Конкурс","t":{"ru":"IT Job Fair 2026: найдите работу мечты","uz":"IT Job Fair 2026: orzuingizdagi ishni toping","en":"IT Job Fair 2026: find your dream job"},"b":{"ru":"Ведущие компании Узбекистана проведут ярмарку вакансий. Готовьте резюме и портфолио. Лучшие кандидаты получают оффер на месте.","uz":"O'zbekistonning yetakchi kompaniyalari vakansiya yarmarkasini o'tkazadi. Rezyume va portfolio tayyorlang. Eng yaxshi nomzodlar joyida offer oladi.","en":"Leading Uzbek companies will hold a job fair. Prepare your CV and portfolio. Top candidates get offers on the spot."}},
]

def refresh_feed():
    """Refresh feed.json with a shuffled selection of cards."""
    cards = CURATED_CARDS.copy()
    random.shuffle(cards)
    selected = cards[:7]  # 7 cards per day
    
    with open(FEED_PATH, 'w', encoding='utf-8') as f:
        json.dump(selected, f, ensure_ascii=False, indent=2)
    
    print(f"Feed refreshed: {len(selected)} cards written to {FEED_PATH}")

if __name__ == '__main__':
    refresh_feed()
