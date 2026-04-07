from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Shop, Category, Product, ProductInfo, Parameter, ProductParameter, Contact, Order, OrderItem


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'username', 'type', 'is_staff']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Тип пользователя', {'fields': ('type',)}),
    )


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ['name', 'url', 'state']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category']


class ProductParameterInline(admin.TabularInline):
    model = ProductParameter
    extra = 0


@admin.register(ProductInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    list_display = ['product', 'shop', 'price', 'quantity']
    inlines = [ProductParameterInline]


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['user', 'city', 'street', 'phone']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'status', 'dt']
    list_filter = ['status']
    inlines = [OrderItemInline]
