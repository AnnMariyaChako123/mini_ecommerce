from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

# Create your models here.
class category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name
class brand(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class product(models.Model):
    name = models.CharField(max_length=100)
    sku = models.CharField(max_length=50,unique=True)
    category = models.ForeignKey(category,on_delete=models.PROTECT)
    brand = models.ForeignKey(brand,on_delete=models.PROTECT)
    price = models.DecimalField(max_digits=10,decimal_places=2)
    stoct = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to="products/",blank=True,null=True)
    disc_perc = models.PositiveIntegerField(default=0)

    def get_disc_perc(self):
        discount =self.price * self.disc_perc / 100
        return self.price - discount

    def __str__(self):
        return self.name

class Wishlist(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    product = models.ForeignKey(
        'catalog.product',
        on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"


class Review(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    product = models.ForeignKey(
        'catalog.product',
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    rating = models.PositiveIntegerField(
        validators=[
        MinValueValidator(1),
        MaxValueValidator(5)
        ]
    )
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"

class EmailOTP(models.Model):
    email = models.EmailField(db_index=True)
    otp_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveIntegerField(default=0)
    is_used = models.BooleanField(default=False)

    def is_expired(self):
        return timezone.now() >= self.expires_at