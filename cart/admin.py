
from django.contrib import admin
from django.db.models import Sum
from .models import Cart, cartItem, Order, OrderItem
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.urls import path


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'created_at')
    search_fields = ('user__username',)



@admin.register(cartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'cart', 'product', 'quantity')
    search_fields = ('product__name',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'customer_name',
        'total_amount',
        'status',
        'payment_status',
        'shipping_charge',
        'shipping_status',
        'created_at',
    )

    list_filter = (
        'status',
        'payment_status',
        'shipping_status',
        'created_at',
    )

    search_fields = (
        'id',
        'user__username',
        'razorpay_order_id',
        'razorpay_payment_id',
    )

    fields = (
        'user',
        'total_amount',
        'status',
        'payment_status',
        'shipping_charge',
        'shipping_status',
        'delivery_address',
        'razorpay_order_id',
        'razorpay_payment_id',
        'created_at',
    )

    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

    @admin.display(description='Customer')
    def customer_name(self, obj):
        return obj.user.username if obj.user else 'Guest'

    @admin.display(description='Total Sales')
    def total_sales(self, obj):
        return obj.total_amount


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'product', 'quantity', 'price')
    search_fields = ('order__id', 'product__name')


def sales_dashboard_view(request):
    total_orders = Order.objects.count()

    total_sales = (
        Order.objects.filter(payment_status='Paid')
        .aggregate(total=Sum('total_amount'))['total'] or 0
    )

    pending_orders = Order.objects.filter(status='Pending').count()
    paid_orders = Order.objects.filter(payment_status='Paid').count()

    context = {
        **admin.site.each_context(request),
        'title': 'Sales Dashboard',
        'total_orders': total_orders,
        'total_sales': total_sales,
        'pending_orders': pending_orders,
        'paid_orders': paid_orders,
    }

    return render(request, 'cart/sales_dashboard.html', context)


original_get_urls = admin.site.get_urls


def custom_get_urls():
    custom_urls = [
        path(
            'sales-dashboard/',
            admin.site.admin_view(sales_dashboard_view),
            name='sales-dashboard',
        ),
    ]
    return custom_urls + original_get_urls()


admin.site.get_urls = custom_get_urls
