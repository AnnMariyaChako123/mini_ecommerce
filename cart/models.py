from django.db import models
from django.conf import settings

class Cart(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True) 

    def __str__(self):
        return f"cart {self.id}"

class cartItem(models.Model):
    cart = models.ForeignKey(Cart,on_delete=models.CASCADE)
    product = models.ForeignKey("catalog.product", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.product.name
    

class Order(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    status = models.CharField(
        max_length=20,
        default='Pending'
    )

    payment_status = models.CharField(
        max_length=20,
        default='Pending'
    )

    razorpay_order_id = models.CharField(
        max_length=100,
        blank=True,
        default=''
    )

    razorpay_payment_id = models.CharField(
        max_length=100,
        blank=True,
        default=''
    )

    created_at = models.DateTimeField(auto_now_add=True)

    delivery_address = models.TextField(default='')


    shipping_charge = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=50.00
    )

    shipping_status = models.CharField(
    max_length=20,
    choices=[
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Shipped', 'Shipped'),
        ('Out for Delivery', 'Out for Delivery'),
        ('Delivered', 'Delivered'),
    ],
    default='Pending'
    )
    def __str__(self):
        return f"Order {self.id}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        "catalog.product",
        on_delete=models.PROTECT
    )
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    def __str__(self):
        return self.product.name


class RazorpayWebhookEvent(models.Model):
    event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=100)
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)