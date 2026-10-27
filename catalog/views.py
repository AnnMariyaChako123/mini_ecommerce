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

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = UserCreationForm()

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