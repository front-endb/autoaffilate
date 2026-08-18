# Pin Pipeline — Pinterest affiliate автоматизація (легітимна версія)

Пайплайн: тренд → фільтр Temu-фіду → Claude пише промпти й тексти → генерація зображень → публікація через офіційний Pinterest API v5.

Без API-ключів усе працює в **mock-режимі**: тестовий фід, placeholder-зображення, dry-run замість постингу. Коли отримаєш ключі — вписуєш у `.env`, код не змінюється.

## Що тут насправді автоматизовано, а що ні

Щоб не було ілюзій "повністю AI-агенти на кожному кроці":

| Етап | Реальність |
|---|---|
| Trend analysis | **Ручний ввід** у `trends.json` раз на тиждень (дивишся Pinterest Trends сам) |
| Product matching (Temu) | **Офіційний affiliate product feed** (CSV/JSON export з дашборду), не скрапінг сайту |
| Visual research / image prompts | **Автоматично** — Claude (або mock-шаблон) пише промпти на основі trend-даних |
| Image generation | **Автоматично** — Pollinations AI (безкоштовно, без ключа) |
| Pin copy (title/description/hashtags) | **Автоматично** — Claude (або mock-шаблон) |
| Publishing | **Автоматично** — офіційний Pinterest API v5, мультиборд-фанаут на всі запропоновані борди |

Тобто три з п'яти "агентів" з оригінальної статті, що надихнула цей проєкт, у нас — свідомо ручний ввід або статичний фід, а не автономний AI/скрапер. Це зроблено навмисно (обхід ToS Pinterest/Temu через скрапінг — юридичний і практичний ризик), а не недогляд.

## Установка

```
cd pin_pipeline
pip install -r requirements.txt
copy .env.example .env
git config core.hooksPath .githooks
```

Останній рядок вмикає pre-commit хук, який блокує коміт, якщо туди випадково потрапить реальний `.env` або текст, схожий на живий API-ключ (Anthropic, Gemini) — додатковий рівень захисту поверх `.gitignore`.

## Тест без жодного ключа (CLI)

```
python pipeline.py --feed sample_feed.csv --trend "desk organization" --limit 2
python pipeline.py --feed sample_feed.csv --trend "desk organization" --trend "bathroom organization"  # кілька трендів за раз
python pipeline.py --feed sample_feed.csv --all-trends   # усі тренди з trends.json за один запуск
```

Створить mock-зображення в `output/images/`, згенерує тексти пінів, покаже dry-run "публікацію" і залогує все в `pipeline.db`. Кожен пін публікується на **всі** запропоновані Claude борди (3-4), не тільки на перший — так само, як у оригінальному пайплайні, під який це писалось.

## Веб-панель (замість CLI)

Той самий пайплайн, керований через браузер: редагування трендів, завантаження фіду з preview, запуск з живим логом (той самий кольоровий формат, що в консолі), історія пінів, налаштування ключів.

```
python -m uvicorn webapp.main:app --reload --port 8000
```

Відкрий http://localhost:8000 — вкладки Dashboard / Trends / Feed / Run / History / Settings.
Все, включно з mock-режимом, працює так само як через `pipeline.py`, просто зручніше клікати, ніж пам'ятати прапори.

## Що робити, коли прийдуть апруви

1. **Anthropic** — ключ з console.anthropic.com → `ANTHROPIC_API_KEY`. Одразу вмикає реальну генерацію промптів і текстів.
2. **Зображення** — нічого чекати не треба: Pollinations AI вже працює без жодного ключа (безкоштовно, без реєстрації, без карти).
3. **Pinterest**:
   - зареєструй апку на developers.pinterest.com (потрібен Business account);
   - Redirect URI в апці має бути **точно** `http://localhost:8000/api/pinterest/callback` (або онови під свій порт і в `.env`, і в налаштуваннях апки);
   - App ID/Secret → `.env` (напряму або через вкладку Settings у веб-панелі);
   - OAuth: або `python pinterest_client.py auth` (термінал), або кнопка "Отримати посилання авторизації" у Settings — токен сам запишеться в `.env` після редіректу.
4. **Temu affiliate** — після апруву скачай product feed (CSV/JSON) з дашборду. Подивись реальні назви колонок і онови `FEED_COLUMN_MAP` у `config.py`.

Реальний постинг:

```
python pipeline.py --feed real_feed.csv --trend "desk organization" --limit 5 --post
```

## Статистика

```
python stats.py
python stats.py --days 14 --months 6
```

Показує піни за день/місяць, топ бордів — усе з локального `pipeline.db`, без зовнішніх API. Impressions і дохід з Pinterest/Temu поки недоступні (потрібен живий доступ до Pinterest Analytics і Temu-дашборду) — заплановано додати, коли обидва апруви прийдуть.

## Щотижнева рутина

1. Подивись [Pinterest Trends](https://www.pinterest.com/business/trends) → онови `trends.json` (категорія, keywords, естетика).
2. Скачай свіжий фід з Temu affiliate dashboard.
3. Запусти пайплайн 1-2 рази на тиждень з `--limit 5-10`.

## Файли

| Файл | Що робить |
|---|---|
| `config.py` | всі налаштування: фільтри, ліміти, шляхи |
| `trends.json` | ручний ввід трендів (раз на тиждень) |
| `temu_feed.py` | завантаження + фільтр фіду (pandas) |
| `claude_client.py` | Claude: image-промпти та pin copy |
| `image_gen.py` | Pollinations AI (безкоштовно, без ключа) + crop до 1000x1500 |
| `pinterest_client.py` | OAuth, boards, create pin (API v5) |
| `db.py` | SQLite: дедуп продуктів, лог пінів, статистика |
| `pipeline.py` | оркестратор, CLI |
| `stats.py` | локальна статистика (піни за день/місяць, топ бордів) з `pipeline.db` |
| `webapp/main.py` | FastAPI backend веб-панелі (ті самі модулі, без дублювання логіки) |
| `webapp/static/` | фронтенд: index.html + app.js + styles.css |

## Важливо

- В описі кожного піна автоматично додається disclosure про AI-зображення та affiliate-лінк (`DISCLOSURE_TEXT` у config) — не прибирай його, це вимога FTC і захист акаунта.
- Між пінами пауза 5 хв (`SECONDS_BETWEEN_PINS`) — не постити пачками.
- Дедуп у SQLite не дасть запостити той самий продукт двічі.
