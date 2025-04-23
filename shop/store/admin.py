from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(Product)
admin.site.register(Customer)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(ShippingAddress)
admin.site.register(Cart)
admin.site.register(Category)
admin.site.register(Brand)
admin.site.register(NewsletterSubscription)


@admin.register(ChangeHistory)
class ChangeHistoryAdmin(admin.ModelAdmin):
    list_display = ('model_name', 'object_id', 'action', 'user', 'created_at')
    list_filter = ('action', 'model_name', 'created_at')
    search_fields = ('model_name', 'object_id', 'user__email')

@admin.register(UTMTracking)
class UTMTrackingAdmin(admin.ModelAdmin):
    list_display = ('user', 'utm_source', 'utm_medium', 'utm_campaign', 'converted', 'timestamp', 'last_activity')
    list_filter = ('utm_source', 'utm_medium', 'converted', 'timestamp')
    search_fields = ('utm_campaign', 'user__email', 'session_key')
    readonly_fields = ('timestamp', 'last_activity')
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request):
        return False  # Prevent manual addition of UTM records
