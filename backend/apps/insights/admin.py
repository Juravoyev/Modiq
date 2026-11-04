from django.contrib import admin

from .models import Dismissal, InsightSettings

admin.site.register(InsightSettings)
admin.site.register(Dismissal)
