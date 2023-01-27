from django.contrib import admin
from django.urls import path, include
import osmosis.views


urlpatterns = [
    path('status', osmosis.views.status),
    path('tx/<slug:tx_hash>', osmosis.views.tx),
    path('block/<int:height>', osmosis.views.block),
    path('last_block_available', osmosis.views.last_block_available),
    path('', osmosis.views.home)
]