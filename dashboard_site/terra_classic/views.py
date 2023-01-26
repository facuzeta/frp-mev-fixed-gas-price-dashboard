from django.shortcuts import render
from django.http import JsonResponse
from terra_classic.services import analyze_arb_opportunity_from_tx_hash
from django.http import HttpResponseNotFound, HttpResponse
from django.shortcuts import render
from terra_classic.services import *
from django.db.models import Sum, Avg
from dateutil.parser import parse, ParserError
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django.contrib.admin.views.decorators import staff_member_required
from terra_classic.models import *
import logging


logger = logging.getLogger(__name__)
CACHE_MAX_TIME = 60 * 60* 24 * 100 # 100 days


@cache_page(CACHE_MAX_TIME) 
def home(requests, date_start=None, date_end=None):
    ctx = {}
    query_filter_arb = {}
    query_filter_block = {}
    ctx['date_end'] = parse('2022-05-08 00:00+00:00')
    query_filter_arb['tx__block__timestamp__lte'] = ctx['date_end']
    query_filter_block['timestamp__lte'] = ctx['date_end']

    if date_start is not None:
        try:
            ctx['date_start'] = parse(date_start+' 00:00+00:00')
            query_filter_arb['tx__block__timestamp__gte'] = ctx['date_start']
            query_filter_block['timestamp__gte'] = ctx['date_start']
        except ParserError:
            pass

    if date_end is not None:
        try:
            ctx['date_end'] = parse(date_end+' 00:00+00:00')
            query_filter_arb['tx__block__timestamp__lte'] = ctx['date_end']
            query_filter_block['timestamp__lte'] = ctx['date_end']
        except ParserError:
            pass

    logger.debug(f'query_filter_arb={query_filter_arb}')

    arb_query_result = Arb.objects.filter(**query_filter_arb)
    logger.debug('ya filtre arb_query_result')

    arb_query_result_only_ust = arb_query_result.filter(token_in='uusd')
    logger.debug('arb_query_result_only_ust created')

    arb_query_result_only_luna = arb_query_result.filter(token_in='uluna')
    logger.debug('arb_query_result_only_luna created')

    # arb_query_result = arb_query_result[:1000]
    # arb_query_result_only_ust = arb_query_result_only_ust[:1000]
    # arb_query_result_only_luna = arb_query_result_only_luna[:1000]

    # figures home
    ctx['monitor'] = get_monitor_values(query_filter_block, arb_query_result_only_ust, arb_query_result_only_luna)
    logger.debug('monitor created')

    ctx['fig_tx_timeseries'] = get_plot_of_number_of(query_filter_block)
    logger.debug('fig_tx_timeseries created')

    ctx['fig_arb_timesieries'] = get_plot_arb_timeseries(arb_query_result_only_ust, arb_query_result_only_luna)
    logger.debug('fig_arb_timesieries created')

    # distribution of token_in
    ctx['fig_disfig_distribution__token_in_start_arb_html'] = fig_dist__token_in_start_arb_html(arb_query_result)
    logger.debug('fig_disfig_distribution__token_in_start_arb_html created')

    # distribution of tokens in path
    ctx['fig_disfig_distribution__tokens_arb_html'] = fig_dist__tokens_arb_html(arb_query_result)
    logger.debug('fig_disfig_distribution__tokens_arb_html')

    
    # distribution of pools 
    ctx['fig_distribution__pools_html'] = fig_distribution__pools_html(arb_query_result)
    logger.debug('fig_distribution__pools_html')


    # distrubution of amount_in only uusd    
    fig_html_ust, top10_ust = dist__amount_in(arb_query_result_only_ust, 'uusd')
    ctx['fig_distribution__amount_in_html__ust'] = fig_html_ust
    ctx['fig_distribution__amount_in_ust_top10'] = top10_ust
    logger.debug('dist__amount_in ust')

    fig_html_luna, top10_luna = dist__amount_in(arb_query_result_only_luna, 'uluna')
    ctx['fig_distribution__amount_in_html__luna'] = fig_html_luna
    ctx['fig_distribution__amount_in_luna_top10'] = top10_luna
    logger.debug('dist__amount_in luna')


    # longitud de los paths

    # total MEV in uusd y uluna
    ctx['profit__usd__sum'] = get_profit_sum(arb_query_result_only_ust)
    ctx['profit__uluna__sum'] = get_profit_sum(arb_query_result_only_luna)
    logger.debug('get_profit_sum')

    fig_html_ust, top10_ust = dist__profit(arb_query_result_only_ust, 'uusd')
    ctx['fig_distribution__profit_html__ust'] = fig_html_ust
    ctx['fig_distribution__profit_ust_top10'] = top10_ust
    logger.debug('dist__profit ust')

    fig_html_uluna, top10_uluna = dist__profit(arb_query_result_only_luna, 'uluna')
    ctx['fig_distribution__profit_html__luna'] = fig_html_uluna
    ctx['fig_distribution__profit_luna_top10'] = top10_uluna

    logger.debug('get_profit_sum')

    # profit_rate promedio
    # ctx['profit_rate__usd__mean_in_percentage'] = 100 * get_profit_avg(arb_query_result_only_ust)
    # ctx['profit_rate__uluna__mean_in_percentage'] = 100 * get_profit_avg(arb_query_result_only_luna)
    # logger.debug('get_profit_avg')


    return render(requests, 'terra_classic/home.html', ctx)
 
def change_token_name_in_cycle(cycle):
    for i in range(len(cycle)):
        cycle[i]['token_in'] = TokenName.get_name(cycle[i]['token_in'])
        cycle[i]['token_out'] = TokenName.get_name(cycle[i]['token_out'])
    return cycle

def check_path_integrity(path):
    for i, o in zip(path[:-1],path[1:]):
        if i['token_out'] != o['token_in']:
            return False
    return True

def tx(request,tx_hash):
    ctx = {"tx_hash": tx_hash}
    query = Arb.objects.filter(tx_id=tx_hash)
    if query.exists():
        arb = query.first()
        ctx['arb'] = arb
        ctx['cycle'] = change_token_name_in_cycle(json.loads(arb.path.replace('\'', '"').replace('cw20:','')))
        ctx['profit'] = arb.profit/10**6
        ctx['amount_in'] = arb.amount_in/10**6
        return render(request, 'terra_classic/tx.html', ctx)
    else:
        return HttpResponseNotFound("tx not found")         


def pool(request, pool_name):
    ctx = {"pool_name": pool_name}
    return render(request, 'pool.html', ctx)

def token(request, token_name):
    ctx = {"token_name": token_name}
    return render(request, 'token.html', ctx)

@cache_page(CACHE_MAX_TIME) 
def contract(request, contract_address):
    txs = TxContractExecution.objects.filter(contract=contract_address)
    header = "Contract: " + contract_address
    return address(request, txs, header)


@cache_page(CACHE_MAX_TIME) 
def sender(request, sender_address):
    txs = TxContractExecution.objects.filter(sender=sender_address)
    header = "Sender: " + sender_address
    return address(request, txs, header)


def address(request, txs, header):
    MAX_TXS = 1000 
    
    # if there are more thant 10K txs, cut for performance issues
    flag_more_than_limit = False
    if len(txs[:MAX_TXS+1])>MAX_TXS:
        flag_more_than_limit = True
        txs = txs[:MAX_TXS]
    print("flag_more_than_limit", flag_more_than_limit)

    revenue_ust = Arb.objects.filter(tx__in=txs, token_in='uusd')[:MAX_TXS].aggregate(Sum("profit"))["profit__sum"]
    if revenue_ust is None:
        revenue_ust  = 0

    revenue_luna = Arb.objects.filter(tx__in=txs, token_in='uluna')[:MAX_TXS].aggregate(Sum("profit"))["profit__sum"]
    if revenue_luna is None:
        revenue_luna = 0

    ctx = {}
    ctx['flag_more_than_limit'] = flag_more_than_limit
    ctx['limit'] = MAX_TXS
    ctx['txs'] = txs
    ctx['n_success'] = len([True for tx in ctx['txs'] if tx.success == True])
    ctx['revenue_ust'] = revenue_ust
    ctx['revenue_luna'] = revenue_luna

    ctx['revenue_ust'] = ctx['revenue_ust']/10**6
    ctx['revenue_luna'] = ctx['revenue_luna']/10**6
    ctx['header'] = header

    return render(request, 'terra_classic/address.html', ctx)

@staff_member_required
def flush_cache(request):
    cache.clear()
    return HttpResponse("Cache flushed")

def is_arb(requests, txhash):
    res = analyze_arb_opportunity_from_tx_hash(txhash)
    return JsonResponse(res, safe=False, json_dumps_params={'indent': 2})