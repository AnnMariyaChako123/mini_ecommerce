from django.shortcuts import render
from django.core.paginator import Paginator
from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from .models import Wishlist
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from .models import Review

# Create your views here.
from .models import product,category

def home(request):
    products = product.objects.all()
    search = request.GET.get("search","")
    category_id = request.GET.get("category","")

    if search:
        products = products.filter(name__icontains=search)

    if category_id:
        products = products.filter(category_id=category_id)

    categories = category.objects.all()

        
    paginator = Paginator(products,4)
    page_num = request.GET.get("page")
    page_obj = paginator.get_page(page_num)
        

    return render(request, "catalog/home.html", {
        "products":page_obj,
        "page_obj":page_obj,
        "categories":categories,
        "search":search,
        "selected_category":category_id,
    })

# def register(request):
#     if request.method == 'POST':
#         form = UserCreationForm(request.POST)

#         if form.is_valid():
#             form.save()
#             return redirect('login')
#     else:
#         form = UserCreationForm()

#     return render(
#         request,
#         'catalog/register.html',
#         {'form': form}
#     )



from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.shortcuts import render, redirect

User = get_user_model()


class CustomerRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email already exists."
            )

        return email


def register(request):
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = CustomerRegistrationForm()

    return render(
        request,
        'catalog/register.html',
        {'form': form}
    )

@login_required
def add_to_wishlist(request, product_id):
    item = get_object_or_404(product, id=product_id)

    Wishlist.objects.get_or_create(
        user=request.user,
        product=item
    )

    return redirect('wishlist')


@login_required
def wishlist(request):
    items = Wishlist.objects.filter(
        user=request.user
    ).select_related('product')

    return render(
        request,
        'catalog/wishlist.html',
        {'items': items}
    )

@login_required
def remove_from_wishlist(request, item_id):
    item = get_object_or_404(
        Wishlist,
        id=item_id,
        user=request.user
    )
    if request.method == 'POST':
        item.delete()

    return redirect('wishlist')

@login_required
def add_review(request, product_id):
    item = get_object_or_404(product, id=product_id)

    if request.method == 'POST':
        rating = int(request.POST.get('rating', 0))
        comment = request.POST.get('comment', '').strip()

        if 1 <= rating <= 5 and comment:
            Review.objects.update_or_create(
                user=request.user,
                product=item,
                defaults={
                    'rating': rating,
                    'comment': comment
                }
            )

        return redirect('home')

    return render(
        request,
        'catalog/review.html',
        {'product': item}
    )


from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import product
from .serializers import ProductSerializer


@api_view(['GET'])
def product_api(request):
    products = product.objects.all()
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def single_product_api(request, pk):
    try:
        product_obj = product.objects.get(pk=pk)
        serializer = ProductSerializer(product_obj)
        return Response(serializer.data)
    except product.DoesNotExist:
        return Response(
            {"error": "Product not found"},
            status=404
        )

from django.shortcuts import render

def api_test_page(request):
    return render(request, "catalog/api_test.html")

import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.core.mail import send_mail
from django.utils import timezone
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password

from .models import EmailOTP


User = get_user_model()



def request_otp(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()

        if not email:
            messages.error(request, 'Please enter your email address.')
            return redirect('login')

        if not User.objects.filter(email__iexact=email).exists():
            messages.error(
                request,
                'No account found with this email. Please register first.'
            )
            return redirect('login')

        
        recent_otp = EmailOTP.objects.filter(
            email__iexact=email,
            created_at__gte=timezone.now() - timedelta(seconds=60)
        ).exists()

        if recent_otp:
            messages.error(
                request,
                'Please wait 60 seconds before requesting another OTP.'
            )
            return redirect('login')

        
        otp = f'{secrets.randbelow(1_000_000):06d}'

        
        EmailOTP.objects.filter(
            email__iexact=email,
            is_used=False
        ).update(is_used=True)

        
        EmailOTP.objects.create(
            email=email,
            otp_hash=make_password(otp),
            expires_at=timezone.now() + timedelta(minutes=5)
        )

        
        try:
            send_mail(
                'Your Mini Ecommerce Login OTP',
                f'Your OTP is {otp}. It expires in 5 minutes. '
                'Do not share it with anyone.',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )

        except Exception as e:
            print("OTP EMAIL ERROR:", repr(e))

            EmailOTP.objects.filter(
                email__iexact=email,
                is_used=False
            ).update(is_used=True)

            messages.error(
                request,
                'Unable to send OTP. Please check email settings.'
            )
            return redirect('login')

        # Store email in session after successful sending
        request.session['otp_email'] = email

        messages.success(request, 'OTP sent successfully. Please check your email.')
        return redirect('verify_otp')

    return render(request, 'catalog/login.html')


def verify_otp(request):
    email = request.session.get('otp_email')

    if not email:
        messages.error(request, 'Please request an OTP first.')
        return redirect('login')

    if request.method == 'POST':
        otp = request.POST.get('otp', '').strip()

        record = EmailOTP.objects.filter(
            email__iexact=email,
            is_used=False
        ).order_by('-created_at').first()

        if not record or record.is_expired():
            messages.error(request, 'OTP expired. Please request a new one.')
            request.session.pop('otp_email', None)
            return redirect('login')

        if record.attempts >= 5:
            record.is_used = True
            record.save(update_fields=['is_used'])
            request.session.pop('otp_email', None)
            messages.error(request, 'Too many attempts. Request a new OTP.')
            return redirect('login')

        record.attempts += 1
        record.save(update_fields=['attempts'])

        if not check_password(otp, record.otp_hash):
            messages.error(request, 'Invalid OTP. Please try again.')
            return redirect('verify_otp')

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            record.is_used = True
            record.save(update_fields=['is_used'])
            request.session.pop('otp_email', None)
            messages.error(
                request,
                'Account not found for this email. Please register first.'
            )
            return redirect('login')

        record.is_used = True
        record.save(update_fields=['is_used'])

       
        from django.contrib.auth import logout
        logout(request)

       
        login(request, user)

        request.session.pop('otp_email', None)

        return redirect('home')

    return render(request, 'catalog/verify_otp.html')
