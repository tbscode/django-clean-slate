from . import api
from django.urls import path

VERSION = 1

urlpatterns = [
    path(f"api/v{VERSION}/user_data/", api.user_app_data),
    path(f"api/v{VERSION}/register/", api.register),
]
