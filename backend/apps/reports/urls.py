from django.urls import path

from .views import DashboardView, DiscountResultsView, ReportView, WeeklySummaryView

urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("discounts/<int:pk>/results/", DiscountResultsView.as_view(), name="discount-results"),
    path("weekly-summary/", WeeklySummaryView.as_view(), name="weekly-summary"),
    path("<slug:name>/", ReportView.as_view(), name="report"),
]
