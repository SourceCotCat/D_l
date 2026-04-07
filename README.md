# Сервис автоматизации закупок

## Возможности

- Регистрация и авторизация (покупатели и поставщики)
- Каталог товаров от нескольких поставщиков
- Корзина (можно добавлять товары от разных магазинов)
- Оформление заказа с адресом доставки
- Email-уведомления о регистрации и подтверждении заказа
- Загрузка прайс-листов поставщиками
- Управление статусом приёма заказов

## Быстрый запуск

1. Установите зависимости:

pip install -r requirements.txt

python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000

## Основные эндпоинты

POST /api/v1/user/register/ — регистрация
POST /api/v1/user/login/ — вход
POST /api/v1/user/logout/ — выход
GET/PATCH /api/v1/user/details/ — профиль

Каталог

GET /api/v1/shops/ — магазины
GET /api/v1/categories/ — категории
GET /api/v1/products/ — товары
GET /api/v1/products/{id}/ — детальная информация о товаре

Корзина и заказы

GET/POST/PUT/DELETE /api/v1/basket/ — корзина
POST /api/v1/order/confirm/ — подтвердить заказ
GET /api/v1/order/ — список заказов
GET /api/v1/order/{id}/ — детали заказа

Для поставщиков

POST /api/v1/partner/update/ — обновить прайс по URL
POST /api/v1/partner/upload/ — загрузить прайс файлом
GET/POST /api/v1/partner/state/ — статус приёма заказов
GET /api/v1/partner/orders/ — заказы поставщика
