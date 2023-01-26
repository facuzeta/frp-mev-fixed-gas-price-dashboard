import os
import json
import re
import pandas as pd
from tqdm import tqdm
from multiprocessing import Pool
import numpy as np
import re
import requests
from terra_sdk.core.tx import TxInfo

class ErrorLockColatteralFail(Exception):
    pass


class ErrorWithdrawCollateral(Exception):
    pass


class ErrorSwapAdhoc(Exception):
    pass


ANCHOR_ADDRESS = 'terra1sepfj7s0aeg5967uxnfk4thzlerrsktkpelm5s'
AUST_TOKEN_ADDRESS = 'terra1hzh9vpxhsk8253se0vv5jj6etdvxu3nv8z07zu'
ST_LUNA_TOKEN_ADDRESS = 'terra1yg3j2s986nyp5z7r2lvt0hx3r0lnd7kwvwwtsc'
BLUNA_TOKEN_ADDRESS = 'terra1kc87mu460fwkqte29rquh4hc20m54fxwtsx7gp'

EXECUTE_MSG_KEYS_THAT_ARE_NOT_ARBS = 'activate_boost ledger_proxy transmit claim_rewards_and_optionally_unlock deposit_tokens withdraw_voting_tokens record_twap_snapshots allocate_user_rewards transfer_nft cancel_order unlock_collateral approve unbond repay_stable transfer send_nft borrow_stable assert_limit_order send swap feed_price feed_price claim relay deposit_stable execute_strategy zap_into_strategy compound zap_to_bond mint re_invest create_position migrate_position_contracts re_invest zap_into_strategy send compound harvest_all zap_to_bond open_position create_position swap withdraw controller mint convert_and_claim_rewards assert_reaction_z migrate_position_contracts update_position start_swap deposit increase_allowance swap_asset_to_uusd swap_uusd_to_mars field_liquidate attempt_mirror_liq execute_basset_to_nasset_route delta_neutral_invest deposit_stable harvest liquidate_red_bank_user submit_order chad_money execute_loan liquidate liquidate_fields_position run_external claim_rewards set liquidate_dollar rebalance add_liquidity liquidate_luna claim_tokens_from_wormhole_and_delta_neutral_invest mint_from_uusd execute_poll'
EXECUTE_MSG_KEYS_THAT_ARE_NOT_ARBS = [set([e]) for e in list(set(EXECUTE_MSG_KEYS_THAT_ARE_NOT_ARBS.split()))]


def remove_numbers(s):
    return re.sub('[^a-z]+', ' ', s).strip()


def remove_letters(s):
    return int(re.sub('[^0-9]+', '', s))


def clean_token(t):
    return t.replace('native:', '')


def get_sections(logs_wasm, logs_swap_adhoc):

    indexes_start_sections = [i for i, r in enumerate(logs_wasm) if r['key'] == 'contract_address']
    indexes_and_sections = [{r['key']: r['value'] for r in logs_wasm[m:M]} for m, M in zip(indexes_start_sections, indexes_start_sections[1:]+[len(logs_wasm)])]
    df_sections_pre = pd.DataFrame(indexes_and_sections)
    if 'action' not in df_sections_pre.columns:
        return pd.DataFrame()

    sections_clean = []

    indexes_and_sections = list(df_sections_pre.iterrows())
    for index, r in indexes_and_sections:
        if r.action == 'swap':
            sections_clean.append({
                'pair': r.contract_address,
                'token_in': clean_token(r.offer_asset),
                'token_out': clean_token(r.ask_asset),
                'amount_in': int(r.offer_amount),
                'amount_out': int(r.return_amount),
            })
        if r.action == 'withdraw_collateral':
            if not(indexes_and_sections[index+1][1].action == 'transfer'):
                raise ErrorWithdrawCollateral('withdraw_collateral')

            infered_token_out = indexes_and_sections[index +
                                                     1][1].contract_address

            # busco el send anterior (mismo ejemplo lock_collateral)
            infered_token_in = df_sections_pre[:index][df_sections_pre[:index].action ==
                                                       'send'].iloc[-1].contract_address
            sections_clean.append({
                'pair': r.borrower,
                'token_in': clean_token(infered_token_in),
                'token_out': clean_token(infered_token_out),
                'amount_in': int(r.amount),
                'amount_out': int(r.amount),
            })
        if r.action == 'mint':

            if r.contract_address == AUST_TOKEN_ADDRESS:
                pass
            else:
                if (indexes_and_sections[index-1][1].action == 'lock_collateral'):
                    fake_pair = indexes_and_sections[index-1][1].borrower

                    infered_token_input = df_sections_pre[:index][df_sections_pre[:index].action ==
                                                                  'send'].iloc[-1].contract_address
                    sections_clean.append({
                        'pair': fake_pair,
                        'token_in': clean_token(infered_token_input),
                        'token_out': clean_token(r.contract_address),  # lo que se minteo es lo que sale
                        'amount_in': int(r.amount),
                        # creo q siempre es lo mismo
                        'amount_out': int(r.amount),
                    })
        if r.action == 'deposit_stable' and r.contract_address == ANCHOR_ADDRESS:
            sections_clean.append({
                'pair': r.contract_address,
                'token_in': 'uusd',
                'token_out': AUST_TOKEN_ADDRESS,
                'amount_in': int(r.deposit_amount),
                'amount_out': int(r.mint_amount),  # creo q siempre es lo mismo
            })

        if r.action == 'convert_stluna':
            sections_clean.append({
                'pair': r.contract_address,
                'token_in': ST_LUNA_TOKEN_ADDRESS,
                'token_out': BLUNA_TOKEN_ADDRESS,
                'amount_in': int(r.stluna_amount),
                # creo q siempre es lo mismo
                'amount_out': int(r.bluna_amount),
            })



    if len(logs_swap_adhoc) > 0:

        r = {l['key']: l['value'] for l in logs_swap_adhoc}
        parsed_r = {
                'pair': '<native-swap>',
                'token_in': clean_token(remove_numbers(r['offer'])),
                'token_out': clean_token(remove_numbers(r['swap_coin'])),
                'amount_in': int(remove_letters(r['offer'])),
                'amount_out': int(remove_letters(r['swap_coin'])),
            }

        # if the last token_out is the token_in of this swap and the amount is the same
        #  then we put this swap at the end
        if (sections_clean[-1]['token_out'] == parsed_r['token_in']) and (sections_clean[-1]['amount_out'] == parsed_r['amount_in']):
            sections_clean.append(parsed_r)
        # if the first token_in is the same of this swap token_out and the amount matches
        # then we put this swap at the beginning
        elif (sections_clean[0]['token_in'] == parsed_r['token_out']) and (sections_clean[0]['amount_in'] == parsed_r['amount_out']):
            sections_clean = [parsed_r]+sections_clean
        else:
            raise ErrorSwapAdhoc('swap_adhoc, there is a swap in the middle of the tx, we dont know how to handle it')



    return pd.DataFrame(sections_clean)


def get_tokens(df_sections):
    if len(df_sections) == 0:
        return []
    return df_sections.token_in.tolist()+[df_sections.tail(1).token_out.values[0]]


def get_contracts(df_sections):
    if len(df_sections) == 0:
        return []
    return df_sections.pair.tolist()


def get_amounts(df_sections):
    if len(df_sections) == 0:
        return []
    return list(set(df_sections.amount_in.tolist()+df_sections.amount_out.tolist()))

 
def get_txs_from_terra_sdk(txhash):
    # from terra_sdk.client.lcd import LCDClient
    # if '/Users/fcarrillo' in os.path.abspath('./'):
    #     terra = LCDClient(url='https://lcd.terra.dev', chain_id='columbus-5')
    # else:
    #     terra = LCDClient(url='http://localhost:1317', chain_id='columbus-5')
    # tx = terra.tx.tx_info(txhash)
    res = requests.get(f'https://lcd.terra.dev/cosmos/tx/v1beta1/txs/{txhash}')
    res_json = res.json()
    tx = TxInfo.from_data(res_json['tx_response'])

    logs = tx.logs[-1].events
    logs_wasm = logs[-1]['attributes']
    logs_swap_adhoc = []


    try:
        potencial_results = [
            l for l in logs if 'type' in l and l['type'] == 'swap']
        if len(potencial_results) > 0:
            logs_swap_adhoc = potencial_results[-1]['attributes']
    except:
        pass
    return logs_wasm, logs_swap_adhoc


def test():

    data_test = [
        {
            "hash": "04272b76d1f033bf86b2d9eb203f077f6325b9a843ea64b0cad5a9cb5f81dea6",
            "contracts_real": [
                "terra1v5ct2tuhfqd0tf8z0wwengh4fg77kaczgf6gtx",
                "terra10lv5wz84kpwxys7jeqkfxx299drs3vnw0lj8mz",
                "terra1cda4adzngjzcn8quvfu2229s8tedl5t306352x",
                "terra1j66jatn3k50hjtg2xemnjm8s7y8dws9xqa5y8w",
                "terra1m6ywlgn6wrjuagcmmezzz2a029gtldhey5k552"
            ],
            "tokens_real": [
                "uusd",
                "terra12897djskt9rge8dtmm86w654g7kzckkd698608",
                "terra10f2mt82kjnkxqj2gepgwl637u2w4ue2z5nhz5j",
                "terra1kc87mu460fwkqte29rquh4hc20m54fxwtsx7gp",
                "uluna",
                "uusd"
            ],
            "amounts_real": [
                13647309570,
                1185978963083,
                862692167,
                862692167,
                716737568,
                13706830030
            ]
        },
        {
            "hash": "288e5494ca6035d00df46d2288970392dc2ada60a8f8a8cc8fc51cd2a05f3ef2",
            "contracts_real": [
                "terra1c0afrdc5253tkp5wt7rxhuj42xwyf2lcre0s7c",
                "terra1tfrecwlvzcv9h697q3g0d08vd53ssu5w4war4n",
                "terra14zhkur7l7ut7tx6kvj28fp5q982lrqns59mnp3",
                "terra163pkeeuwxzr0yhndf8xd2jprm9hrtk59xf7nqf"
            ],
            "tokens_real": [
                "uusd",
                "terra1dzhzukyezv0etz22ud940z7adyv7xgcjkahuun",
                "terra178v546c407pdnx5rer3hu8s2c0fc924k74ymnn",
                "terra12897djskt9rge8dtmm86w654g7kzckkd698608",
                "uusd"
            ],
            "amounts_real": [
                5998598832,
                1454989,
                1454989,
                62700168363,
                6025042436
            ]
        },
        {
            "hash": "BD32DCF36890610BFB1D1F04F0452FB35934CD03F9E513CE06CD742A23E7F2BE",
            "contracts_real": [
                "terra1tndcaqxkpc5ce9qee5ggqf430mr2z3pefe5wj6",
                "terra1nujm9zqa4hpaz9s8wrhrp86h3m9xwprjt9kmf9",
                "terra1l7xu2rl3c7qmtx3r5sd2tz25glf6jh8ul7aag7"
            ],
            "tokens_real": [
                "uusd",
                "uluna",
                "terra1xj49zyqrwpv5k928jwfpfy2ha668nwdgkwlrg3",
                "uusd"
            ],
            "amounts_real": [
                62601969,
                7057941202,
                171860067,
                62833952
            ]
        },
        {
            "hash": "840A01F4273ADF1708C59EEC813697816F85584B31BE426D08A1E7DE676D2D5C",
            "contracts_real": [
                "terra1prfcyujt9nsn5kfj5n925sfd737r2n8tk5lmpv",
                "terra13awymgywq8nth34qgjaa6rm6junfqv3nxaupnw"
            ],
            "tokens_real": [
                "uusd",
                "terra1rhhvx8nzfrx5fufkuft06q5marfkucdqwq5sjw",
                "uusd"
            ],
            "amounts_real": [
                614303165,
                12958930,
                794249948
            ]
        },
        {
            "hash": "4EEA34C07E7705A4E4120BC89FBA08F1DC9549D5C0A856362CD82801092E8C39",
            "contracts_real": [
                "terra10k7y9qw63tfwj7e3x4uuzru2u9kvtd4ureajhd",
                "terra1tksv8cn7j95mecxjhj3dgcz3xtylcw5xkarre7",
                "terra17e0aslpj3rrt62gwh7utj3fayas4h8dl3y8ju3"
            ],
            "tokens_real": [
                "uusd",
                "terra1nef5jf6c7js9x6gkntlehgywvjlpytm7pcgkn4",
                "terra1aa7upykmmqqc63l924l5qfap8mrmx5rfdm0v55",
                "uusd"
            ],
            "amounts_real": [
                25358147,
                2582181965,
                4291,
                25924354
            ]
        },
        {
            "hash": "1640d67ce5c89a023517ffeecbfc62813430da781e70046f71c9519be210bcf0",
            "contracts_real": [
                "terra17kmgn775v2y9m35gunn3pnw8s2ggv6h95wvkxr",
                "terra1m32zs8725j9jzvva7zmytzasj392wpss63j2v0",
                "terra1m6ywlgn6wrjuagcmmezzz2a029gtldhey5k552"
            ],
            "tokens_real": [
                "uusd",
                "terra14tl83xcwqjy0ken9peu4pjjuu755lrry2uy25r",
                "uluna",
                "uusd"
            ],
            "amounts_real": [
                1373218663,
                50119302,
                72836726,
                1391412899
            ]
        },
        {
            "hash": "25B028336C59A64244CEE2617014431CCB597CFFF2D82000FD67B5FD059E9E6B",
            "contracts_real": [
                "terra1z6tp0ruxvynsx5r9mmcc2wcezz9ey9pmrw5r8g",
                "terra1mxyp5z27xxgmv70xpqjk7jvfq54as9dfzug74m"
            ],
            "tokens_real": [
                "uusd",
                "terra1mddcdx0ujx89f38gu7zspk2r2ffdl5enyz2u03",
                "uusd"
            ],
            "amounts_real": [
                1000000000,
                880143418225,
                1024266339
            ]
        },
        {
            "hash": "70e11ad816f955478833697903274bc91b9b572af844555b17aba8be518f99cc",
            "contracts_real": [
                "terra1sepfj7s0aeg5967uxnfk4thzlerrsktkpelm5s",
                "terra16j5f4lp4z8dddm3rhyw8stwrktyhcsc8ll6xtt",
                "<native-swap>"
            ],
            "tokens_real": [
                "uusd",
                "terra1hzh9vpxhsk8253se0vv5jj6etdvxu3nv8z07zu",
                "uluna",
                "uusd"
            ],
            "amounts_real": [
                2000000000,
                1669345784,
                37865388,
                2002062403
            ]
        },
        {
            "hash": "25fced25917786aac7d6135089eba1123184374fb4cb848e55ce6d88d99deb41",
            "contracts_real": [
                "terra1sepfj7s0aeg5967uxnfk4thzlerrsktkpelm5s",
                "terra16j5f4lp4z8dddm3rhyw8stwrktyhcsc8ll6xtt",
                "terra1m6ywlgn6wrjuagcmmezzz2a029gtldhey5k552"
            ],
            "tokens_real": [
                "uusd",
                "terra1hzh9vpxhsk8253se0vv5jj6etdvxu3nv8z07zu",
                "uluna",
                "uusd"
            ],
            "amounts_real": [
                1500000000,
                1280073591,
                19323229,
                1545637154
            ]
        },
        {
            "hash": "0cab7f93751d42d0ed33f3512760fc3e1833a84a8137d3812dcee18326e36279",
            "contracts_real": [
                "terra1gxjjrer8mywt4020xdl5e5x7n6ncn6w38gjzae",
                "terra1mtwph2juhj0rvjz7dy92gvl6xvukaxu8rfv8ts",
                "terra1j66jatn3k50hjtg2xemnjm8s7y8dws9xqa5y8w"
            ],
            "tokens_real": [
                "uluna",
                "terra1yg3j2s986nyp5z7r2lvt0hx3r0lnd7kwvwwtsc",
                "terra1kc87mu460fwkqte29rquh4hc20m54fxwtsx7gp",
                "uluna"
            ],
            "amounts_real": [
                500000000,
                503222236,
                510259687,
                500050855
            ]
        }
    ]

    for r in data_test:
        tx_hash = r['hash']
        print(tx_hash)
        logs_wasm, logs_swap_adhoc = get_txs_from_terra_sdk(tx_hash)

        df_sections = get_sections(logs_wasm, logs_swap_adhoc)
        contracts = get_contracts(df_sections)
        tokens = get_tokens(df_sections)
        amounts = get_amounts(df_sections)

        assert(set(r['contracts_real']) == set(contracts))
        assert(set(r['tokens_real']) == set(tokens))
        assert(set(r['amounts_real']) == set(amounts))
        print('PASS')
        print()


def analyze_arb_opportunity_from_tx_hash(tx_hash):
    logs_wasm, logs_swap_adhoc = get_txs_from_terra_sdk(tx_hash)

    df_sections = get_sections(logs_wasm, logs_swap_adhoc)
    if len(df_sections) > 0:
        contracts = get_contracts(df_sections)
        tokens = get_tokens(df_sections)
        amounts = get_amounts(df_sections)

        hay_arb, arb = check_arbitrage_and_return_profit_from_logs(logs_wasm, logs_swap_adhoc)
        return {'is_arb': hay_arb, 'arb': arb, 'contracts': contracts, 'tokens': tokens, 'amounts': amounts}
    return {'is_arb': False}


def check_arbitrage_and_return_profit(tx, execute_msg):
    try:
        logs = tx['logs'][-1]['events']
        logs_wasm = logs[-1]['attributes']
        logs_swap_adhoc = []
        try:
            logs_swap_adhoc = [l for l in logs if 'type' in l and l['type'] == 'swap'][-1]['attributes']
        except: pass

         # caso de ejemplo https://finder.terra.money/classic/tx/1654faa64343e65a733b58848c63e0fdb658700922ad0d0c41f0830996ae9802
        return check_arbitrage_and_return_profit_from_logs(logs_wasm, logs_swap_adhoc)
    except Exception as e:
        logs = open('txs_fails.txt', 'a')
        error_r = {'tx_hash': tx['hash'], 'execute_msg': str(execute_msg),'error': str(e)}
        logs.write(json.dumps(error_r)+'\n')
        logs.close()
        return False, {}


def check_arbitrage_and_return_profit_from_logs(logs_wasm, logs_swap_adhoc):
    df_sections = get_sections(logs_wasm, logs_swap_adhoc)

    if len(df_sections) == 0:
        # no tiene secciones
        return False, {}

    tokens = get_tokens(df_sections)

    try:
        start_token = df_sections[df_sections.amount_in == list(set(df_sections.amount_in.tolist())-set(df_sections.amount_out.tolist()))[0]].iloc[0].token_in
        end_token = df_sections[df_sections.amount_out == list(set(df_sections.amount_out.tolist())-set(df_sections.amount_in.tolist()))[0]].iloc[0].token_out
    except:
        return False, {}

    if start_token == end_token:

        r = {}
        r['path'] = df_sections.to_dict('records')
        r['profit'] = r['path'][-1]['amount_out'] - r['path'][0]['amount_in']
        r['profit_rate'] = r['profit'] / r['path'][0]['amount_in']
        r['amount_in'] = r['path'][0]['amount_in']
        r['amount_out'] = r['path'][-1]['amount_out']
        r['token_in'] = tokens[0]

        return True, r

    else:
        return False, {}
