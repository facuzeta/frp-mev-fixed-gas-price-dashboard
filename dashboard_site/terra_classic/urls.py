from django.contrib import admin
from django.urls import path, include
import terra_classic.views


urlpatterns = [
    path('is_arb/<slug:txhash>', terra_classic.views.is_arb),
    path('flush_cache', terra_classic.views.flush_cache),
    path('tx/<slug:tx_hash>/', terra_classic.views.tx, name='txs'),
    path('token/<slug:token_name>/', terra_classic.views.token, name='token'),
    path('pool/<slug:pool_name>/', terra_classic.views.pool, name='pool'),
    path('sender/<slug:sender_address>/', terra_classic.views.sender, name='sender'),
    path('contract/<slug:contract_address>/', terra_classic.views.contract, name='contract'),
        
    path('<slug:date_start>/<slug:date_end>/', terra_classic.views.home),
    path('', terra_classic.views.home)
]