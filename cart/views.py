from decimal import Decimal

import razorpay

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST

from catalog.models import product
from .models import Cart, cartItem, Order, OrderItem
from django.core.mail import send_mail
from .tasks import send_order_confirmation_email

import hashlib
import hmac
import json

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from .models import RazorpayWebhookEvent

client = razorpay.Client(
    auth=(
        settings.RAZORPAY_KEY_ID,
        settings.RAZORPAY_KEY_SECRET
    )
)



def cart_view(request):
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(
            user=request.user
        )

        items = list(
            cartItem.objects.filter(
                cart=cart,
                product__stoct__gt=0
            ).select_related('product')
        )

        for item in items:
            item.subtotal = (
                item.product.get_disc_perc() * item.quantity
            )

        return render(request, 'cart/cart.html', {
            'items': items,
            'is_guest': False,
        })

    
    guest_cart = request.session.get('guest_cart', {})
    items = []

    for product_id, quantity in guest_cart.items():
        try:
            product_obj = product.objects.get(
                id=int(product_id),
                stoct__gt=0
            )

            quantity = int(quantity)

            items.append({
                'product': product_obj,
                'quantity': quantity,
                'subtotal': (
                    product_obj.get_disc_perc() * quantity
                ),
            })

        except (product.DoesNotExist, ValueError, TypeError):
            continue

    return render(request, 'cart/cart.html', {
        'items': items,
        'is_guest': True,
    })


@require_POST
def add_to_cart(request, product_id):
    product_obj = get_object_or_404(
        product,
        id=product_id
    )

    if product_obj.stoct < 1:
        return HttpResponse("Product is out of stock")

    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(
            user=request.user
        )

        cart_item, created = cartItem.objects.get_or_create(
            cart=cart,
            product=product_obj,
            defaults={'quantity': 1}
        )

        if not created:
            if cart_item.quantity < product_obj.stoct:
                cart_item.quantity += 1
                cart_item.save(update_fields=['quantity'])
            else:
                return HttpResponse(
                    "Maximum available stock reached"
                )

    else:
        guest_cart = request.session.get('guest_cart', {})
        product_id_str = str(product_obj.id)

        quantity = int(guest_cart.get(product_id_str, 0))

        if quantity < product_obj.stoct:
            guest_cart[product_id_str] = quantity + 1
            request.session['guest_cart'] = guest_cart
        else:
            return HttpResponse(
                "Maximum available stock reached"
            )

    return redirect('cart')



@require_POST
def update_quantity(request, item_id, action):
    if action not in ['increase', 'decrease']:
        return HttpResponse("Invalid quantity action", status=400)
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(
            user=request.user
        )

        cart_item = get_object_or_404(
            cartItem,
            id=item_id,
            cart=cart
        )

        if action == 'increase':
            if cart_item.quantity < cart_item.product.stoct:
                cart_item.quantity += 1
                cart_item.save(update_fields=['quantity'])

        elif action == 'decrease':
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                cart_item.save(update_fields=['quantity'])
            else:
                cart_item.delete()

    else:
        guest_cart = request.session.get('guest_cart', {})
        product_id_str = str(item_id)

        if product_id_str in guest_cart:
            try:
                product_obj = product.objects.get(
                    id=int(product_id_str)
                )
                quantity = int(guest_cart[product_id_str])

                if action == 'increase':
                    if quantity < product_obj.stoct:
                        guest_cart[product_id_str] = quantity + 1

                elif action == 'decrease':
                    if quantity > 1:
                        guest_cart[product_id_str] = quantity - 1
                    else:
                        del guest_cart[product_id_str]

                request.session['guest_cart'] = guest_cart
                request.session.save()

            except (product.DoesNotExist, ValueError, TypeError):
                guest_cart.pop(product_id_str, None)
                request.session['guest_cart'] = guest_cart

    return redirect('cart')


@login_required
def checkout(request):
    cart, created = Cart.objects.get_or_create(
        user=request.user
    )

    items = list(
        cartItem.objects.filter(
            cart=cart
        ).select_related('product')
    )

    if not items:
        return HttpResponse("Your cart is empty")

    
    subtotal = Decimal('0.00')

    for item in items:
        if item.quantity < 1:
            return HttpResponse("Invalid quantity")

        if item.quantity > item.product.stoct:
            return HttpResponse(
                f"Not enough stock for {item.product.name}"
            )

        item.discounted_price = item.product.get_disc_perc()
        item.subtotal = item.discounted_price * item.quantity
        subtotal += item.subtotal

    tax = (subtotal * Decimal('0.05')).quantize(
    Decimal('0.01')
    )

    shipping_charge = Decimal('50.00')

    total = subtotal + tax + shipping_charge

    
    print("CURRENT USER:", request.user.username)
    print("CART ITEMS:")

    for item in items:
        print({
            'product': item.product.name,
            'price': str(item.product.price),
            'discounted_price': str(item.discounted_price),
            'quantity': item.quantity,
            'subtotal': str(item.subtotal),
        })

    print("SUBTOTAL:", subtotal)
    print("TAX:", tax)
    print("TOTAL:", total)

    if request.method == 'POST':
        address = request.POST.get(
            'delivery_address', ''
        ).strip()

        if not address:
            return HttpResponse(
                "Please enter your delivery address"
            )

        
        try:
            with transaction.atomic():
                for item in items:
                    product_obj = product.objects.select_for_update().get(
                        id=item.product_id
                    )

                    if item.quantity > product_obj.stoct:
                        return HttpResponse(
                            f"Not enough stock for {product_obj.name}"
                        )

                order = Order.objects.create(
                    user=request.user,
                    total_amount=total,
                    delivery_address=address,
                    shipping_charge=shipping_charge,
                    shipping_status='Pending',
                    status='Pending',
                    payment_status='Pending'
                )

                for item in items:
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        quantity=item.quantity,
                        price=item.discounted_price
                    )

                razorpay_order = client.order.create({
                    'amount': int(total * 100),
                    'currency': 'INR',
                    'receipt': f'order_{order.id}'
                })

                order.razorpay_order_id = razorpay_order['id']
                order.save(update_fields=['razorpay_order_id'])

        except Exception as error:
            print("CHECKOUT / RAZORPAY ERROR:", repr(error))

            if 'order' in locals():
                order.delete()

            return HttpResponse(
                "Unable to create payment. Please try again.",
                status=500
            )

        return render(request, 'cart/payment.html', {
            'order': order,
            'razorpay_order_id': razorpay_order['id'],
            'razorpay_key_id': settings.RAZORPAY_KEY_ID,
            'amount': int(total * 100),
        })

    return render(request, 'cart/checkout.html', {
        'items': items,
        'subtotal': subtotal,
        'tax': tax,
        'shipping_charge': shipping_charge,
        'total': total,
    })



@login_required
def order_history(request):
    orders = Order.objects.filter(
        user=request.user
    ).order_by('-created_at')

    return render(request, 'cart/order_history.html', {
        'orders': orders,
    })



@login_required
def order_detail(request, order_id):
    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user
    )

    items = OrderItem.objects.filter(
        order=order
    ).select_related('product')

    return render(request, 'cart/order_detail.html', {
        'order': order,
        'items': items,
    })


@login_required
def verify_payment(request):
    if request.method != 'POST':
        return redirect('cart')

    razorpay_order_id = request.POST.get('razorpay_order_id')
    razorpay_payment_id = request.POST.get('razorpay_payment_id')
    razorpay_signature = request.POST.get('razorpay_signature')

    if not all([
        razorpay_order_id,
        razorpay_payment_id,
        razorpay_signature
    ]):
        return HttpResponse(
            "Payment verification details are missing.",
            status=400
        )

    try:
        order = get_object_or_404(
            Order,
            razorpay_order_id=razorpay_order_id,
            user=request.user
        )

        
        if order.payment_status == 'Paid':
            return render(
                request,
                'cart/order_success.html',
                {'order': order}
            )

        
        client.utility.verify_payment_signature({
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature,
        })

        low_stock_products = []

        with transaction.atomic():
            order = Order.objects.select_for_update().get(
                id=order.id
            )

            
            if order.payment_status != 'Paid':

                order_items = list(
                    OrderItem.objects.filter(
                        order=order
                    ).select_related('product')
                )

                
                for order_item in order_items:
                    product_obj = product.objects.select_for_update().get(
                        id=order_item.product_id
                    )

                    if product_obj.stoct < order_item.quantity:
                        raise ValueError(
                            f"Insufficient stock for {product_obj.name}"
                        )

                
                for order_item in order_items:
                    product_obj = product.objects.select_for_update().get(
                        id=order_item.product_id
                    )

                    product_obj.stoct -= order_item.quantity
                    product_obj.save(update_fields=['stoct'])

                    if product_obj.stoct <= 5:
                        low_stock_products.append({
                            'name': product_obj.name,
                            'sku': product_obj.sku,
                            'stock': product_obj.stoct,
                        })

                
                order.payment_status = 'Paid'
                order.status = 'Confirmed'
                order.razorpay_payment_id = razorpay_payment_id

                order.save(update_fields=[
                    'payment_status',
                    'status',
                    'razorpay_payment_id'
                ])

                
                cart = Cart.objects.filter(
                    user=request.user
                ).first()

                if cart:
                    cartItem.objects.filter(cart=cart).delete()

        
        if request.user.email:
            send_order_confirmation_email.delay(
                request.user.username,
                request.user.email,
                order.id,
                str(order.total_amount),
                order.status
            )

        
        if low_stock_products:
            stock_message = '\n\n'.join(
                (
                    f"Product: {item['name']}\n"
                    f"SKU: {item['sku']}\n"
                    f"Remaining Stock: {item['stock']}"
                )
                for item in low_stock_products
            )

            send_mail(
                subject='Low Stock Alert - Mini E-commerce',
                message=(
                    'The following products have low stock:\n\n'
                    f'{stock_message}\n\n'
                    'Please restock these products.'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.DEFAULT_FROM_EMAIL],
                fail_silently=True,
            )

        return render(
            request,
            'cart/order_success.html',
            {'order': order}
        )

    except razorpay.errors.SignatureVerificationError:
        return HttpResponse(
            "Payment verification failed.",
            status=400
        )

    except ValueError as error:
        return HttpResponse(str(error), status=400)


@login_required
def cancel_order(request, order_id):
    if request.method != 'POST':
        return redirect('order_history')

    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user
    )

    if order.payment_status == 'Paid':
        return HttpResponse(
            "Paid orders cannot be cancelled here.",
            status=400
        )

    if order.status == 'Cancelled':
        return redirect('order_history')

    order.status = 'Cancelled'
    order.save(update_fields=['status'])

    return redirect('order_history')


@csrf_exempt
def razorpay_webhook(request):
    print("RAZORPAY WEBHOOK HIT")
    if request.method != "POST":
        return HttpResponse(status=405)

    webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET

    if not webhook_secret:
        return HttpResponse("Webhook secret is not configured", status=500)

    body = request.body
    signature = request.headers.get("X-Razorpay-Signature", "")

    expected_signature = hmac.new(
        webhook_secret.encode("utf-8"),
        body,
        hashlib.sha256
    ).hexdigest()

    print("WEBHOOK SECRET CONFIGURED:", bool(webhook_secret))
    print("SIGNATURE HEADER PRESENT:", bool(signature))

    if not hmac.compare_digest(expected_signature, signature):
        return HttpResponse("Invalid signature", status=400)

    try:
        payload = json.loads(body)
        event_type = payload.get("event", "")
        event_id = request.headers.get("X-Razorpay-Event-Id")

        if not event_id:
            return HttpResponse("Missing event ID", status=400)

        event, created = RazorpayWebhookEvent.objects.get_or_create(
            event_id=event_id,
            defaults={
                "event_type": event_type,
                "processed": False,
            },
        )

        
        if not created and event.processed:
            return HttpResponse("Already processed", status=200)

        if event_type == "payment.failed":
            payment = (
                payload.get("payload", {})
                .get("payment", {})
                .get("entity", {})
            )
            razorpay_order_id = payment.get("order_id")

            if razorpay_order_id:
                order = Order.objects.filter(
                    razorpay_order_id=razorpay_order_id
                ).first()

                if order and order.payment_status != "Paid":
                    order.payment_status = "Failed"
                    order.save(update_fields=["payment_status"])


        event.processed = True
        event.save(update_fields=["processed"])

        return HttpResponse("Webhook processed", status=200)

    except (ValueError, TypeError, KeyError):
        return HttpResponse("Invalid webhook payload", status=400)
    except Exception:
        return HttpResponse("Webhook processing failed", status=500)

@login_required
def payment_failed(request):
    if request.method != 'POST':
        return redirect('cart')

    razorpay_order_id = request.POST.get(
        'razorpay_order_id', ''
    )

    order = get_object_or_404(
        Order,
        razorpay_order_id=razorpay_order_id,
        user=request.user
    )

    if order.payment_status != 'Paid':
        order.payment_status = 'Failed'
        order.save(update_fields=['payment_status'])

    return render(
        request,
        'cart/payment_failed.html',
        {'order': order}
    )


from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum


@staff_member_required(login_url='/login/')
def sales_dashboard_page(request):
    total_orders = Order.objects.count()

    total_sales = (
        Order.objects.filter(payment_status='Paid')
        .aggregate(total=Sum('total_amount'))['total'] or 0
    )

    pending_orders = Order.objects.filter(status='Pending').count()
    paid_orders = Order.objects.filter(payment_status='Paid').count()

    recent_orders = Order.objects.order_by('-created_at')[:10]

    context = {
        'total_orders': total_orders,
        'total_sales': total_sales,
        'pending_orders': pending_orders,
        'paid_orders': paid_orders,
        'recent_orders': recent_orders,
    }

    return render(request, 'cart/sales_dashboard.html', context)

from django.http import JsonResponse
from django.views.decorators.http import require_GET
@require_GET
def delivery_status_api(request, order_id):
    try:
        order = Order.objects.get(id=order_id)

    except Order.DoesNotExist:
        return JsonResponse(
            {
                "success": False,
                "message": "Order not found"
            },
            status=404
        )

    return JsonResponse({
        "success": True,
        "order_id": order.id,
        "shipping_status": order.shipping_status,
        "delivery_address": order.delivery_address,
        "message": "Delivery status fetched successfully"
    })