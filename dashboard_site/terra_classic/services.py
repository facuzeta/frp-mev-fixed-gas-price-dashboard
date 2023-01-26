from collections import Counter
from typing import List, Dict, Tuple
import pandas as pd
import plotly.express as px
from terra_classic.check_arbs import analyze_arb_opportunity_from_tx_hash
import json
from django.utils.crypto import get_random_string
from django.db.models import Sum, Avg, Count
from tqdm import tqdm
import pandas as pd
from terra_classic.models import Block, TxContractExecution, Arb, TokenName
from django.db.models import Sum, Avg
import plotly.express as px
import datetime
# create the distribution of a list of elements


def get_distribution(a_list):
    cn = Counter(a_list)
    return cn.most_common()


def _iterate_arb_list_project_some_field_and_get_distribution(arbs_list, field_name):
    return get_distribution([e[field_name] for arb in arbs_list for e in arb.path])


# iterate arbs list and get the frequency of each token
def get_token_distribution_used_in_arbitrage_list(arbs_list) -> List[Tuple[str, int]]:
    return _iterate_arb_list_project_some_field_and_get_distribution(arbs_list, "token_in")


# iterate arbs list and get the frequency of each pair
def get_pools_distribution_used_in_arbitrage_list(arbs_list) -> List[Tuple[str, int]]:
    pairs = []
    for arb in arbs_list:
        for r in json.loads(arb.path.replace("'", '"')):
            t1, t2 = sorted([ TokenName.get_name(r["token_in"]), TokenName.get_name(r["token_out"])])
            pairs.append(f"{r['pair']}\n({t1}-{t2})")
    return get_distribution(pairs)


# iterate arbs list and get the frequency of token_in


def token_in_in_arbitrage(arbs_list) -> List[Tuple[str, int]]:
    return {TokenName.get_name(r["token_in"]): r["count"] for r in arbs_list.values("token_in").annotate(count=Count("token_in"))}


# iterate arbs list and get the amount_in value
def list_amount_in_in_arbitrage(arbs_list) -> List[int]:
    return [arb.amount_in for arb in arbs_list]


# iterate arbs list and get the profit value
def list_profit_in_arbitrage(arbs_list) -> List[int]:
    return [arb.profit for arb in arbs_list]


# iterate arbs list and get the profit_rate value
def list_profit_rate_in_arbitrage(arbs_list) -> List[float]:
    return [arb.profit_rate for arb in arbs_list]


# iterate arbs list and get the lenght of the path
def list_path_length_in_arbitrage(arbs_list) -> List[int]:
    return [len(arb.path) for arb in arbs_list]


# iterarate arbs list and get the gas of the tx
def list_gas_used_in_arbitrage(arbs_list) -> List[int]:
    return [arb.tx.gas_used for arb in arbs_list]


def fig_distribution__amount_in(arbs_list, token):
    df = pd.DataFrame(list_amount_in_in_arbitrage(arbs_list), columns=["Amount"])

    # esto ahorra una query a la tabla de Txs
    df["txhash"] = [a.tx_id for a in arbs_list]
    df["Amount"] = (df["Amount"] / 10**6).astype(int)
    fig = px.histogram(df, x="Amount", log_y=True, nbins=200)
    fig = fig.update_layout(
        xaxis_title=f"Amount use to perform arbitrage {token}",
        yaxis_title="Count",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False),
    )
    return fig, df.nlargest(10, "Amount").to_dict("records")


def dist__amount_in(arbs_list, token):
    fig, top10 = fig_distribution__amount_in(arbs_list, token)
    return (
        fig.to_html(
            full_html=False,
            include_plotlyjs="cdn",
            default_width="100%",
        ),
        top10,
    )


def fig_distribution__profit(arb_query, token):
    y = "Profit"
    df = pd.DataFrame([{"txhash": arb.tx_id, y: arb.profit / 10**6} for arb in arb_query])
    fig = px.histogram(df, x=y, log_y=True, nbins=200)
    fig = fig.update_layout(
        xaxis_title=f"Profit in arbs that start with {token}",
        yaxis_title="Count",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False),
    )
    df_ranking = df.nlargest(10, y).copy()

    return fig, df_ranking["Profit txhash".split()].to_dict("records")


def dist__profit(arb_query, token):
    fig, top10 = fig_distribution__profit(arb_query, token)
    return (
        fig.to_html(
            full_html=False,
            include_plotlyjs="cdn",
            default_width="100%",
        ),
        top10,
    )


# Pool distribution
def fig_distribution__pools(arbs_list):

    df = pd.DataFrame(get_pools_distribution_used_in_arbitrage_list(arbs_list)).sort_values(1)
    df["Pair"] = df[0].astype(str)
    df["Total"] = df[1].astype(int)
    df["Pool"] = [e.split("\n")[0] for e in df[0]]
    df["Token 1"], df["Token 2"] = zip(*[e.split("\n")[1][1:-1].split("-") for e in df[0]])
    df = df.sort_values("Total").reset_index()
    fig = px.bar(
        df,
        x="Total",
        y="Pair",
        orientation="h",
        log_x=True,
        hover_data={"Pool": False, "Total": True, "Pair": False, "Token 1": True, "Token 2": True},
        hover_name="Pool",
    )
    fig = fig.update_layout(
        yaxis_title="Pools used to perform arbitrage",
        xaxis_title="Count",
        margin=dict(l=30, r=30, t=30, b=30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False),
    )

    fig = fig.update_yaxes(showticklabels=False)
    return fig


def fig_distribution__pools_html(arbs_list):
    js_callback = """
    var plot_element = document.getElementById("{plot_id}");
    
    plot_element.on('plotly_click', function(data){
        fig_distribution__pools_handler("{plot_id}", data);
    });
    """

    fig = fig_distribution__pools(arbs_list)
    return fig.to_html(full_html=False, include_plotlyjs="cdn", default_width="100%")
    # post_script=js_callback)


# Token distribution


def fig_distribution__token_in_start_arb(arbs_list):

    df = pd.DataFrame(list(token_in_in_arbitrage(arbs_list).items()), columns="token total".split())
    df.token = df.token.apply(TokenName.get_name)
    # df = pd.DataFrame(token_in_in_arbitrage(arbs_list),
    #                   columns='Token Total'.split())
    # df = df .sort_values('Total').reset_index()
    # fig = px.bar(df, x="Total", y='Token',
    #              orientation='h',
    #              log_x=True,
    #              text_auto=True,

    #              #  hover_data={"Pool": False, "Total": True, "Pair": False,
    #              #              "Token 1": True, "Token 2": True},
    #              hover_name='Token',
    #              )
    # fig = fig.update_layout(yaxis_title="Token used to start arbitrage",
    #                         xaxis_title="Count",
    #                         margin=dict(l=30, r=30, t=30, b=30),
    #                         )
    # fig = fig.update_yaxes(showticklabels=False)
    fig = px.treemap(df, path=["token"], values="total", hover_data={}, hover_name="token")
    fig = fig.update_layout(uniformtext=dict(minsize=33, mode="hide"))
    fig = fig.update_layout(
        margin=dict(l=30, r=30, t=30, b=30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False),
    )
    fig.data[0].hovertemplate = "%{label}<br>%{value}"

    return fig


# df = pd.DataFrame([['ETH',50],['UST',30],['LUNA',10]], columns='Token total'.split())


def fig_dist__token_in_start_arb_html(arbs_list):
    js_callback = """
    var plot_element = document.getElementById("{plot_id}");
    
    plot_element.on('plotly_click', function(data){
        fig_disfig_distribution__token_in_start_arb_handler("{plot_id}", data);
    });
    """

    fig = fig_distribution__token_in_start_arb(arbs_list)
    return fig.to_html(
        full_html=False,
        include_plotlyjs="cdn",
        default_width="100%",
)
# post_script=js_callback)


def fig_distribution__tokens_arb(arb_query_result):
    def get_tokens_from_path(path):
        # Ojo, que si guardamos como json tenemos que cambiar esto
        return [e.split("'")[0] for e in path.split("token_in': '")[1:]]

    tokens = [token for arb in arb_query_result for token in get_tokens_from_path(arb.path)]
    cn = Counter(tokens)

    df = pd.DataFrame(list(cn.items()), columns="token total".split())
    df.token = df.token.apply(TokenName.get_name)
    fig = px.treemap(df, path=["token"], values="total", hover_data={}, hover_name="token")
    fig = fig.update_layout(uniformtext=dict(minsize=33, mode="hide"))
    fig = fig.update_layout(margin=dict(l=30, r=30, t=30, b=30))
    fig.data[0].hovertemplate = "%{label}<br>%{value}"
    return fig


def fig_dist__tokens_arb_html(arb_query_result):
    js_callback = """
    var plot_element = document.getElementById("{plot_id}");
    
    plot_element.on('plotly_click', function(data){
        fig_disfig_distribution__tokens_arb_handler("{plot_id}", data);
    });
    """

    fig = fig_distribution__tokens_arb(arb_query_result)
    return fig.to_html(
        full_html=False,
        include_plotlyjs="cdn",
        default_width="100%",
)
# post_script=js_callback )


def get_profit_sum(arbs_list):
    return arbs_list.aggregate(Sum("profit"))["profit__sum"]


def get_profit_avg(arbs_list):
    return arbs_list.aggregate(Avg("profit_rate"))["profit_rate__avg"]


def get_monitor_values(query_filter_block, arb_query_result_only_ust, arb_query_result_only_luna):

    query = Block.objects.filter(**query_filter_block)
    d = query.aggregate(n_txs=Sum("number_of_txs"), n_arb=Sum("number_of_txs_with_succeded_arbs"))

    d["arb_profit_ust"] = arb_query_result_only_ust.aggregate(sum_arb=Sum("profit"))["sum_arb"] / 10**6
    d["arb_profit_luna"] = arb_query_result_only_luna.aggregate(sum_arb=Sum("profit"))["sum_arb"] / 10**6

    return d


def get_plot_arb_timeseries(arb_query_result_only_ust, arb_query_result_only_luna):
    figs = {}

    df_ust = pd.DataFrame(
        [(arb.timestamp.date(), arb.profit / 10**6) for arb in arb_query_result_only_ust],
        columns="Date Profit".split(),
    )
    df_ust = df_ust.groupby("Date", as_index=False).sum()
    df_ust.sort_values("Date", inplace=True)

    figs["arb_profit_intime_ust"] = px.line(df_ust, x="Date", y="Profit", title="Profit UST")
    figs["arb_profit_intime_ust"] = figs["arb_profit_intime_ust"].update_layout(
        xaxis_title="Date",
        yaxis_title="Profit UST",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False),
    )
    figs["arb_profit_intime_ust"] = figs["arb_profit_intime_ust"].to_html(include_plotlyjs=False, full_html=False)

    df_luna = pd.DataFrame(
        [(arb.timestamp.date(), arb.profit / 10**6) for arb in arb_query_result_only_luna],
        columns="Date Profit".split(),
    )
    df_luna = df_luna.groupby("Date", as_index=False).sum()
    df_luna.sort_values("Date", inplace=True)
    figs["arb_profit_intime_luna"] = px.line(df_luna, x="Date", y="Profit", title="Profit LUNA")
    figs["arb_profit_intime_luna"] = figs["arb_profit_intime_luna"].update_layout(
        xaxis_title="Date",
        yaxis_title="Profit LUNA",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False),
    )
    figs["arb_profit_intime_luna"] = figs["arb_profit_intime_luna"].to_html(include_plotlyjs=False, full_html=False)

    return figs




MAX_DATE = datetime.date(2022, 5, 8)


def get_data_frame_of_number_of(query_filter_block):
    data = Block.objects.filter(**query_filter_block).values('timestamp__date')
    data = data.annotate(
        n_txs=Sum('number_of_txs'),
        n_txs_exec=Sum('number_of_txs_with_execute_contract_msg'),
        n_arb=Sum('number_of_txs_with_succeded_arbs'))
    df = pd.DataFrame(data)

    return df[df.timestamp__date < MAX_DATE].sort_values('timestamp__date').reset_index()


def get_plot_of_number_of(query_filter_block):
    df = get_data_frame_of_number_of(query_filter_block)

    conf = [
        # {
        #     'fig_name': 'fig_n_txs',
        #     'column_name': 'n_txs',
        #     'title': 'Number of transactions per day',
        # },
        {
            'fig_name': 'fig_n_txs_exec',
            'column_name': 'n_txs_exec',
            'title': 'Number of transactions with contract execution per day',
        },
        {
            'fig_name': 'fig_n_arbs',
            'column_name': 'n_arb',
            'title': 'Number of success arbitrage transactions per day',
        }
    ]
    df['Date'] = df.timestamp__date
    df.sort_values('Date', inplace=True)
    
    figs = {}
    for r in conf:
        figs[r['fig_name']] = px.line(
            df, x="Date", y=r['column_name'],
            # title=r['title']
            )
        figs[r['fig_name']] = figs[r['fig_name']].update_layout(xaxis_title="Date",
                                                                yaxis_title="number",
                                                                margin=dict(l=10, r=10, t=10, b=10),
                                                                paper_bgcolor='rgba(0,0,0,0)',
                                                                plot_bgcolor='rgba(0,0,0,0)',
                                                                xaxis=dict(showgrid=False),
                                                                yaxis=dict(showgrid=False),
                                                                )
        figs[r['fig_name']] = figs[r['fig_name']].to_html(
            include_plotlyjs=False, full_html=False)

    figs['n_txs'] = df.n_txs.sum()
    figs['n_txs_exec'] = df.n_txs_exec.sum()
    figs['n_arb'] = df.n_arb.sum()
    return figs

