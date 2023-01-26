from django.contrib import admin
from django.apps import apps
from terra_classic.models import *



@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    list_display = ('height', 'timestamp',
                    'number_of_txs', 'number_of_txs_with_execute_contract_msg', 'number_of_txs_with_succeded_arbs')


@admin.register(TxContractExecution)
class TxContractExecutionAdmin(admin.ModelAdmin):
    list_display = ('block', 'order',
                    'success', 'sender', 'contract', 'execute_msg')


@admin.register(Arb)
class ArbAdmin(admin.ModelAdmin):
    list_display = ('id', 'profit', 'profit_rate', 'token_in', 'amount_in', 'path')


@admin.register(TokenName)
class TokenNameAdmin(admin.ModelAdmin):
    list_display = ('address', 'name')


for model in apps.get_app_config('terra_classic').models.values():
    try:
        admin.site.register(model)
    except:
        pass