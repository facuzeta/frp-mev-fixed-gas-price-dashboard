from django.shortcuts import render
from osmosis.models import *
from django.db.models import Sum, Avg, Count
from osmosis.services_osmosis import *
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
import datetime
from osmosis.services_osmosis_manager import *
from django.http import JsonResponse

BLOCKS_PER_HOUR = 10*60 # 10 per miniute

def home(request):
    ctx = {}
    last_block = Block.objects.all().order_by('-height')[0]
    ctx['last_height'] = last_block.height
    ctx['last_timestamp'] = last_block.timestamp

    summarized_query = {"number_of_txs": Sum("number_of_txs"),
                        "number_of_txs_with_swaps": Sum('number_of_txs_with_swaps'),
                        "number_of_txs_with_swaps_no_arbs": Sum('number_of_txs_with_swaps')-Sum('number_of_arbs'),
                        "number_of_arbs": Sum('number_of_arbs'),
                        "number_of_arb_successful": Sum('number_of_arb_successful'),
                        "number_of_arb_failed": Sum('number_of_arbs')-Sum('number_of_arb_successful'),
                        "gas_wanted_total": Sum('gas_wanted_total'),
                        "gas_wanted_total_swaps_no_arb":  Sum('gas_wanted_total')-Sum('gas_wanted_arb'),
                        "gas_wanted_arb": Sum('gas_wanted_arb'),
                        "gas_wanted_arb_successful": Sum('gas_wanted_arb_successful'),
                        "gas_wanted_arb_failed": Sum('gas_wanted_arb')-Sum('gas_wanted_arb_successful'),
    }
    
    # last hour
    blocks = Block.objects.filter(timestamp__gt=last_block.timestamp-datetime.timedelta(hours=1))
    # blocks = Block.objects.filter(timestamp__gt=timezone.now()-datetime.timedelta(hours=1))
    ctx['last_hour'] = blocks.aggregate(**summarized_query)
    ctx['last_hour']['profits_fig'], ctx['last_hour']['profits_ouosmo'] = fig_profit_summary(blocks)
    ctx['last_hour']['profit_ranking'] = ranking_15_most_profitable_swap_msgs(blocks)

    # last 24 hours
    blocks = Block.objects.filter(timestamp__gt=last_block.timestamp-datetime.timedelta(hours=24))
    # blocks = Block.objects.filter(timestamp__gt=timezone.now()-datetime.timedelta(hours=24))
    ctx['last_day'] = blocks.aggregate(**summarized_query)
    ctx['last_day']['profits_fig'], ctx['last_day']['profits_ouosmo'] = fig_profit_summary(blocks)
    ctx['last_day']['profit_ranking'] = ranking_15_most_profitable_swap_msgs(blocks)

    # last 24 hours
    blocks = Block.objects.filter(timestamp__gt=last_block.timestamp-datetime.timedelta(days=30))
    # blocks = Block.objects.filter(timestamp__gt=timezone.now()-datetime.timedelta(days=30))
    ctx['last_month'] = blocks.aggregate(**summarized_query)
    ctx['last_month']['profits_fig'], ctx['last_month']['profits_ouosmo'] = fig_profit_summary(blocks)
    # ctx['last_month']['profit_ranking'] = ranking_15_most_profitable_swap_msgs(blocks)

    ctx['mev_diary_figure'] = get_fig_diary_graph()

    return render(request, 'osmosis/home_osmosis.html', ctx)



@staff_member_required
def status(request):
    ctx = {}
    ctx['fig_blocks_per_hour'] = fig_blocks_per_hour().to_html(full_html=False, include_plotlyjs="cdn", default_width="100%")
    return render(request, 'osmosis/status.html', ctx)


def last_block_available(request):
    return JsonResponse({"last_height":Block.objects.all().order_by('-height')[0].height}, safe=False)



def tx(request,tx_hash):
    ctx = {}
    ctx['tx'] = TxSwap.objects.get(hash=tx_hash)
    return render(request, 'osmosis/tx.html', ctx)

def block(request, height):
    ctx = {'height':height}
    ctx['block_'] = Block.objects.get(height=height)
    return render(request, 'osmosis/block.html', ctx)
