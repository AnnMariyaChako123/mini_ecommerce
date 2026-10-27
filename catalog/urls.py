from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from .views import product_api
from .views import product_api, single_product_api
from .views import api_test_page

urlpatterns = [
    path("", views.home, name = "home"),
    path('register/', views.register, name='register'),
    path('login/',auth_views.LoginView.as_view(template_name='catalog/login.html'),name='login'),
    path('logout/',auth_views.LogoutView.as_view(),name='logout'),
    path('wishlist/add/<int:product_id>/',views.add_to_wishlist,name='add_to_wishlist'),
    path('wishlist/',views.wishlist,name='wishlist'),
    path('wishlist/remove/<int:item_id>/',views.remove_from_wishlist,name='remove_from_wishlist'),
    path('review/<int:product_id>/',views.add_review,name='add_review'),
    path('api/products/', product_api, name='product_api'),
    path('api/products/<int:pk>/',single_product_api,name='single_product_api'),
]