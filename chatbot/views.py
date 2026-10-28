
from decimal import Decimal, InvalidOperation
import re

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from catalog.models import product


def chat_page(request):
    return render(request, "chatbot/chat.html")


def get_products():
    result = []

    for item in product.objects.all()[:100]:
        original_price = Decimal(str(item.price))
        discount_percent = Decimal(str(item.disc_perc or 0))

        discount_price = (
            original_price
            * (Decimal("100") - discount_percent)
            / Decimal("100")
        )

        result.append({
            "name": item.name,
            "price": original_price,
            "original_price": original_price,
            "discount_percent": discount_percent,
            "discount_price": discount_price,
        })

    return result


def format_products(products):
    lines = []

    for item in products:
        original = item["original_price"]
        discount = item["discount_percent"]
        final_price = item["discount_price"]

        if discount > 0:
            lines.append(
                f"- {item['name']}: Original price ₹{original:,.2f}, "
                f"{discount}% off, Offer price ₹{final_price:,.2f}"
            )
        else:
            lines.append(
                f"- {item['name']}: ₹{original:,.2f}"
            )

    return "\n".join(lines)


def get_reply(message):
    text = message.lower().strip()
    products = get_products()

    
    if text in [
        "hi", "hello", "hey", "hai",
        "good morning", "good evening"
    ]:
        return (
            "Hello! Welcome to Glow Beauty! 💗\n\n"
            "I can help you with skincare products, hair care products, "
            "prices, discounts, budgets, orders and payments.\n\n"
            "What are you looking for?"
        )

    
    if "face wash" in text and "sunscreen" in text:
        return (
            "Face Wash vs Sunscreen 🧴\n\n"
            "• Face wash cleans your skin by removing dirt, oil "
            "and impurities.\n\n"
            "• Sunscreen helps protect your skin from UV rays. "
            "Choose a broad-spectrum sunscreen and follow its label.\n\n"
            "They have different purposes, so one does not replace the other."
        )

    
    hair_words = [
        "hair", "haircare", "shampoo", "conditioner",
        "hair oil", "hair serum"
    ]

    skin_words = [
        "skin", "skincare", "face wash", "sunscreen",
        "moisturizer", "moisturiser", "cleanser"
    ]

    wants_hair = any(word in text for word in hair_words)
    wants_skin = any(word in text for word in skin_words)

    # Skincare routine
    routine_words = [
        "routine", "daily skincare", "skin care routine",
        "skincare routine", "daily skin care"
    ]

    if any(word in text for word in routine_words):
        skin_products = [
            item for item in products
            if any(word in item["name"].lower() for word in [
                "face wash", "cleanser", "cream", "moisturizer",
                "moisturiser", "sunscreen", "skin", "skincare"
            ])
        ]

        reply = (
            "A simple skincare routine 💗\n\n"
            "Morning:\n"
            "1. Cleanse your face.\n"
            "2. Apply moisturizer if needed.\n"
            "3. Apply sunscreen.\n\n"
            "Evening:\n"
            "1. Cleanse your face.\n"
            "2. Apply moisturizer if needed.\n\n"
        )

        if skin_products:
            reply += (
                "Available skincare products:\n\n"
                + format_products(skin_products)
            )
        else:
            reply += "No matching skincare products were found."

        return reply

    
    hair_products = [
        item for item in products
        if any(word in item["name"].lower() for word in [
            "hair", "serum", "oil", "shampoo", "conditioner"
        ])
    ]

    skin_products = [
        item for item in products
        if any(word in item["name"].lower() for word in [
            "face wash", "cleanser", "cream", "moisturizer",
            "moisturiser", "sunscreen", "skin", "skincare"
        ])
    ]

    
    if wants_hair and wants_skin:
        return (
            "Welcome to Glow Beauty! 💗\n\n"
            "HAIR CARE PRODUCTS 💇‍♀️\n\n"
            + (
                format_products(hair_products)
                if hair_products
                else "No hair care products found."
            )
            + "\n\nSKINCARE PRODUCTS 🧴\n\n"
            + (
                format_products(skin_products)
                if skin_products
                else "No skincare products found."
            )
        )

    
    if wants_hair:
        if hair_products:
            return (
                "Our Hair Care Products 💇‍♀️\n\n"
                + format_products(hair_products)
            )

        return "Sorry! No hair care products were found."

    
    if wants_skin:
        if skin_products:
            return (
                "Our Skincare Products 🧴\n\n"
                + format_products(skin_products)
            )

        return "Sorry! No skincare products were found."

    
    budget_words = [
        "under", "below", "within", "less than",
        "budget", "cheapest", "affordable"
    ]

    if any(word in text for word in budget_words):
        numbers = re.findall(r"\d[\d,]*(?:\.\d+)?", text)

        if numbers:
            try:
                budget = Decimal(numbers[0].replace(",", ""))

                matches = [
                    item for item in products
                    if item["discount_price"] <= budget
                ]

                matches.sort(
                    key=lambda item: item["discount_price"]
                )

                if matches:
                    return (
                        f"Products within ₹{budget:,.2f} 💰\n\n"
                        + format_products(matches)
                    )

                return (
                    f"Sorry, no products were found within "
                    f"₹{budget:,.2f}."
                )

            except InvalidOperation:
                pass

        return (
            "Please mention your budget, for example: "
            "'Suggest products under ₹500'."
        )

    
    if any(word in text for word in [
        "discount", "discounts", "offer", "offers",
        "sale", "final price", "offer price"
    ]):
        discounted = [
            item for item in products
            if item["discount_percent"] > 0
        ]

        if discounted:
            return (
                "Our discounted products 🎉\n\n"
                + format_products(discounted)
            )

        return "No discounted products were found."

    
    if any(word in text for word in [
        "all products", "show products", "list products",
        "our products", "catalog", "available products"
    ]):
        if products:
            return (
                "Our available Glow Beauty products 💗\n\n"
                + format_products(products)
            )

        return "No products are listed in the store right now."

    
    matched = [
        item for item in products
        if item["name"].lower() in text
    ]

    if matched:
        return (
            "Here are the matching products:\n\n"
            + format_products(matched)
        )

    
    if any(word in text for word in ["price", "prices", "cost"]):
        if products:
            return (
                "Our product prices and offers 💗\n\n"
                + format_products(products)
            )

        return "No product prices are available right now."

    
    if any(word in text for word in [
        "order", "my orders", "order status", "track order"
    ]):
        return (
            "You can check your orders on the My Orders page "
            "after logging in."
        )

    
    if any(word in text for word in [
        "payment", "razorpay", "pay", "payment failed"
    ]):
        return (
            "You can use the payment options shown during checkout. "
            "If a payment fails, check your order and payment status."
        )

    
    if any(word in text for word in [
        "delivery", "shipping", "shipment"
    ]):
        return (
            "Please check your order details for delivery information. "
            "Contact the store for a confirmed delivery date."
        )

    
    if "thank" in text:
        return "You're welcome! Thank you for shopping with Glow Beauty. 💗"

    
    return (
        "Welcome to Glow Beauty! 💗\n\n"
        "I can help you with:\n"
        "• Skincare products\n"
        "• Hair care products\n"
        "• Both categories together\n"
        "• Prices and discounts\n"
        "• Products under a budget\n"
        "• Skincare routines\n"
        "• Orders, payments and delivery\n\n"
        "Try asking: 'Show me hair and skin care products'."
    )


@require_POST
def chat_message(request):
    message = request.POST.get("message", "").strip()

    if not message:
        return JsonResponse(
            {"reply": "Please enter a message."},
            status=400
        )

    if len(message) > 1000:
        return JsonResponse(
            {"reply": "Please keep your message under 1000 characters."},
            status=400
        )

    try:
        reply = get_reply(message)
        return JsonResponse({"reply": reply})

    except Exception as error:
        print("Chatbot Error:", repr(error))
        return JsonResponse(
            {
                "reply": (
                    "Sorry, I couldn't process that message. "
                    "Please try again."
                )
            },
            status=500
        )
