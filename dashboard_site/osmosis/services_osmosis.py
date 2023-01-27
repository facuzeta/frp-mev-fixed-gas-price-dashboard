from django.shortcuts import render
from osmosis.models import *
from django.db.models import Sum, Avg
from collections import defaultdict
import plotly.express as px
import pandas as pd
from django.db.models import IntegerField
from django.db.models.functions import Cast

# suma los profits de misma especie
def sum_profit_query_blocks(blocks):
    dic_all_profits = defaultdict(lambda : 0)
    for b in blocks:
        for k,v in b.profit.items():

            if k.lower() == DAI_CODE:
                v = int(v/10**12)

            if k.lower() in DIC_STABLE_COINS_DECIMALS_PLACES:
                dic_all_profits['ALL-STABLE-COINS-USD'] += v
            elif k.lower() == 'uosmo':
                dic_all_profits['OSMO'] += v
            elif k.lower() == 'uatom' or k.lower() == 'ibc/27394fb092d2eccd56123c74f36e4c1f926001ceada9ca97ea622b25f41e5eb2':
                dic_all_profits['ATOM'] += v
            else:
                dic_all_profits[k.lower()] += v

    dic_all_profits = {k: (v/10**6) for k,v in dict(dic_all_profits).items() if (v/10**6)>0}
    return dic_all_profits


def fig_profit_summary(blocks):
    dic_all_profits = sum_profit_query_blocks(blocks)
    if 'usd' in dic_all_profits:
        dic_all_profits['STABLE-COINS'] = dic_all_profits['usd']
        del dic_all_profits['usd']

    if len(dic_all_profits) == 0: return None,{"OSMO":0}
    
    x, y= list(zip(*dic_all_profits.items()))
    df = pd.DataFrame({'Coin':x, 'Sum':y}).sort_values('Sum', ascending=True)
    # df.Coin = [c[:5]+'...'+c[-5:] if 'ibc/' in c else c  for c in df.Coin.iloc]
    df.Coin = [TokenName.get_name(c)   for c in df.Coin.iloc]
    fig = px.bar(data_frame=df, y='Coin', x='Sum',
        orientation="h",
        color='Coin',
        color_discrete_sequence=px.colors.qualitative.Pastel2,

            # hover_data={"Pool": False, "Total": True, "Pair": False, "Token 1": True, "Token 2": True},
            # hover_name="Pool",
    )
    fig = fig.update_layout(
        yaxis_title="Sum",
        xaxis_title="Coin",
        margin=dict(l=30, r=30, t=30, b=30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False),

    )
    fig = fig.update_layout(yaxis=dict(autorange="reversed"))
    fig = fig.update_yaxes(showticklabels=False)
    if 'OSMO' not in dic_all_profits:
        dic_all_profits['OSMO'] = 0
    return fig.to_html(full_html=False, include_plotlyjs="cdn", default_width="100%"), dic_all_profits


def ranking_15_most_profitable_swap_msgs(blocks):
    return sorted([sm for sm in SwapMsg.objects.filter(tx__block__in=blocks, arb=True, tx__success=True, profit_amount__gt=0)],key=lambda x: -x.get_profit_amount_normalized())[:15]



def get_fig_diary_graph():
    df = pd.DataFrame([e for e in Block.objects.values('timestamp__date').annotate(uosmo=Sum(Cast('profit__uosmo',IntegerField()))) if e['uosmo'] is not None]).sort_values('timestamp__date')
    df.index = pd.Index(df.timestamp__date.apply(pd.to_datetime).values, name='Date')
    df['OSMO'] = df.uosmo/10**6
    df = df.OSMO.resample('d').sum()


    fig = px.line(df, y="OSMO", title="Extracted  MEV per day (only OSMO)", markers=True)
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="UOSMO",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False),
    )

    return fig.to_html(full_html=False, include_plotlyjs="cdn", default_width="100%")