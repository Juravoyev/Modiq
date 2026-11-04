from django.urls import path

from .views import DismissView, InsightSettingsView, RecommendationsView, SummaryView

urlpatterns = [
    path("recommendations/", RecommendationsView.as_view(), name="insights-recommendations"),
    path("recommendations/summary/", SummaryView.as_view(), name="insights-summary"),
    path("recommendations/dismiss/", DismissView.as_view(), name="insights-dismiss"),
    path("settings/", InsightSettingsView.as_view(), name="insights-settings"),
]
