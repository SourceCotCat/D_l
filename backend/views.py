import yaml
from django.core.mail import send_mail
from django.conf import settings
from django.db import IntegrityError
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    User, Shop, Category, Product, ProductInfo,
    Parameter, ProductParameter, Contact, Order, OrderItem
)
from .serializers import (
    PartnerOrderSerializer,
    UserSerializer, RegisterSerializer, ShopSerializer, CategorySerializer,
    ProductInfoSerializer, ContactSerializer, OrderSerializer,
    OrderItemCreateSerializer
)


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # создаём токен сразу при регистрации
            token, _ = Token.objects.get_or_create(user=user)
            send_mail(
                subject='Регистрация на сервисе закупок',
                message=f'Здравствуйте, {user.first_name}! Вы успешно зарегистрировались.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
            return Response({'token': token.key}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        if not email or not password:
            return Response({'error': 'Необходимо указать email и пароль'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'Неверные учётные данные'}, status=status.HTTP_401_UNAUTHORIZED)
        if not user.check_password(password):
            return Response({'error': 'Неверные учётные данные'}, status=status.HTTP_401_UNAUTHORIZED)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # удаляем токен  следующие запросы с ним будут отклонены
        request.user.auth_token.delete()
        return Response({'status': 'ok'})


class UserDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        # partial=True позволяет обновлять отдельные поля без передачи всех остальных
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ShopListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        # возвращаем только магазины, принимающие заказы
        shops = Shop.objects.filter(state=True)
        serializer = ShopSerializer(shops, many=True)
        return Response(serializer.data)


class CategoryListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        categories = Category.objects.all()
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)


class ProductListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        # берём только товары из активных магазинов
        queryset = ProductInfo.objects.select_related(
            'product', 'shop'
        ).prefetch_related('product_parameters__parameter').filter(shop__state=True)

        # необязательные фильтры через query params: ?shop_id=1&category_id=2
        shop_id = request.query_params.get('shop_id')
        category_id = request.query_params.get('category_id')

        if shop_id:
            queryset = queryset.filter(shop_id=shop_id)
        if category_id:
            queryset = queryset.filter(product__category_id=category_id)

        serializer = ProductInfoSerializer(queryset, many=True)
        return Response(serializer.data)


class ProductDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        try:
            product_info = ProductInfo.objects.select_related(
                'product', 'shop'
            ).prefetch_related('product_parameters__parameter').get(pk=pk)
        except ProductInfo.DoesNotExist:
            return Response({'error': 'Товар не найден'}, status=status.HTTP_404_NOT_FOUND)
        serializer = ProductInfoSerializer(product_info)
        return Response(serializer.data)


class BasketView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_basket(self, user):
        # get_or_create безопасен благодаря UniqueConstraint в модели Order
        order, _ = Order.objects.get_or_create(user=user, status=Order.NEW)
        return order

    def get(self, request):
        basket = self._get_basket(request.user)
        serializer = OrderSerializer(basket)
        return Response(serializer.data)

    def post(self, request):
        # ожидаем список: [{"product_info": 1, "quantity": 2}, ...]
        items = request.data.get('items')
        if not items or not isinstance(items, list):
            return Response({'error': 'Необходимо передать список товаров'}, status=status.HTTP_400_BAD_REQUEST)
        basket = self._get_basket(request.user)
        errors = []
        created_count = 0
        for item in items:
            serializer = OrderItemCreateSerializer(data=item)
            if serializer.is_valid():
                try:
                    obj, created = OrderItem.objects.get_or_create(
                        order=basket,
                        product_info=serializer.validated_data['product_info'],
                        defaults={'quantity': serializer.validated_data['quantity']}
                    )
                    if not created:
                        # товар уже в корзине — увеличиваем количество
                        obj.quantity += serializer.validated_data['quantity']
                        obj.save()
                    created_count += 1
                except Exception as e:
                    errors.append(str(e))
            else:
                errors.append(serializer.errors)
        return Response({'created': created_count, 'errors': errors})

    def put(self, request):
        # ожидаем список: [{"id": 1, "quantity": 3}, ...]
        items = request.data.get('items')
        if not items or not isinstance(items, list):
            return Response({'error': 'Необходимо передать список товаров'}, status=status.HTTP_400_BAD_REQUEST)
        basket = self._get_basket(request.user)
        updated_count = 0
        for item in items:
            item_id = item.get('id')
            quantity = item.get('quantity')
            if item_id and quantity:
                updated = OrderItem.objects.filter(order=basket, id=item_id).update(quantity=quantity)
                updated_count += updated
        return Response({'updated': updated_count})

    def delete(self, request):
        # ожидаем список id позиций корзины: {"items": [1, 2, 3]}
        items_ids = request.data.get('items')
        if not items_ids:
            return Response({'error': 'Необходимо передать список id товаров'}, status=status.HTTP_400_BAD_REQUEST)
        basket = self._get_basket(request.user)
        deleted, _ = OrderItem.objects.filter(order=basket, id__in=items_ids).delete()
        return Response({'deleted': deleted})


class ContactView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # возвращаем все адреса доставки текущего пользователя
        contacts = Contact.objects.filter(user=request.user)
        serializer = ContactSerializer(contacts, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ContactSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        # id контакта передаётся в теле запроса
        contact_id = request.data.get('id')
        try:
            contact = Contact.objects.get(id=contact_id, user=request.user)
        except Contact.DoesNotExist:
            return Response({'error': 'Контакт не найден'}, status=status.HTTP_404_NOT_FOUND)
        serializer = ContactSerializer(contact, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        contact_id = request.data.get('id')
        deleted, _ = Contact.objects.filter(id=contact_id, user=request.user).delete()
        return Response({'deleted': deleted})


class OrderConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        contact_id = request.data.get('contact')
        if not contact_id:
            return Response({'error': 'Необходимо указать контакт'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            contact = Contact.objects.get(id=contact_id, user=request.user)
        except Contact.DoesNotExist:
            return Response({'error': 'Контакт не найден'}, status=status.HTTP_404_NOT_FOUND)

        # используем filter().first() вместо get() чтобы избежать исключений
        basket = Order.objects.filter(user=request.user, status=Order.NEW).first()
        if not basket:
            return Response({'error': 'Корзина пуста'}, status=status.HTTP_400_BAD_REQUEST)
        if not basket.ordered_items.exists():
            return Response({'error': 'В корзине нет товаров'}, status=status.HTTP_400_BAD_REQUEST)

        basket.contact = contact
        basket.status = Order.CONFIRMED
        basket.save()

        total = sum(item.quantity * item.product_info.price for item in basket.ordered_items.all())
        items_text = '\n'.join(
            f'- {item.product_info.product.name} x{item.quantity} = {item.quantity * item.product_info.price} руб.'
            for item in basket.ordered_items.all()
        )

        # письмо покупателю с подтверждением заказа
        send_mail(
            subject=f'Подтверждение заказа #{basket.id}',
            message=(
                f'Ваш заказ #{basket.id} подтверждён.\n\n'
                f'Товары:\n{items_text}\n\n'
                f'Итого: {total} руб.\n\n'
                f'Адрес доставки: {contact.city}, {contact.street}, {contact.house}'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[request.user.email],
            fail_silently=True,
        )

        # накладная администратору для исполнения заказа
        send_mail(
            subject=f'Новый заказ #{basket.id}',
            message=(
                f'Получен новый заказ #{basket.id} от {request.user.email}.\n\n'
                f'Товары:\n{items_text}\n\n'
                f'Итого: {total} руб.\n\n'
                f'Адрес доставки: {contact.city}, {contact.street}, {contact.house}'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.ADMIN_EMAIL],
            fail_silently=True,
        )

        return Response({'status': 'ok', 'order_id': basket.id})


class OrderListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # корзина (NEW) не показывается в списке заказов
        orders = Order.objects.filter(
            user=request.user
        ).exclude(status=Order.NEW).prefetch_related(
            'ordered_items__product_info__product',
            'ordered_items__product_info__product_parameters__parameter',
        ).select_related('contact')
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)


class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            order = Order.objects.prefetch_related(
                'ordered_items__product_info__product',
                'ordered_items__product_info__product_parameters__parameter',
            ).select_related('contact').get(pk=pk, user=request.user)
        except Order.DoesNotExist:
            return Response({'error': 'Заказ не найден'}, status=status.HTTP_404_NOT_FOUND)
        serializer = OrderSerializer(order)
        return Response(serializer.data)


class OrderStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        # только администратор (is_staff) может менять статус заказа
        if not request.user.is_staff:
            return Response({'error': 'Недостаточно прав'}, status=status.HTTP_403_FORBIDDEN)
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response({'error': 'Заказ не найден'}, status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get('status')
        allowed = [s[0] for s in Order.STATUS_CHOICES]
        if new_status not in allowed:
            return Response(
                {'error': f'Недопустимый статус. Допустимые значения: {allowed}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.status = new_status
        order.save()

        # уведомляем покупателя об изменении статуса
        send_mail(
            subject=f'Статус заказа #{order.id} изменён',
            message=f'Статус вашего заказа #{order.id} изменён на «{order.get_status_display()}».',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.user.email],
            fail_silently=True,
        )

        serializer = OrderSerializer(order)
        return Response(serializer.data)


class PartnerUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.type != User.SHOP:
            return Response({'error': 'Только для поставщиков'}, status=status.HTTP_403_FORBIDDEN)
        url = request.data.get('url')
        if not url:
            return Response({'error': 'Необходимо указать url'}, status=status.HTTP_400_BAD_REQUEST)
        import requests as req
        try:
            response = req.get(url)
            data = yaml.safe_load(response.content)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return _import_yaml_data(data, request.user)


class PartnerUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.type != User.SHOP:
            return Response({'error': 'Только для поставщиков'}, status=status.HTTP_403_FORBIDDEN)
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'Необходимо загрузить файл'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            data = yaml.safe_load(file.read())
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return _import_yaml_data(data, request.user)


def _import_yaml_data(data, user):
    # создаём или находим магазин поставщика по названию из yaml
    shop, _ = Shop.objects.get_or_create(name=data['shop'], defaults={'user': user})

    for category_data in data.get('categories', []):
        category, _ = Category.objects.get_or_create(id=category_data['id'], defaults={'name': category_data['name']})
        category.name = category_data['name']
        category.shops.add(shop)
        category.save()

    # удаляем старые позиции магазина перед загрузкой нового прайса
    ProductInfo.objects.filter(shop=shop).delete()

    for item in data.get('goods', []):
        category = Category.objects.get(id=item['category'])
        product, _ = Product.objects.get_or_create(name=item['name'], category=category)

        product_info = ProductInfo.objects.create(
            product=product,
            external_id=item['id'],
            model=item.get('model', ''),
            price=item['price'],
            price_rrc=item['price_rrc'],
            quantity=item['quantity'],
            shop=shop,
        )

        # сохраняем характеристики товара из блока parameters
        for param_name, param_value in item.get('parameters', {}).items():
            parameter, _ = Parameter.objects.get_or_create(name=param_name)
            ProductParameter.objects.create(
                product_info=product_info,
                parameter=parameter,
                value=str(param_value),
            )

    return Response({'status': 'ok'})


class PartnerStateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.type != User.SHOP:
            return Response({'error': 'Только для поставщиков'}, status=status.HTTP_403_FORBIDDEN)
        try:
            shop = Shop.objects.get(user=request.user)
        except Shop.DoesNotExist:
            return Response({'error': 'Магазин не найден'}, status=status.HTTP_404_NOT_FOUND)
        serializer = ShopSerializer(shop)
        return Response(serializer.data)

    def post(self, request):
        if request.user.type != User.SHOP:
            return Response({'error': 'Только для поставщиков'}, status=status.HTTP_403_FORBIDDEN)
        try:
            shop = Shop.objects.get(user=request.user)
        except Shop.DoesNotExist:
            return Response({'error': 'Магазин не найден'}, status=status.HTTP_404_NOT_FOUND)
        state = request.data.get('state')
        if state is None:
            return Response({'error': 'Необходимо указать state'}, status=status.HTTP_400_BAD_REQUEST)
        # True — принимаем заказы, False — приостанавливаем
        shop.state = state
        shop.save()
        return Response({'status': 'ok', 'state': shop.state})


class PartnerOrdersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.type != User.SHOP:
            return Response({'error': 'Только для поставщиков'}, status=status.HTTP_403_FORBIDDEN)
        try:
            shop = Shop.objects.get(user=request.user)
        except Shop.DoesNotExist:
            return Response({'error': 'Магазин не найден'}, status=status.HTTP_404_NOT_FOUND)
        # distinct() нужен чтобы заказ не дублировался если в нём несколько товаров этого магазина
        orders = Order.objects.filter(
            ordered_items__product_info__shop=shop
        ).exclude(status=Order.NEW).prefetch_related(
            'ordered_items__product_info__product',
            'ordered_items__product_info__product_parameters__parameter',
        ).select_related('contact', 'user').distinct()
        # передаём shop в контекст — сериализатор покажет только позиции этого магазина
        serializer = PartnerOrderSerializer(orders, many=True, context={'shop': shop})
        return Response(serializer.data)
