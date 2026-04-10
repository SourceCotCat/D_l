from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch
from .models import User, Shop, Category, Product, ProductInfo, Contact, Order, OrderItem


class BaseTestCase(TestCase):
    """Базовый класс с общими хелперами для всех тестов."""

    def setUp(self):
        self.client = APIClient()

    def create_buyer(self, email='buyer@test.com', password='testpass123'):
        return User.objects.create_user(
            email=email, username=email,
            password=password, type=User.USER,
        )

    def create_shop_user(self, email='shop@test.com', password='testpass123'):
        return User.objects.create_user(
            email=email, username=email,
            password=password, type=User.SHOP,
        )

    def authenticate(self, user):
        from rest_framework.authtoken.models import Token
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def create_product_info(self, shop=None):
        if not shop:
            shop_user = self.create_shop_user(email='owner@test.com')
            shop = Shop.objects.create(name='Тестовый магазин', user=shop_user, state=True)
        category = Category.objects.create(name='Категория')
        product = Product.objects.create(name='Товар', category=category)
        return ProductInfo.objects.create(
            product=product, shop=shop, external_id=999,
            model='test/model', price=1000, price_rrc=1200, quantity=10,
        )

    def create_contact(self, user):
        return Contact.objects.create(
            user=user, city='Москва', street='Ленина',
            house='1', phone='+79991234567',
        )


class RegisterViewTest(BaseTestCase):
    """Тесты регистрации пользователя."""

    @patch('backend.tasks.send_registration_email.delay')
    def test_register_success(self, mock_email):
        response = self.client.post(reverse('user-register'), {
            'email': 'new@test.com', 'username': 'newuser',
            'first_name': 'Иван', 'last_name': 'Иванов',
            'password': 'testpass123', 'type': 'buyer',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        # убеждаемся что задача отправки письма поставлена в очередь
        mock_email.assert_called_once()

    def test_register_duplicate_email(self):
        self.create_buyer()
        response = self.client.post(reverse('user-register'), {
            'email': 'buyer@test.com', 'username': 'buyer2', 'password': 'testpass123',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_missing_fields(self):
        response = self.client.post(reverse('user-register'), {'email': 'x@test.com'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginViewTest(BaseTestCase):
    """Тесты авторизации."""

    def test_login_success(self):
        self.create_buyer()
        response = self.client.post(reverse('user-login'), {
            'email': 'buyer@test.com', 'password': 'testpass123',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

    def test_login_wrong_password(self):
        self.create_buyer()
        response = self.client.post(reverse('user-login'), {
            'email': 'buyer@test.com', 'password': 'wrongpass',
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_unknown_email(self):
        response = self.client.post(reverse('user-login'), {
            'email': 'nobody@test.com', 'password': 'testpass123',
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_missing_fields(self):
        response = self.client.post(reverse('user-login'), {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserDetailViewTest(BaseTestCase):
    """Тесты просмотра и редактирования профиля."""

    def test_get_profile_authenticated(self):
        user = self.create_buyer()
        self.authenticate(user)
        response = self.client.get(reverse('user-details'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], user.email)

    def test_get_profile_unauthenticated(self):
        response = self.client.get(reverse('user-details'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_patch_profile(self):
        user = self.create_buyer()
        self.authenticate(user)
        response = self.client.patch(reverse('user-details'), {'first_name': 'Пётр'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'Пётр')


class ProductListViewTest(BaseTestCase):
    """Тесты получения списка товаров."""

    def test_product_list_empty(self):
        response = self.client.get(reverse('product-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_product_list_returns_items(self):
        self.create_product_info()
        response = self.client.get(reverse('product-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_product_list_filter_by_shop(self):
        pi = self.create_product_info()
        response = self.client.get(reverse('product-list'), {'shop_id': pi.shop.id})
        self.assertEqual(len(response.data), 1)

    def test_product_list_filter_by_category(self):
        pi = self.create_product_info()
        response = self.client.get(reverse('product-list'), {'category_id': pi.product.category.id})
        self.assertEqual(len(response.data), 1)

    def test_inactive_shop_products_hidden(self):
        shop_user = self.create_shop_user()
        shop = Shop.objects.create(name='Закрытый', user=shop_user, state=False)
        self.create_product_info(shop=shop)
        response = self.client.get(reverse('product-list'))
        self.assertEqual(len(response.data), 0)


class ProductDetailViewTest(BaseTestCase):
    """Тесты получения детальной информации о товаре."""

    def test_product_detail_found(self):
        pi = self.create_product_info()
        response = self.client.get(reverse('product-detail', args=[pi.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], pi.id)

    def test_product_detail_not_found(self):
        response = self.client.get(reverse('product-detail', args=[9999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class BasketViewTest(BaseTestCase):
    """Тесты работы с корзиной."""

    def test_get_empty_basket(self):
        user = self.create_buyer()
        self.authenticate(user)
        response = self.client.get(reverse('basket'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_basket_requires_auth(self):
        response = self.client.get(reverse('basket'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_add_item_to_basket(self):
        user = self.create_buyer()
        self.authenticate(user)
        pi = self.create_product_info()
        response = self.client.post(reverse('basket'), {
            'items': [{'product_info': pi.id, 'quantity': 2}]
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['created'], 1)

    def test_add_invalid_item(self):
        user = self.create_buyer()
        self.authenticate(user)
        response = self.client.post(reverse('basket'), {
            'items': [{'product_info': 9999, 'quantity': 1}]
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['errors']), 1)

    def test_add_item_no_list(self):
        user = self.create_buyer()
        self.authenticate(user)
        response = self.client.post(reverse('basket'), {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_item_quantity(self):
        user = self.create_buyer()
        self.authenticate(user)
        pi = self.create_product_info()
        self.client.post(reverse('basket'), {
            'items': [{'product_info': pi.id, 'quantity': 1}]
        }, format='json')
        basket = Order.objects.get(user=user, status=Order.NEW)
        item = basket.ordered_items.first()
        response = self.client.put(reverse('basket'), {
            'items': [{'id': item.id, 'quantity': 5}]
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['updated'], 1)

    def test_delete_item_from_basket(self):
        user = self.create_buyer()
        self.authenticate(user)
        pi = self.create_product_info()
        self.client.post(reverse('basket'), {
            'items': [{'product_info': pi.id, 'quantity': 1}]
        }, format='json')
        basket = Order.objects.get(user=user, status=Order.NEW)
        item = basket.ordered_items.first()
        response = self.client.delete(reverse('basket'), {'items': [item.id]}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['deleted'], 1)

    def test_delete_no_items(self):
        user = self.create_buyer()
        self.authenticate(user)
        response = self.client.delete(reverse('basket'), {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ContactViewTest(BaseTestCase):
    """Тесты управления адресами доставки."""

    def test_create_contact(self):
        user = self.create_buyer()
        self.authenticate(user)
        response = self.client.post(reverse('user-contact'), {
            'city': 'Москва', 'street': 'Ленина', 'house': '1', 'phone': '+79991234567',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_get_contacts(self):
        user = self.create_buyer()
        self.authenticate(user)
        self.create_contact(user)
        response = self.client.get(reverse('user-contact'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_update_contact(self):
        user = self.create_buyer()
        self.authenticate(user)
        contact = self.create_contact(user)
        response = self.client.put(reverse('user-contact'), {
            'id': contact.id, 'city': 'Питер',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['city'], 'Питер')

    def test_update_contact_not_found(self):
        user = self.create_buyer()
        self.authenticate(user)
        response = self.client.put(reverse('user-contact'), {'id': 9999, 'city': 'Х'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_contact(self):
        user = self.create_buyer()
        self.authenticate(user)
        contact = self.create_contact(user)
        response = self.client.delete(reverse('user-contact'), {'id': contact.id}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['deleted'], 1)


class OrderConfirmViewTest(BaseTestCase):
    """Тесты подтверждения заказа."""

    @patch('backend.tasks.send_order_confirmation_email.delay')
    @patch('backend.tasks.send_order_invoice_email.delay')
    def test_confirm_order_success(self, mock_invoice, mock_confirm):
        user = self.create_buyer()
        self.authenticate(user)
        pi = self.create_product_info()
        contact = self.create_contact(user)
        self.client.post(reverse('basket'), {
            'items': [{'product_info': pi.id, 'quantity': 1}]
        }, format='json')
        response = self.client.post(reverse('order-confirm'), {'contact': contact.id}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('order_id', response.data)
        # оба письма должны быть поставлены в очередь
        mock_confirm.assert_called_once()
        mock_invoice.assert_called_once()

    def test_confirm_no_contact_provided(self):
        user = self.create_buyer()
        self.authenticate(user)
        response = self.client.post(reverse('order-confirm'), {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_confirm_contact_not_found(self):
        user = self.create_buyer()
        self.authenticate(user)
        pi = self.create_product_info()
        self.client.post(reverse('basket'), {
            'items': [{'product_info': pi.id, 'quantity': 1}]
        }, format='json')
        response = self.client.post(reverse('order-confirm'), {'contact': 9999}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_confirm_empty_basket(self):
        user = self.create_buyer()
        self.authenticate(user)
        contact = self.create_contact(user)
        response = self.client.post(reverse('order-confirm'), {'contact': contact.id}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('backend.tasks.send_order_confirmation_email.delay')
    @patch('backend.tasks.send_order_invoice_email.delay')
    def test_confirm_changes_status_to_confirmed(self, mock_invoice, mock_confirm):
        user = self.create_buyer()
        self.authenticate(user)
        pi = self.create_product_info()
        contact = self.create_contact(user)
        self.client.post(reverse('basket'), {
            'items': [{'product_info': pi.id, 'quantity': 1}]
        }, format='json')
        self.client.post(reverse('order-confirm'), {'contact': contact.id}, format='json')
        order = Order.objects.get(user=user, status=Order.CONFIRMED)
        self.assertEqual(order.status, Order.CONFIRMED)


class OrderListViewTest(BaseTestCase):
    """Тесты списка заказов."""

    @patch('backend.tasks.send_order_confirmation_email.delay')
    @patch('backend.tasks.send_order_invoice_email.delay')
    def test_order_appears_after_confirm(self, mock_invoice, mock_confirm):
        user = self.create_buyer()
        self.authenticate(user)
        pi = self.create_product_info()
        contact = self.create_contact(user)
        self.client.post(reverse('basket'), {
            'items': [{'product_info': pi.id, 'quantity': 1}]
        }, format='json')
        self.client.post(reverse('order-confirm'), {'contact': contact.id}, format='json')
        response = self.client.get(reverse('order-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_basket_not_in_order_list(self):
        user = self.create_buyer()
        self.authenticate(user)
        Order.objects.create(user=user, status=Order.NEW)
        response = self.client.get(reverse('order-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_order_list_requires_auth(self):
        response = self.client.get(reverse('order-list'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class OrderDetailViewTest(BaseTestCase):
    """Тесты детальной страницы заказа."""

    def test_order_detail_found(self):
        user = self.create_buyer()
        self.authenticate(user)
        order = Order.objects.create(user=user, status=Order.CONFIRMED)
        response = self.client.get(reverse('order-detail', args=[order.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_order_detail_not_found(self):
        user = self.create_buyer()
        self.authenticate(user)
        response = self.client.get(reverse('order-detail', args=[9999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_order_detail_other_user(self):
        user1 = self.create_buyer(email='u1@test.com')
        user2 = self.create_buyer(email='u2@test.com')
        order = Order.objects.create(user=user1, status=Order.CONFIRMED)
        self.authenticate(user2)
        response = self.client.get(reverse('order-detail', args=[order.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class OrderStatusViewTest(BaseTestCase):
    """Тесты изменения статуса заказа (только для staff)."""

    @patch('backend.tasks.send_order_status_email.delay')
    def test_change_status_as_staff(self, mock_email):
        buyer = self.create_buyer()
        order = Order.objects.create(user=buyer, status=Order.CONFIRMED)
        staff = User.objects.create_user(
            email='admin@test.com', username='admin',
            password='adminpass', is_staff=True,
        )
        self.authenticate(staff)
        response = self.client.patch(
            reverse('order-status', args=[order.id]),
            {'status': Order.ASSEMBLED}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], Order.ASSEMBLED)
        mock_email.assert_called_once()

    def test_change_status_as_regular_user(self):
        buyer = self.create_buyer()
        order = Order.objects.create(user=buyer, status=Order.CONFIRMED)
        self.authenticate(buyer)
        response = self.client.patch(
            reverse('order-status', args=[order.id]),
            {'status': Order.ASSEMBLED}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_change_status_invalid_value(self):
        buyer = self.create_buyer()
        order = Order.objects.create(user=buyer, status=Order.CONFIRMED)
        staff = User.objects.create_user(
            email='admin2@test.com', username='admin2',
            password='adminpass', is_staff=True,
        )
        self.authenticate(staff)
        response = self.client.patch(
            reverse('order-status', args=[order.id]),
            {'status': 'wrong_status'}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_status_order_not_found(self):
        staff = User.objects.create_user(
            email='admin3@test.com', username='admin3',
            password='adminpass', is_staff=True,
        )
        self.authenticate(staff)
        response = self.client.patch(
            reverse('order-status', args=[9999]),
            {'status': Order.ASSEMBLED}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ShopListViewTest(BaseTestCase):
    """Тесты списка магазинов."""

    def test_only_active_shops_returned(self):
        u1 = self.create_shop_user(email='s1@test.com')
        u2 = self.create_shop_user(email='s2@test.com')
        Shop.objects.create(name='Активный', user=u1, state=True)
        Shop.objects.create(name='Закрытый', user=u2, state=False)
        response = self.client.get(reverse('shop-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Активный')


class PartnerStateViewTest(BaseTestCase):
    """Тесты управления статусом магазина поставщиком."""

    def test_get_state(self):
        user = self.create_shop_user()
        Shop.objects.create(name='Мой магазин', user=user, state=True)
        self.authenticate(user)
        response = self.client.get(reverse('partner-state'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['state'])

    def test_set_state_false(self):
        user = self.create_shop_user()
        Shop.objects.create(name='Мой магазин', user=user, state=True)
        self.authenticate(user)
        response = self.client.post(reverse('partner-state'), {'state': False}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['state'])

    def test_buyer_cannot_access_partner_state(self):
        user = self.create_buyer()
        self.authenticate(user)
        response = self.client.get(reverse('partner-state'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_state_shop_not_found(self):
        user = self.create_shop_user()
        self.authenticate(user)
        response = self.client.get(reverse('partner-state'))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_state_missing_value(self):
        user = self.create_shop_user()
        Shop.objects.create(name='Мой магазин', user=user, state=True)
        self.authenticate(user)
        response = self.client.post(reverse('partner-state'), {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
