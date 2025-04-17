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
    *   Могут использоваться для фильтрации (например, `?tags=slug1&author=1`), пагинации (`?page=2&limit=6`), поиска и т.д., в зависимости от настроек ViewSet'а.
*   **Тело запроса:** Не используется для GET-запросов.
*   **Пример ответа (успех, `200 OK`):**

    ```json
    {
      "count": 150,
      "next": "http://example.com/api/recipes/?page=2",
      "previous": null,
      "results": [
        {
          "id": 1,
          "tags": [
            {
              "id": 1,
              "name": "Завтрак",
              "color": "#FF0000",
              "slug": "breakfast"
            }
          ],
          "author": {
            "email": "author1@example.com",
            "id": 1,
            "username": "author1",
            "first_name": "Иван",
            "last_name": "Иванов",
            "is_subscribed": false
          },
          "ingredients": [
            {
              "id": 5,
              "name": "Яйцо",
              "measurement_unit": "шт",
              "amount": 2
            },
            {
              "id": 12,
              "name": "Молоко",
              "measurement_unit": "мл",
              "amount": 100
            }
          ],
          "is_favorited": true,
          "is_in_shopping_cart": false,
          "name": "Омлет классический",
          "image": "http://example.com/media/recipes/images/omelet.jpg",
          "text": "Подробное описание приготовления омлета...",
          "cooking_time": 15
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

5.  **Скачивание списка покупок:**
    *   **Метод:** `GET`
    *   **Endpoint:** `/api/recipes/download_shopping_cart/`
    *   **Аутентификация:** Требуется (Token)
    *   **Ответ:** Файл `shopping_list.txt` для скачивания.

## Автор

*   **<Субботкина Анастасия>**
*   GitHub: [https://github.com/NastSubbotkina](https://github.com/NastSubbotkina)
  
              
## доменное имя: http://nastfoodgram1.zapto.org

## Админка:
Адрес электронной почты:subbotkinanasta00@gmail.com
пароль: q251166q
