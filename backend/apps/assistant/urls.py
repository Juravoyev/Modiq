from django.urls import path

from .views import AskView, TopicsView

urlpatterns = [
    path("topics/", TopicsView.as_view(), name="assistant-topics"),
    path("ask/", AskView.as_view(), name="assistant-ask"),
]
