from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    USER = 'buyer'
    SHOP = 'shop'
    TYPE_CHOICES = [
        (USER, 'Покупатель'),
        (SHOP, 'Магазин'),
    ]
    # тип пользователя: покупатель или поставщик
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=USER)
    email = models.EmailField(unique=True)

    # авторизация по email вместо username
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email


class Shop(models.Model):
    name = models.CharField(max_length=50)
    url = models.URLField(null=True, blank=True)
    # один магазин — один пользователь-поставщик
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    # state=True — магазин принимает заказы, False — не принимает
    state = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=50)
    # категория может присутствовать в нескольких магазинах
    shops = models.ManyToManyField(Shop, related_name='categories', blank=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')

    def __str__(self):
        return self.name


class ProductInfo(models.Model):
    model = models.CharField(max_length=100, blank=True)
    # id товара в системе поставщика
    external_id = models.PositiveIntegerField()
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_infos')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='product_infos')
    quantity = models.PositiveIntegerField()
    price = models.PositiveIntegerField()
    # рекомендованная розничная цена
    price_rrc = models.PositiveIntegerField()

    class Meta:
        # один товар поставщика не может дублироваться в одном магазине
        unique_together = ('shop', 'external_id')

    def __str__(self):
        return f'{self.product.name} ({self.shop.name})'


class Parameter(models.Model):
    # название характеристики, например "Цвет" или "Диагональ"
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class ProductParameter(models.Model):
    product_info = models.ForeignKey(ProductInfo, on_delete=models.CASCADE, related_name='product_parameters')
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE)
    value = models.CharField(max_length=200)

    class Meta:
        # одна характеристика не может повторяться у одного товара
        unique_together = ('product_info', 'parameter')


class Contact(models.Model):
    # адрес доставки пользователя
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contacts')
    city = models.CharField(max_length=50)
    street = models.CharField(max_length=100)
    house = models.CharField(max_length=15)
    apartment = models.CharField(max_length=15, blank=True)
    phone = models.CharField(max_length=20)

    def __str__(self):
        return f'{self.city}, {self.street}, {self.house}'


class Order(models.Model):
    NEW = 'new'
    CONFIRMED = 'confirmed'
    ASSEMBLED = 'assembled'
    SENT = 'sent'
    DELIVERED = 'delivered'
    CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (NEW, 'Новый'),
        (CONFIRMED, 'Подтверждён'),
        (ASSEMBLED, 'Собран'),
        (SENT, 'Отправлен'),
        (DELIVERED, 'Доставлен'),
        (CANCELLED, 'Отменён'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    dt = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=NEW)
    contact = models.ForeignKey(Contact, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        # у одного пользователя может быть только одна корзина (статус new)
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                condition=models.Q(status='new'),
                name='unique_new_order_per_user'
            )
        ]

    def __str__(self):
        return f'Заказ #{self.id} ({self.status})'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='ordered_items')
    product_info = models.ForeignKey(ProductInfo, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    class Meta:
        # один товар не может дублироваться в одном заказе
        unique_together = ('order', 'product_info')
