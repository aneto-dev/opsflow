from django.contrib import admin
from django.http import HttpResponse, JsonResponse
from django.urls import include, path


def home(request):
    return HttpResponse("OpsFlow is running successfully !")

def healthcheck(request):
    return JsonResponse({"status": "healthy"})


urlpatterns = [
    path("", home),
    path("admin/", admin.site.urls),
    path("workflows/", include("workflows.urls")),
    path("healthcheck/", healthcheck),
]