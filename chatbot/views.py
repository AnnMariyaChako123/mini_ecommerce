
import os
import logging
from decimal import Decimal

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from groq import Groq

from catalog.models import product
from .models import ChatMessage


logger = logging.getLogger(__name__)


def get_products():
    """Fetch products from the existing product database."""

    result = []

    for item in product.objects.all()[:100]:
        original_price = Decimal(str(item.price or 0))
        discount_percent = Decimal(str(item.disc_perc or 0))

        discount_price = (
            original_price
            * (Decimal("100") - discount_percent)
            / Decimal("100")
        )

        result.append({
            "name": str(item.name),
            "price": original_price,
            "original_price": original_price,
            "discount_percent": discount_percent,
            "discount_price": discount_price,
        })

    return result


def format_products(products):
    """Format product information for the AI."""

    lines = []

    for item in products:
        original = item["original_price"]
        discount = item["discount_percent"]
        final_price = item["discount_price"]

        if discount > 0:
            lines.append(
                f"- {item['name']}: Original price ₹{original:,.2f}, "
                f"{discount}% discount, Offer price ₹{final_price:,.2f}"
            )
        else:
            lines.append(
                f"- {item['name']}: ₹{original:,.2f}"
            )

    return "\n".join(lines) if lines else "No products are currently listed."


def get_chat_history(request):
    """Retrieve chat history for the current user or guest session."""

    if not request.session.session_key:
        request.session.create()

    session_key = request.session.session_key

    if request.user.is_authenticated:
        return ChatMessage.objects.filter(
            user=request.user
        ).order_by("-created_at")[:50]

    return ChatMessage.objects.filter(
        session_key=session_key,
        user__isnull=True,
    ).order_by("-created_at")[:50]


def chat_page(request):
    """Display the chatbot page with saved messages."""

    history = list(get_chat_history(request))
    history.reverse()

    return render(
        request,
        "chatbot/chat.html",
        {"history": history},
    )


def get_ai_reply(message, request):
    """Generate an AI response using Groq and real product data."""

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise ValueError("GROQ_API_KEY is not configured.")

    client = Groq(api_key=api_key)

    products = get_products()
    product_context = format_products(products[:30])

    messages = [
        {
            "role": "system",
            "content": (
                "You are the friendly AI shopping assistant for "
                "Glow Beauty, an e-commerce website.\n\n"
                "Your responsibilities:\n"
                "1. Answer general questions naturally and helpfully.\n"
                "2. Recommend relevant skincare, haircare and beauty "
                "products when requested.\n"
                "3. Help users compare products and understand prices "
                "and discounts.\n"
                "4. Give clear, concise and friendly responses.\n"
                "5. Use the supplied inventory for product names, "
                "prices and offers. Never invent products or prices.\n"
                "6. If the requested product is not listed, explain "
                "that you could not find it in the current inventory.\n"
                "7. Do not claim to access customer orders, payment "
                "records or private account information unless that "
                "information is explicitly provided.\n"
                "8. For medical or skin concerns, provide general "
                "information and suggest consulting a qualified "
                "professional when appropriate.\n\n"
                f"Current product inventory:\n{product_context}"
            ),
        }
    ]

    
    if not request.session.session_key:
        request.session.create()

    if request.user.is_authenticated:
        previous_messages = ChatMessage.objects.filter(
            user=request.user
        ).order_by("-created_at")[:10]
    else:
        previous_messages = ChatMessage.objects.filter(
            session_key=request.session.session_key,
            user__isnull=True,
        ).order_by("-created_at")[:10]

    for entry in reversed(list(previous_messages)):
        messages.append({
            "role": "user",
            "content": entry.message,
        })
        messages.append({
            "role": "assistant",
            "content": entry.reply,
        })

    messages.append({
        "role": "user",
        "content": message,
    })

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=messages,
        max_tokens=600,
        temperature=0.7,
    )

    answer = response.choices[0].message.content

    if not answer:
        return "Sorry, I could not generate a response. Please try again."

    return answer.strip()


@require_POST
def chat_message(request):
    """Receive a message, call Groq AI and save the conversation."""

    message = request.POST.get("message", "").strip()

    if not message:
        return JsonResponse(
            {"reply": "Please enter a message."},
            status=400,
        )

    if len(message) > 1000:
        return JsonResponse(
            {"reply": "Please keep your message under 1000 characters."},
            status=400,
        )

    try:
        if not request.session.session_key:
            request.session.create()

        reply = get_ai_reply(message, request)

        ChatMessage.objects.create(
            user=(
                request.user
                if request.user.is_authenticated
                else None
            ),
            session_key=request.session.session_key or "",
            message=message,
            reply=reply,
        )

        return JsonResponse({
            "reply": reply,
        })

    except Exception:
        logger.exception("Groq chatbot request failed")

        return JsonResponse(
            {
                "reply": (
                    "Sorry, the AI assistant is temporarily unavailable. "
                    "Please try again in a moment."
                )
            },
            status=500,
        )
