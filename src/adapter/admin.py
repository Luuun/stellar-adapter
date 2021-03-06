from django.contrib import admin

from stellar_adapter.models import UserAccount, AdminAccount, Asset


class CustomModelAdmin(admin.ModelAdmin):
    def __init__(self, model, admin_site):
        self.list_display = [field.name for field in model._meta.fields]
        super(CustomModelAdmin, self).__init__(model, admin_site)


class UserAccountAdmin(CustomModelAdmin):
    pass


class AdminAccountAdmin(CustomModelAdmin):
    pass


class AssetAdmin(CustomModelAdmin):
    pass

admin.site.register(UserAccount, UserAccountAdmin)
admin.site.register(AdminAccount, AdminAccountAdmin)
admin.site.register(Asset, AssetAdmin)
