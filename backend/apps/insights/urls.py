from django.urls import path

from .views import RiskListView, RiskSettingsView

urlpatterns = [
    path("risks/", RiskListView.as_view(), name="risks"),
    path("settings/", RiskSettingsView.as_view(), name="risk-settings"),
]
