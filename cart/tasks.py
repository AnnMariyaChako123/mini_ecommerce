
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings


@shared_task
def send_order_confirmation_email(
    username,
    email,
    order_id,
    total_amount,
    order_status
):
    subject = f"Order Confirmation - Order {order_id}"

    message = (
        f"Hi {username},\n\n"
        f"Your payment was successful.\n"
        f"Order ID: {order_id}\n"
        f"Total Amount: ₹{total_amount}\n"
        f"Status: {order_status}\n\n"
        "Thank you for your order!"
    )

    return send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )
