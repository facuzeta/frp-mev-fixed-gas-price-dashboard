from django.db import models
from django.utils import timezone

DAI_CODE = 'ibc/0CD3A0285E1341859B5E86B6AB7682F023D03E97607CCC1DC95706411D866DF7'.lower()
DIC_STABLE_COINS_DECIMALS_PLACES = {
    'axldai': 18,
    'ibc/0cd3a0285e1341859b5e86b6ab7682f023d03e97607ccc1dc95706411d866df7':18,
    'axlusdt': 6,
    'ibc/8242ad24008032e457d2e12d46588fd39fb54fb29680c6c7663d296b383c37c4':6,
    'axlusdc':6,
    'ibc/d189335c6e4a68b513c10ab227bf1c1d38c746766278ba3eeb4fb14124f1d858':6,
    'uusdc':6,
    'ibc/9f9b07ef9ad291167cf5700628145de1deb777c2cfc7907553b24446515f6d0e':6
} 

DIC_STABLE_COINS_NICE_NAME = {
    'axldai': 'DAI',
    'ibc/0cd3a0285e1341859b5e86b6ab7682f023d03e97607ccc1dc95706411d866df7':'DAI',
    'axlusdt': "Tether USD",
    'ibc/8242ad24008032e457d2e12d46588fd39fb54fb29680c6c7663d296b383c37c4':"Tether USD",
    'axlusdc': "USDC",
    'ibc/d189335c6e4a68b513c10ab227bf1c1d38c746766278ba3eeb4fb14124f1d858':"USDC",
    'uusdc':"USDC",
    'ibc/9f9b07ef9ad291167cf5700628145de1deb777c2cfc7907553b24446515f6d0e':"USDC"
} 

def clean(s):
    return s[:8]+'...'+s[-8:]

class Block(models.Model):
    height = models.IntegerField(primary_key=True)
    timestamp = models.DateTimeField()

    # desnormalize this for performance (it could be computedu sing Tx and arb)
    number_of_txs = models.IntegerField()
    number_of_txs_with_swaps = models.IntegerField()
    number_of_arbs = models.IntegerField()
    number_of_arb_successful = models.IntegerField(default=0)

    profit = models.JSONField(default=dict)

    gas_wanted_total = models.IntegerField(default=0)
    gas_wanted_arb = models.IntegerField(default=0)
    gas_wanted_arb_successful = models.IntegerField(default=0)
    
    def long_ago(self):
        return str(timezone.now()-self.timestamp).split('.')[0]
        get_profimit_denom_normalized
    def get_profit(self):
        r = dict(self.profit)
        change_token = 'usd uosmo uatom'.split()
        change_token_label = {'usd': 'USD', 'uosmo':'OSMO', 'uatom':'ATOM'}
        for token in change_token:
            if token in r:
                r[change_token_label[token]] = r[token]/10**6
                del r[token]
        return r

    # class Meta:
    #     indexes = [
    #         models.Index(fields=['height']),
    #         models.Index(fields=['timestamp']),
    #     ]

# only store swaps
class TxSwap(models.Model):
    hash = models.TextField(max_length=64)
    block = models.ForeignKey(Block, on_delete=models.CASCADE)
    order = models.IntegerField()
    success = models.BooleanField(null=True, blank=True)

    fee_amount = models.BigIntegerField()
    fee_denom = models.TextField()


    gas_wanted = models.BigIntegerField()
    gas_used = models.BigIntegerField()

    def clean_hash(self):
        return clean(self.hash)

    def is_arb(self):
        return any(list(self.swapmsg_set.all().values_list('arb',flat=True)))

    def number_of_msg(self):
        return self.swapmsg_set.count()

    class Meta:
        # I use this and no only hash because in Terra I found many txs minned in different blocks
        # I would like to check if it is happening here too 
        unique_together = ('hash', 'block')


class SwapMsg(models.Model):
    tx = models.ForeignKey(TxSwap, on_delete=models.CASCADE)
    order = models.IntegerField()
    arb = models.BooleanField(default=False)
    sender = models.TextField()


    # this exists indepedently of the success of the tx
    routes = models.JSONField(null=True, blank=True)

    # this exists only if the tx was successful
    routes_result = models.JSONField(null=True, blank=True)

    # if it is an arb, I may have profit
    profit_amount = models.BigIntegerField(null=True, blank=True)
    profit_denom = models.TextField(null=True, blank=True)

    # normalizo, osea le saco los decimales places (10**18 dai, 10**6 para todos los demas)
    def  get_profit_amount_normalized(self):
        if self.profit_denom.lower() in DIC_STABLE_COINS_DECIMALS_PLACES:
            return self.profit_amount / 10**DIC_STABLE_COINS_DECIMALS_PLACES[self.profit_denom.lower()]
        else:
            return self.profit_amount/10**6
            
    def get_profimit_denom_normalized(self):
        dic_norm = {'uosmo': 'OSMO', 'utom':'ATOM', 'usd':'USD'}
        dic_norm.update(dict(DIC_STABLE_COINS_NICE_NAME))
        k = self.profit_denom.lower()
        if k in dic_norm:
            return dic_norm[k]
        return k

    def clean_sender(self):
        return clean(self.sender[2:-2])



class TokenName(models.Model):
    address = models.TextField(max_length=64, primary_key=True)
    name = models.TextField()

    @classmethod
    def get_name(cls, address):
        address = address.replace('cw20:', '')
        try:
            return cls.objects.get(address=address.lower()).name
        except:
            return address


    # ../tools/osmosis/tokens_aliases/assets_osmosis.json
