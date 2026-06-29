CRUD REST API для планувальника подорожей. Користувач створює **проекти** подорожей, додає до них **місця** (картини з [Art Institute of Chicago API](https://api.artic.edu/docs/)), залишає **нотатки** до кожного місця і позначає їх як відвідані. Коли всі місця відвідані — проект автоматично стає `completed`.

> Stack: **Django 5**, **Django REST Framework**, **SQLite**, **requests**.

---

## Можливості

- CRUD для проектів і місць
- Валідація кожного місця через зовнішнє API
- Ліміт 10 місць на проект
- Заборона додавати дублікати в один проект
- Заборона видалення проекту з відвіданими місцями
- Автоматичний статус: `planning` → `completed` коли всі місця відвідані

**Бонуси:** Docker, готова Postman-колекція.

---

## Запуск

### Локально

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

API → <http://localhost:8000/projects/>

### Docker

```bash
docker compose up --build
```

---

## Endpoints

| Метод    | URL                                              | Опис                                    |
| -------- | ------------------------------------------------ | --------------------------------------- |
| `POST`   | `/projects/`                                     | Створити проект (можна з місцями)       |
| `GET`    | `/projects/`                                     | Список проектів                         |
| `GET`    | `/projects/{id}/`                                | Отримати проект з місцями               |
| `PATCH`  | `/projects/{id}/`                                | Оновити name / description / start_date |
| `DELETE` | `/projects/{id}/`                                | Видалити проект                         |
| `POST`   | `/projects/{id}/places/`                         | Додати місце                            |
| `GET`    | `/projects/{id}/places/`                         | Список місць проекту                    |
| `GET`    | `/projects/{id}/places/{place_id}/`              | Отримати одне місце                     |
| `PATCH`  | `/projects/{id}/places/{place_id}/`              | Оновити notes / позначити відвіданим    |

### Приклад: створити проект з місцями

```bash
curl -X POST http://localhost:8000/projects/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Chicago tour",
    "description": "Art trip",
    "places": [
      {"external_id": "28560", "notes": "Seurat"},
      {"external_id": "16568"}
    ]
  }'
```

### Приклад: позначити місце відвіданим

```bash
curl -X PATCH http://localhost:8000/projects/1/places/1/ \
  -H "Content-Type: application/json" \
  -d '{"is_visited": true}'
```

---

## Змінні оточення

| Variable                 | Default                          | Опис                                  |
| ------------------------ | -------------------------------- | ------------------------------------- |
| `SECRET_KEY`             | `django-insecure-...`            | Django secret key                     |
| `DEBUG`                  | `True`                           | Режим розробки                        |
| `DATABASE_PATH`          | `./travel_planner.db`            | Шлях до SQLite                        |
| `ARTIC_API_BASE_URL`     | `https://api.artic.edu/api/v1`   | Базовий URL зовнішнього API           |
| `ARTIC_API_TIMEOUT`      | `10.0`                           | Таймаут запиту до API                 |
| `MAX_PLACES_PER_PROJECT` | `10`                             | Максимум місць у проекті              |

Див. `.env.example` для готового шаблону.

---

## Postman collection

Готова колекція з усіма запитами лежить у [`postman/TravelPlanner.postman_collection.json`](postman/TravelPlanner.postman_collection.json).

**Як використати:**
1. Postman → Import → обрати файл.
2. У змінних колекції `baseUrl` стоїть `http://localhost:8000`.
3. Запусти запити по порядку — `projectId` і `placeId` збережуться у змінні автоматично.

---

## Структура проекту

```
TravelPlanner/
├── manage.py
├── TravelPlanner/           # Налаштування Django
│   ├── settings.py
│   └── urls.py
├── projects/                # Основний застосунок
│   ├── models.py            # Project, Place
│   ├── serializers.py       # Валідація + серіалізація
│   ├── views.py             # HTTP endpoints + клієнт зовнішнього API
│   ├── urls.py              # Маршрути
│   └── migrations/
├── postman/
│   └── TravelPlanner.postman_collection.json
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```