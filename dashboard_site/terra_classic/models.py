from distutils.util import execute
from django.db import models

def clean(s):
    return s[:8]+'...'+s[-8:]

class Block(models.Model):
    height = models.IntegerField(primary_key=True)
    timestamp = models.DateTimeField()

    # desnormalize this for performance (it could be computedu sing Tx and arb)
    number_of_txs = models.IntegerField()
    number_of_txs_with_execute_contract_msg = models.IntegerField()
    number_of_txs_with_succeded_arbs = models.IntegerField(default=-1)
    
    # class Meta:
    #     unique_together = ('blockchain', 'height')
    class Meta:
        indexes = [
            models.Index(fields=['height']),
            models.Index(fields=['timestamp']),
        ]

class TxContractExecution(models.Model):
    hash = models.TextField(max_length=64, primary_key=True)

    block = models.ForeignKey(Block, on_delete=models.CASCADE)
    order = models.IntegerField()
    success = models.BooleanField()

    fee = models.BigIntegerField()
    fee_token = models.TextField()
    memo = models.TextField(blank=True, null=True)

    sender = models.TextField()
    contract = models.TextField()


    execute_msg = models.TextField()

    gas_wanted = models.BigIntegerField()
    gas_used = models.BigIntegerField()
    timestamp = models.DateTimeField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['hash']),
            models.Index(fields=['sender']),
            models.Index(fields=['contract']),
            models.Index(fields=['block']),
            models.Index(fields=['contract', 'success']),
        ]


    def clean_hash(self):
        return clean(self.hash)

    def clean_sender(self):
        return clean(self.sender)

    def clean_contract(self):
        return clean(self.contract)


class Arb(models.Model):
    tx = models.ForeignKey(TxContractExecution, on_delete=models.CASCADE)
    success = models.BooleanField(default=True)

    profit = models.BigIntegerField()
    profit_rate = models.FloatField()

    amount_in = models.BigIntegerField()
    amount_out = models.BigIntegerField()

    token_in = models.TextField()

    path = models.JSONField()

    timestamp = models.DateTimeField(null=True, blank=True)

    def clean_hash(self):
        return self.tx.hash[:8]+'...'+self.tx.hash[-8:]


    # transaction that origins this arbitrage opportunity
    # TODO: think how to infer this
    # arbitrated_tx = models.ForeignKey(TxContractExecution, on_delete=models.CASCADE, related_name='arbitrated_tx')
    class Meta:
        indexes = [
            models.Index(fields=['token_in']),
            models.Index(fields=['tx']),
            models.Index(fields=['success']),
        ]


class TokenName(models.Model):
    address = models.TextField(max_length=64, primary_key=True)
    name = models.TextField()

    @classmethod
    def get_name(cls, address):
        address = address.replace('cw20:', '')
        try:
            return cls.objects.get(address=address).name
        except:
            return address

    # dic_terra = json.load(open('../tools/terra/tokens_terra.json'))
    # TokenName.objects.bulk_create([TokenName(**{'address':r['token'], 'name':r['symbol']}) for _,r in dic_terra.items()])