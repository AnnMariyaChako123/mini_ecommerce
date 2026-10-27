from django.urls import path
from . import views

urlpatterns = [
    path("", views.cart_view, name="cart"),
    path('add/<int:product_id>/', views.add_to_cart, name="add_to_cart"),
    path('update/<int:item_id>/<str:action>/',views.update_quantity,name='update_quantity'),
    path('checkout/', views.checkout, name='checkout'),
    path('orders/', views.order_history, name='order_history'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('payment/verify/', views.verify_payment, name='verify_payment'),
    path('order/<int:order_id>/cancel/',views.cancel_order,name='cancel_order'),
    path("razorpay/webhook/",views.razorpay_webhook,name="razorpay_webhook"),
    path('payment-failed/',views.payment_failed,name='payment_failed'),
     path("api/delivery-status/<int:order_id>/",views.delivery_status_api,name="delivery_status_api"),
]