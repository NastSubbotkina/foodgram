# Foodgram - Продуктовый Помощник

## Описание проекта

**Foodgram** ("Продуктовый помощник") — это веб-сервис, где пользователи могут публиковать свои рецепты, подписываться на публикации других авторов, добавлять понравившиеся рецепты в избранное и формировать список покупок на основе выбранных рецептов.

**Основные возможности:**

*   Регистрация и аутентификация пользователей.
*   Создание, редактирование и удаление собственных рецептов.
*   Использование тегов для категоризации рецептов.
*   Подписка на других авторов.
*   Добавление рецептов в список "Избранное".
*   Формирование "Списка покупок" с возможностью скачивания в виде текстового файла.
*   Просмотр рецептов с фильтрацией по автору, тегам, наличию в избранном или списке покупок.

## Технологии

*   **Backend:** Python 3.9+, Django 3.2+, Django REST Framework
*   **База данных:** PostgreSQL
*   **Веб-сервер:** Nginx
*   **Контейнеризация:** Docker, Docker Compose
*   **CI/CD:** GitHub Actions (пример)

## Запуск проекта на сервере с Docker

**Требования:**

*   Установленный Docker (`docker`)
*   Установленный Docker Compose (`docker compose` или `docker-compose`)
*   Система контроля версий Git
*   Сервер с доступом по SSH (ОС Linux)

**Инструкция по развертыванию:**

1.  **Создать и заполнить `.env` файл:**
    В корневой директории проекта создайте файл `.env` и заполните его необходимыми переменными окружения.

2.  **Проверить конфигурацию Nginx:**
    Убедитесь, что файл конфигурации Nginx (например, `nginx/default.conf`), на который ссылается сервис `nginx` в `docker-compose.yml`, существует и настроен правильно (проксирование на сервис `backend`).

3.  **Собрать и запустить контейнеры:**
    Эта команда скачает или соберет образы (если используется `build`) и запустит все сервисы в фоновом режиме.
    ```bash
    sudo docker compose up -d --build
    ```

4.  **Применить миграции:**
    ```bash
    sudo docker compose exec backend python manage.py migrate
    ```

5.  **Создать суперпользователя:**
    ```bash
    sudo docker compose exec backend python manage.py createsuperuser
    ```
    *(Следуйте инструкциям для ввода логина, email и пароля)*

7.  **Собрать статику:**
    ```bash
    sudo docker compose exec backend python manage.py collectstatic --noinput
    ```

5.  **Заполните базу ингредиентами:**
    Выполните кастомную команду управления для импорта данных.
    ```bash
    sudo docker-compose exec backend python manage.py import_ingredients.py
    ```
    *   Эта команда запустит скрипт `import_ingredients.py` внутри контейнера `backend` для наполнения таблицы ингредиентов.
      
6.  **Создать пару тегов через админку**
    
9.  **Готово!**
    Проект должен быть доступен по IP-адресу вашего сервера (или домену).


## Примеры запросов к API

API доступно по адресу `http://nastfoodgram1.zapto.org/api/`. Для некоторых запросов (создание, изменение, подписки и т.д.) требуется аутентификация по токену.

1.  **Получение токена (Login):**
    *   **Метод:** `POST`
    *   **Endpoint:** `/api/auth/token/login/`
    *   **Body (JSON):**
        ```json
        {
          "email": "user@example.com",
          "password": "your_password"
        }
        ```
    *   **Ответ:**
        ```json
        {
          "auth_token": "your_authentication_token"
        }
        ```
### 2. Получение списка рецептов

*   **Метод:** `GET`
*   **Endpoint:** `/api/recipes/`
*   **Аутентификация:** Не требуется
*   **Параметры запроса (Query Parameters):**
    *   Могут использоваться для фильтрации (например, `?tags=slug1&author=1`), пагинации (`?page=2&limit=6`).
*   **Тело запроса:** Не используется для GET-запросов.
*   **Пример ответа (успех, `200 OK`):**

    ```json
    {
      "count": 10,
    "next": "http://nastfoodgram1.zapto.org/api/recipes/?page=2",
    "previous": null,
    "results": [
        {
            "id": 29,
            "tags": [
                {
                    "id": 10,
                    "name": "Здоровое питание",
                    "slug": "Healthy"
                },
                {
                    "id": 5,
                    "name": "итальянская кухня",
                    "slug": "Italian_food"
                },
                {
                    "id": 6,
                    "name": "Обед",
                    "slug": "Lunch"
                }
            ],
            "author": {
                "email": "nast3@yandex.ru",
                "id": 3,
                "username": "Nast3",
                "first_name": "Настя2",
                "last_name": "Субботкина",
                "is_subscribed": false,
                "avatar": null
            },
            "ingredients": [
                {
                    "id": 557,
                    "name": "картофель",
                    "measurement_unit": "г",
                    "amount": 500
                },
                {
                    "id": 521,
                    "name": "капуста белокочанная",
                    "measurement_unit": "г",
                    "amount": 300
                },
                {
                    "id": 887,
                    "name": "лук репчатый",
                    "measurement_unit": "г",
                    "amount": 100
                },
                {
                    "id": 1854,
                    "name": "томатная паста",
                    "measurement_unit": "г",
                    "amount": 50
                },
                {
                    "id": 1420,
                    "name": "растительное масло",
                    "measurement_unit": "мл",
                    "amount": 30
                },
                {
                    "id": 1685,
                    "name": "соль",
                    "measurement_unit": "г",
                    "amount": 10
                },
                {
                    "id": 1054,
                    "name": "морковь",
                    "measurement_unit": "г",
                    "amount": 400
                }
            ],
            "is_favorited": false,
            "is_in_shopping_cart": false,
            "name": "Овощное рагу",
            "image": "http://nastfoodgram1.zapto.org/media/recipes/images/temp.jpeg",
            "text": "1. Подготовка овощей:\n   - Картофель очистить и нарезать кубиками\n   - Морковь натереть на крупной терке\n   - Лук нарезать полукольцами\n   - Капусту нашинковать\n\n2. Обжарка:\n   - Разогреть растительное масло в казане или глубокой сковороде\n   - Обжарить лук до прозрачности (3-4 минуты)\n   - Добавить морковь, готовить ещё 5 минут\n\n3. Основное приготовление:\n   - Добавить картофель, перемешать\n   - Влить 200 мл воды, тушить под крышкой 15 минут\n   - Добавить капусту и томатную пасту\n   - Посолить, поперчить по вкусу\n\n4. Завершение:\n   - Тушить на медленном огне ещё 20 минут до готовности овощей\n   - Дать настояться 10 минут перед подачей\n\nПодавать горячим, посыпав свежей зеленью.",
            "cooking_time": 32
        },
        {
          // ... другие рецепты ...
        }
      ]
    }
    ```
3.  **Создание нового рецепта:*
    *   **Метод:** `POST`
    *   **Endpoint:** `/api/recipes/`
    *   **Аутентификация:** Требуется (Token)
    *   **Body (JSON):** 
        ```json
        {
          "ingredients": [
            { "id": 1, "amount": 100 },
            { "id": 5, "amount": 2 }
          ],
          "tags": [1, 3],
          "image": "data:image/png;base64,iVBORw0KGgo...", // base64 encoded image
          "name": "Название рецепта",
          "text": "Описание приготовления.",
          "cooking_time": 30
        }
        ```
4.  **Подписка на автора:**
    *   **Метод:** `POST`
    *   **Endpoint:** `/api/users/{user_id}/subscribe/` (где `{user_id}` - ID автора)
    *   **Аутентификация:** Требуется (Token)
    *   **Body (JSON):**
       ```json
      {
    "email": "nast.subbotkina@yandex.ru",
    "id": 1,
    "username": "Nastya1604",
    "first_name": "Настя3",
    "last_name": "Субботкина",
    "is_subscribed": true,
    "avatar": null
    }

5.  **Скачивание списка покупок:**
    *   **Метод:** `GET`
    *   **Endpoint:** `/api/recipes/download_shopping_cart/`
    *   **Аутентификация:** Требуется (Token)
    *   **Ответ:** Файл `shopping_list.txt` для скачивания.

## Автор

*   **<Субботкина Анастасия>**
*   GitHub: [https://github.com/NastSubbotkina](https://github.com/NastSubbotkina)
  
              
## доменное имя: http://nastfoodgram1.zapto.org


