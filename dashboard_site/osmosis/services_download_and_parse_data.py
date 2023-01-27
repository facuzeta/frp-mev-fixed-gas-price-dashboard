import requests
import tqdm
import time
import hashlib
import base64
import json
import os
import re
from collections import defaultdict
from django.conf import settings 
from django.db import transaction
from osmosis.models import Block, TxSwap, SwapMsg, DAI_CODE, DIC_STABLE_COINS_DECIMALS_PLACES, DIC_STABLE_COINS_NICE_NAME


# this call the downloader and populate the data into django db
@transaction.atomic
def get_data_and_populate(height):
    if Block.objects.filter(height=height)[:1].exists():
        print("Block already computed, delete if you want to compute again")
        return {'msg': 'Block already computed, delete if you want to compute again', 'status':'ok'}

    # download the data and create local block
    local_block, msg = get_local_block(height)
    if local_block is None:
        print("Block not found")
        return {'error': 'Block not found', 'status':'failed', "msg":msg}

    block_params = {}
    block_params['height'] = height
    block_params['timestamp'] = local_block.timestamp
    block_params['number_of_txs'] = local_block.n_txs
    block_params['number_of_txs_with_swaps'] = sum([tx.are_swaps for tx in local_block.txs])
    block_params['number_of_arbs'] = sum([any(tx.are_arb) for tx in local_block.txs])
    block_params['number_of_arb_successful'] = sum([any(tx.are_arb) for tx in local_block.txs if tx.success])

    # create block obj
    new_block = Block.objects.create(**block_params)

    dic_all_profits = defaultdict(lambda : 0)
    gas_wanted_total = 0
    gas_wanted_arb = 0
    gas_wanted_arb_successful = 0

    # create txs objs
    for i, tx in enumerate(local_block.txs):
        if not tx.are_swaps:
            continue

        tx_swap_params = {}
        tx_swap_params['hash'] = tx.hash
        tx_swap_params['block'] = new_block
        tx_swap_params['order'] = i
        tx_swap_params['success'] = tx.success
        tx_swap_params['fee_denom'] = tx.fee['denom']
        tx_swap_params['fee_amount'] = int(tx.fee['amount'])
        tx_swap_params['gas_wanted'] = tx.gas_wanted
        tx_swap_params['gas_used'] = tx.gas_used

        # store the gas wanted
        gas_wanted_total += tx.gas_wanted
        if any(tx.are_arb):
            gas_wanted_arb += tx.gas_wanted
            if tx.success:
                gas_wanted_arb_successful += tx.gas_wanted

        tx_swap = TxSwap.objects.create(**tx_swap_params)

        for j, _ in enumerate(tx.are_arb):

            swap_msgs_params = {}
            swap_msgs_params['tx'] = tx_swap
            swap_msgs_params['order'] = j
            swap_msgs_params['arb'] = tx.are_arb[j]
            swap_msgs_params['routes'] = tx.parsed_tx[j]
            swap_msgs_params['sender'] = tx.senders

            if tx_swap.success:
                swap_msgs_params['routes_result'] = tx.routes_result[j]
                swap_msgs_params['profit_amount'] = tx.profits[j]['amount']
                swap_msgs_params['profit_denom'] = tx.profits[j]['denom']

                # sum the profit for the block summary 
                dic_all_profits[tx.profits[j]['denom']] += tx.profits[j]['amount']

            SwapMsg.objects.create(**swap_msgs_params)

    # update the block profit summary
    dic_all_profits = dict(dic_all_profits)
    # remove the 0 values
    keys_to_delete = []
    for k,v in dic_all_profits.items():
        if v == 0:
            keys_to_delete.append(k)
    for k in keys_to_delete:
        del dic_all_profits[k]
        
    new_block.profit = dic_all_profits
    new_block.gas_wanted_total = gas_wanted_total
    new_block.gas_wanted_arb = gas_wanted_arb
    new_block.gas_wanted_arb_successful = gas_wanted_arb_successful
    new_block.save()

    return {'msg': '', 'status':'ok'}


####### Download data from rpc and lcd



def only_letters(s):
    if 'ibc/' in s:
        return 'ibc/'+s.split('/')[1]
    return re.sub(r'[^a-zA-Z]', '', s)

def only_numbers(s):
    if 'ibc/' in s:
        return int(s.split('ibc/')[0])
    return int(re.sub(r'[^0-9]', '', s))


def token_are_the_same_or_equivalent(token1, token2):
    if token1 == token2:
        return True
    if token1.lower() in DIC_STABLE_COINS_DECIMALS_PLACES and token2.lower() in DIC_STABLE_COINS_DECIMALS_PLACES:
        return True
    return False


class LocalTx():
    def __init__(self, tx_lcd, tx_rpc):
        self.tx_rpc = tx_rpc
        self.tx_lcd = tx_lcd
        # asumo que si hay swaps son todos swaps
        self.are_swaps = False
        self.are_arb = []
        self.profits = []
        self.routes_result = [] 

        self.compute_hash()
        self.parse_tx_lcd()
        self.check_success()
        self.get_gas()
        if len(self.parsed_tx) >0:
            self.tx_fail_but_chekc_if_it_would_be_arb()

            if self.success:
                self.parse_tx_rpc_logs()
                self.get_routes_results()
                self.compute_profit()

    def __str__(self):
        return self.hash
    def __repr__(self):
        return self.hash

    def tx_fail_but_chekc_if_it_would_be_arb(self):
        res = []
        for m in self.parsed_tx:
            if not ('routes' in m and 'token_in' in m and len(m['routes'])>0):
                res.append(False)
                continue

            if 'token_in' in m:
                if token_are_the_same_or_equivalent(m['token_in']['denom'], m['routes'][-1]['token_out_denom']):
                    res.append(True)
                    continue
            if 'token_out' in m:
                # https://www.mintscan.io/osmosis/txs/1cb08d7e3014db1a95208dd843af7029fe001d2612c83bc73754e8605b1d16f3
                if token_are_the_same_or_equivalent(m['token_out']['denom'], m['routes'][0]['token_in_denom']):
                    res.append(True)
                    continue
            res.append(False)
        self.are_arb = res


    def compute_hash(self):
        decoded = base64.decodebytes(self.tx_lcd.encode('utf-8'))
        self.hash = hashlib.sha256(decoded).hexdigest()

    def parse_tx_lcd(self):
        parsed = json.loads(os.popen(settings.OSMOSIS_DECODER_BIN_FN+' '+self.tx_lcd).read().strip())
        self.parsed_tx = parsed['Msgs']
        self.fee = parsed['Fee']
        self.senders = [l['sender'] for l in self.parsed_tx]
        self.are_swaps = len(self.parsed_tx) > 0



    def check_success(self):

        if 'failed to execute message;' in self.tx_rpc['log']:
            self.success = False
        elif 'account sequence mismatch' in self.tx_rpc['log']:
            self.success = False
        else:
            try:
                # creo q si puedo parsearlo como un json significa q esta success
                json.loads(self.tx_rpc['log'])
                self.success = True
            except:
                self.success = False



    def parse_tx_rpc_logs(self):
        # requiere success
        self.rpc_logs = [log['events'] for log in json.loads(self.tx_rpc['log'])]


    def get_routes_results(self):
        self.routes_result = []
        for log in self.rpc_logs:
            token_swapped_query = [l for l in log if l['type'] == 'token_swapped']
            if len(token_swapped_query)==0:
                routes_result = []
            else:
                token_swapped = token_swapped_query[0]['attributes']
                routes_result = []
                for pool_id, t_in, t_out in zip(
                    [l['value'] for l in token_swapped  if l['key']=='pool_id'],
                    [l['value'] for l in token_swapped  if l['key']=='tokens_in'],
                    [l['value'] for l in token_swapped if l['key']=='tokens_out']):
                    routes_result.append({
                        'pool_id': pool_id,
                        'token_in_amount': only_numbers(t_in),
                        'token_in_denom': only_letters(t_in),
                        'token_out_amount': only_numbers(t_out),
                        'token_out_denom': only_letters(t_out),
                    })
            self.routes_result.append(routes_result)

    def get_gas(self):
        self.gas_wanted = int(self.tx_rpc['gas_wanted'])
        self.gas_used = int(self.tx_rpc['gas_used'])
 
    def compute_profit(self):
        # requiere q sea arb

        def normalize_value_amount(value, denom):
            if denom.lower() in DIC_STABLE_COINS_DECIMALS_PLACES:
                decimals_places = DIC_STABLE_COINS_DECIMALS_PLACES[denom.lower()]
                # el unico casi confictivo es DAI que se representa con 18 numeros
                # si viene dai entonces divido por 10**12 asi queda en la misma base que todo lo demas
                if decimals_places != 6:
                    return value/10**(decimals_places-6)
            return value
            
        def normalize_denom_to_stable_coin(denom):
            if denom.lower() in DIC_STABLE_COINS_DECIMALS_PLACES:
                return 'usd'
            return denom

        self.profits = [ 
            {"amount": normalize_value_amount(rr[-1]['token_out_amount'], rr[-1]['token_out_denom']) - normalize_value_amount(rr[0]['token_in_amount'], rr[0]['token_in_denom']),
            "denom": normalize_denom_to_stable_coin(rr[-1]['token_out_denom'])}
            if self.are_arb[i]
            else {"amount":0, "denom":""}
            for i, rr in enumerate(self.routes_result)]
        

    
    def toDict(self):
        data ={ 
            'hash': self.hash,
            'success': self.success,
            'gas_wanted': self.gas_wanted,
            'senders': self.senders,
            'arbs': self.are_arb,
        }
        if self.success:
            data['routes_result'] = self.routes_result
            data['profits'] = self.profits
        return data



class LocalBlock():
    def __init__(self, txs, timestamp):
        self.txs = txs
        self.timestamp = timestamp
        self.gas_wanted = sum([tx.gas_wanted for tx in self.txs])
        self.n_txs = len(txs)


        self.n_txs_with_arbs = sum([any(tx.are_arb) for tx in txs])
        self.n_success_txs_with_arbs = sum([any(tx.are_arb) and tx.success for tx in txs])
        self.n_fail_txs_with_arbs = sum([any(tx.are_arb) and not tx.success for tx in txs])
        self.gas_wanted_fail_arb_txs = sum([tx.gas_wanted for tx in txs if any(tx.are_arb) and not tx.success])
        self.profits = [p for tx in txs if len(tx.profits)>0 for p in tx.profits if 'denom' in p and p['denom']!='']

# download the data and create localStructu to populate the db
def get_local_block(height):
    headers = {'x-allthatnode-api-key': settings.ALLTHATNODE_APIKEY}

    # get data from lcd:
    # 1. hash
    # 2. parse tx
    try:
        data_lcd = requests.get(f'{settings.OSMOSIS_LCD_URL}/cosmos/base/tendermint/v1beta1/blocks/{height}', headers=headers).json()
    except:
        return None, "Error getting data from lcd"

    if 'block' not in data_lcd or 'data' not in data_lcd['block'] or 'txs' not in data_lcd['block']['data']:
        return None, data_lcd
    txs_lcd = data_lcd['block']['data']['txs']

    # get data from rpc:
    # work or not
    try:
        data_rpc = requests.get(f'{settings.OSMOSIS_RPC_URL}/block_results?height={height}', headers=headers).json()
    except:
        return None, "Error getting data from rpc"
    txs_rpc = data_rpc['result']['txs_results']
    # si esta vacio
    if txs_rpc is None:
        txs_rpc = []

    txs = [LocalTx(tx_lcd, tx_rpc) for tx_lcd, tx_rpc in zip(txs_lcd, txs_rpc)]
    return LocalBlock(txs, data_lcd['block']['header']['time']), ""



def get_last_height_on_chain():
    headers = {'x-allthatnode-api-key': settings.ALLTHATNODE_APIKEY}
    data = requests.get(f'{settings.OSMOSIS_LCD_URL}/blocks/latest', headers=headers).json()
    return data['block']['header']