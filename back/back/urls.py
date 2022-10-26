from django.contrib import admin
from django.urls import path, include

"""
We are adding all app urls under `'/'` their paths should be set under `<app>/urls.py`
Admin paths registered last
"""

urlpatterns = [
    path('/', include('management.urls')),
    path('admin/', admin.site.urls),
]
