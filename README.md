# Pin Pipeline — Pinterest affiliate автоматизація (легітимна версія)

Пайплайн: тренд → фільтр Temu-фіду → Claude пише промпти й тексти → генерація зображень → публікація через офіційний Pinterest API v5.

Без API-ключів усе працює в **mock-режимі**: тестовий фід, placeholder-зображення, dry-run замість постингу. Коли отримаєш ключі — вписуєш у `.env`, код не змінюється.

## Установка

```
cd pin_pipeline
pip install -r requirements.txt
copy .env.example .env
```

## Тест без жодного ключа (CLI)

```
python pipeline.py --feed sample_feed.csv --trend "desk organization" --limit 2
```

Створить mock-зображення в `output/images/`, згенерує тексти пінів, покаже dry-run "публікацію" і залогує все в `pipeline.db`.

## Веб-панель (замість CLI)

Той самий пайплайн, керований через браузер: редагування трендів, завантаження фіду з preview, запуск з живим логом (той самий кольоровий формат, що в консолі), історія пінів, налаштування ключів.

```
python -m uvicorn webapp.main:app --reload --port 8000
```

Відкрий http://localhost:8000 — вкладки Dashboard / Trends / Feed / Run / History / Settings.
Все, включно з mock-режимом, працює так само як через `pipeline.py`, просто зручніше клікати, ніж пам'ятати прапори.

## Що робити, коли прийдуть апруви

1. **Anthropic** — ключ з console.anthropic.com → `ANTHROPIC_API_KEY`. Одразу вмикає реальну генерацію промптів і текстів.
2. **fal.ai** — ключ → `FAL_API_KEY`. Вмикає реальну генерацію зображень (flux/schnell, ~$0.003/зображення).
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
| `image_gen.py` | fal.ai flux/schnell + crop до 1000x1500 |
| `pinterest_client.py` | OAuth, boards, create pin (API v5) |
| `db.py` | SQLite: дедуп продуктів, лог пінів |
| `pipeline.py` | оркестратор, CLI |
| `webapp/main.py` | FastAPI backend веб-панелі (ті самі модулі, без дублювання логіки) |
| `webapp/static/` | фронтенд: index.html + app.js + styles.css |

## Важливо

- В описі кожного піна автоматично додається disclosure про AI-зображення та affiliate-лінк (`DISCLOSURE_TEXT` у config) — не прибирай його, це вимога FTC і захист акаунта.
- Між пінами пауза 5 хв (`SECONDS_BETWEEN_PINS`) — не постити пачками.
- Дедуп у SQLite не дасть запостити той самий продукт двічі.
