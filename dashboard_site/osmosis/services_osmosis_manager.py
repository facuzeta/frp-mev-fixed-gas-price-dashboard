from django.db.models.functions import TruncHour
from osmosis.models import *
from django.db.models import Sum, Avg, Count
from osmosis.services_osmosis import *
from django.utils import timezone
import datetime
import pandas as pd
import plotly.express as px


def get_df_blocks_per_hour():
    df = pd.DataFrame(list(Block.objects.annotate(hour=TruncHour('timestamp')).values('hour').annotate(Count('height')))).sort_values('hour')
    df.index = df.hour
    return df.height__count.resample('h').sum()


def fig_blocks_per_hour():
    df = get_df_blocks_per_hour()
    fig = px.line(df, y="height__count", title="Blocks per hour")
    fig.update_layout(
        xaxis_title="Date",
        # yaxis_title="Profit UST",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False),
    )
    return fig
# fig.to_html(include_plotlyjs=False, full_html=False)
