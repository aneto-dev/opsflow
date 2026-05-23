from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path


def home(request):
    return HttpResponse("OpsFlow is running successfully on Railway 🚀")


urlpatterns = [
    path("", home),
    path("admin/", admin.site.urls),
    path("workflows/", include("workflows.urls")),
]