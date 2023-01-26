from django.contrib import admin
from django.urls import path, include
import terra_classic.views
urlpatterns = [
    path('admin/', admin.site.urls),
    path('terra-classic/', include('terra_classic.urls')),
    # path('osmosis/', include('osmosis.urls')),
    path('', terra_classic.views.home),  
]
