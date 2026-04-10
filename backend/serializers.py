from rest_framework import serializers
from .models import (
    User, Shop, Category, Product, ProductInfo,
    Parameter, ProductParameter, Contact, Order, OrderItem
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 'type']
        read_only_fields = ['id']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['email', 'username', 'first_name', 'last_name', 'password', 'type']

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            password=validated_data['password'],
            type=validated_data.get('type', User.USER),
        )
        return user


class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ['id', 'name', 'url', 'state']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']


class ProductParameterSerializer(serializers.ModelSerializer):
    parameter = serializers.StringRelatedField()

    class Meta:
        model = ProductParameter
        fields = ['parameter', 'value']


class ProductInfoSerializer(serializers.ModelSerializer):
    product_parameters = ProductParameterSerializer(many=True, read_only=True)
    product = serializers.StringRelatedField()
    shop = serializers.StringRelatedField()

    class Meta:
        model = ProductInfo
        fields = ['id', 'model', 'external_id', 'product', 'shop', 'quantity', 'price', 'price_rrc', 'product_parameters']


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ['id', 'city', 'street', 'house', 'apartment', 'phone']
        read_only_fields = ['id']


class OrderItemSerializer(serializers.ModelSerializer):
    product_info = ProductInfoSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product_info', 'quantity']


class OrderItemCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['product_info', 'quantity']


class OrderSerializer(serializers.ModelSerializer):
    ordered_items = OrderItemSerializer(many=True, read_only=True)
    contact = ContactSerializer(read_only=True)
    total_sum = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['id', 'dt', 'status', 'contact', 'ordered_items', 'total_sum']

    def get_total_sum(self, obj):
        return sum(item.quantity * item.product_info.price for item in obj.ordered_items.all())


class PartnerOrderItemSerializer(serializers.ModelSerializer):
    product_info = ProductInfoSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product_info', 'quantity']


class PartnerOrderSerializer(serializers.ModelSerializer):
    # показываем поставщику только его позиции заказа, не чужие
    ordered_items = serializers.SerializerMethodField()
    contact = ContactSerializer(read_only=True)
    # сумма только по товарам этого поставщика
    total_sum = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['id', 'dt', 'status', 'contact', 'ordered_items', 'total_sum']

    def get_ordered_items(self, obj):
        shop = self.context.get('shop')
        items = obj.ordered_items.filter(product_info__shop=shop)
        return PartnerOrderItemSerializer(items, many=True).data

    def get_total_sum(self, obj):
        shop = self.context.get('shop')
        items = obj.ordered_items.filter(product_info__shop=shop)
        return sum(item.quantity * item.product_info.price for item in items)
