from django.urls import path
from .views import (
    RegisterView, LoginView, LogoutView, UserDetailView,
    ShopListView, CategoryListView, ProductListView, ProductDetailView,
    BasketView, ContactView, OrderConfirmView, OrderListView, OrderDetailView,
    OrderStatusView,
    PartnerUpdateView, PartnerUploadView, PartnerStateView, PartnerOrdersView,
)

urlpatterns = [
    # авторизация и профиль пользователя
    path('user/register/', RegisterView.as_view(), name='user-register'),
    path('user/login/', LoginView.as_view(), name='user-login'),
    path('user/logout/', LogoutView.as_view(), name='user-logout'),
    path('user/details/', UserDetailView.as_view(), name='user-details'),
    path('user/contact/', ContactView.as_view(), name='user-contact'),

    # каталог товаров
    path('shops/', ShopListView.as_view(), name='shop-list'),
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('products/', ProductListView.as_view(), name='product-list'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),

    # корзина и заказы
    path('basket/', BasketView.as_view(), name='basket'),
    path('order/', OrderListView.as_view(), name='order-list'),
    path('order/confirm/', OrderConfirmView.as_view(), name='order-confirm'),
    path('order/<int:pk>/', OrderDetailView.as_view(), name='order-detail'),
    path('order/<int:pk>/status/', OrderStatusView.as_view(), name='order-status'),

    # эндпоинты для поставщиков
    path('partner/update/', PartnerUpdateView.as_view(), name='partner-update'),
    path('partner/upload/', PartnerUploadView.as_view(), name='partner-upload'),
    path('partner/state/', PartnerStateView.as_view(), name='partner-state'),
    path('partner/orders/', PartnerOrdersView.as_view(), name='partner-orders'),
]
