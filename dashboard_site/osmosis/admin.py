from django.contrib import admin
from django.apps import apps
from osmosis.models import *


@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    list_display = ('height', 'timestamp',
                    'number_of_txs', 'number_of_txs_with_swaps',
                    'number_of_arbs', 'number_of_arb_successful', 'profit',
                    'gas_wanted_total', 'gas_wanted_arb', 'gas_wanted_arb_successful')


@admin.register(TxSwap)
class TxSwapAdmin(admin.ModelAdmin):
    list_display = ('hash', 'block', 'order',
                    'success', 'fee_amount', 'fee_denom',
                    'gas_wanted', 'gas_used')



@admin.register(SwapMsg)
class SwapMsgAdmin(admin.ModelAdmin):
    list_display = ('tx', 'order',
                    'arb', 'sender', 'routes',
                    'routes_result', 'profit_amount','profit_denom')



for model in apps.get_app_config('osmosis').models.values():
    try:
        admin.site.register(model)
    except:
        pass