import requests
import tqdm
import time
import hashlib
import base64
import json
import os
import re
from django.conf import settings 


STABLE_COINS = "axlDAI ibc/0CD3A0285E1341859B5E86B6AB7682F023D03E97607CCC1DC95706411D866DF7 axlUSDT ibc/8242AD24008032E457D2E12D46588FD39FB54FB29680C6C7663D296B383C37C4 axlUSDC ibc/D189335C6E4A68B513C10AB227BF1C1D38C746766278BA3EEB4FB14124F1D858 ibc/D189335C6E4A68B513C10AB227BF1C1D38C746766278BA3EEB4FB14124F1D858 axlusdc uusdc ibc/0CD3A0285E1341859B5E86B6AB7682F023D03E97607CCC1DC95706411D866DF7 ibc/9F9B07EF9AD291167CF5700628145DE1DEB777C2CFC7907553B24446515F6D0E".split()
 

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
    if token1 in STABLE_COINS and token2 in STABLE_COINS:
        return True
    return False


class Tx():
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
        self.success = 'failed to execute message;' not in self.tx_rpc['log']

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
        self.profits = [ {"amount": rr[-1]['token_out_amount'] - rr[0]['token_in_amount'], "denom":rr[-1]['token_out_denom']} if self.are_arb[i] else {"amount":0, "denom":""} for i, rr in enumerate(self.routes_result)]
        

    
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



class Block():
    def __init__(self, txs):
        self.txs = txs
        self.gas_wanted = sum([tx.gas_wanted for tx in self.txs])
        self.n_txs = len(txs)


        self.n_txs_with_arbs = sum([any(tx.are_arb) for tx in txs])
        self.n_success_txs_with_arbs = sum([any(tx.are_arb) and tx.success for tx in txs])
        self.n_fail_txs_with_arbs = sum([any(tx.are_arb) and not tx.success for tx in txs])
        self.gas_wanted_fail_arb_txs = sum([tx.gas_wanted for tx in txs if any(tx.are_arb) and not tx.success])
        self.profits = [p for tx in txs if len(tx.profits)>0 for p in tx.profits if 'denom' in p and p['denom']!='']


def get_block(height):
    # get data from lcd:
    # 1. hash
    # 2. parse tx
    data_lcd = requests.get(f'{settings.OSMOSIS_LCD_URL}/cosmos/base/tendermint/v1beta1/blocks/{height}').json()
    txs_lcd = data_lcd['block']['data']['txs']

    # get data from rpc:
    # work or not
    data_rpc = requests.get(f'{settings.OSMOSIS_RPC_URL}/block_results?height={height}').json()
    txs_rpc = data_rpc['result']['txs_results']

    txs = [Tx(tx_lcd, tx_rpc) for tx_lcd, tx_rpc in zip(txs_lcd, txs_rpc)]
    return Block(txs)
        
# https://www.mintscan.io/osmosis/blocks/6718697
height = 6718697



