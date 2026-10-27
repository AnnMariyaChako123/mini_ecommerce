from django.contrib import admin
from .models import product, category, brand, Wishlist, Review


class StockStatusFilter(admin.SimpleListFilter):
    title = 'Stock Status'
    parameter_name = 'stock_status'

    def lookups(self, request, model_admin):
        return [
            ('out', 'Out of Stock'),
            ('low', 'Low Stock'),
            ('in', 'In Stock'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'out':
            return queryset.filter(stoct=0)
        elif self.value() == 'low':
            return queryset.filter(stoct__gt=0, stoct__lte=5)
        elif self.value() == 'in':
            return queryset.filter(stoct__gt=5)

        return queryset


@admin.register(product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'sku',
        'category',
        'brand',
        'stoct',
        'stock_status',
    )

    list_filter = ('category', 'brand', StockStatusFilter)
    search_fields = ('name', 'sku')
    list_editable = ('stoct',)
    ordering = ('stoct',)

    @admin.display(description='Stock Status')
    def stock_status(self, obj):
        if obj.stoct == 0:
            return 'Out of Stock'
        elif obj.stoct <= 5:
            return 'Low Stock'
        return 'In Stock'


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created_at')
    search_fields = ('user__username', 'product__name')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('user__username', 'product__name', 'comment')


admin.site.register(category)
admin.site.register(brand)
