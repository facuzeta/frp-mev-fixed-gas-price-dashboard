from django.conf import settings
import requests
import json
import base64
import hashlib

from terra_classic.models import Tx, Block
from terra_proto.cosmos.tx.v1beta1 import Tx as Tx_pb


def decoded_base64_tx(encoded_tx):
    tx = Tx_pb().parse(base64.decodebytes(encoded_tx.encode('utf-8')))
    r = {}
    r['memo'] = tx.body.memo
    r['fee_token'] = tx.auth_info.fee.amount[0].denom
    r['fee_amount'] = tx.auth_info.fee.amount[0].amount



def create_tx_hash(encoded_tx):
    decoded = base64.decodebytes(encoded_tx.encode('utf-8'))
    return hashlib.sha256(decoded).hexdigest()


def get_block_data(block_height, blockchain='columbus-5'):
    block, _ = Block.objects.get_or_create(blockchain=blockchain, height=block_height)

    txs_with_logs = get_block_data_results(block_height)
    txs_with_encoded = get_block_data_encoded(block_height)

    for encoded_tx, log in zip(txs_with_encoded, txs_with_logs):
        tx_hash = create_tx_hash(encoded_tx)
        Tx.objects.create(
            hash=tx_hash,
            block=block,
            encoded64=encoded_tx,
            
        )


# this entry gets the logs of the transaction
def get_block_data_results(block_height):
    url = settings.URL_RPC+f'/block_results?height={block_height}'
    res = requests.get(url)
    return res.json()['result']['txs_results']


# this entry gets the encoded data
def get_block_data_encoded(block_height):
    url = settings.URL_RPC+f'/block?height={block_height}'
    res = requests.get(url)
    return res.json()['result']['block']['data']['txs']


def get_tx_data_from_hash(tx_hash):
    url = settings.URL_LCD+f'/cosmos/tx/v1beta1/txs/{tx_hash}'
    res = requests.get(url)
    return res.json()['result']

# Por ahi podemos resolver todo con el lcd que estan mas publicos y luego hacerlo online, cada vez que cae un bloque
# nuevo le pegamos a dame un bloque y listo todos los hash y luego pido cada hash, podria ser
# de esta manera no uso el rpc que es mas privado y no se si se puede usar en produccion


#  esto devuelve info de una txs, incluyendo todo lo que quiero logs, etc
# http://localhost:1317/txs/3A1400150C475C599BFA5FD1CE7D07A5F9432500875D0EE42DFC0056D214EC70
# https://lcd.terra.dev/txs/3A1400150C475C599BFA5FD1CE7D07A5F9432500875D0EE42DFC0056D214EC70
# este tambien
# http://localhost:1317/cosmos/tx/v1beta1/txs/3A1400150C475C599BFA5FD1CE7D07A5F9432500875D0EE42DFC0056D214EC70

#
# devuelve el bloque encodeado
# http://localhost:1317/blocks/9487256

# este tambien
# http://localhost:1317/cosmos/base/tendermint/v1beta1/blocks/9487256
