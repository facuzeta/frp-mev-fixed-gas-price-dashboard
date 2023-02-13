## How to run

1. Define a new file ./dashboard_site/dashboard_site/.env  with a new secrete key for Django, and the api key of allthatnode.com.

For example:


```
DEBUG=on
OSMOSIS_DECODER_BIN_FN='/code/osmosisd_decoder'
OSMOSIS_LCD_URL='https://osmosis-mainnet-rpc.allthatnode.com:1317'
OSMOSIS_RPC_URL='https://osmosis-mainnet-rpc.allthatnode.com:26657'
SECRET_KEY='qflfdt^7lufhf2+zyt6lwvvwlbyd#unv$m2j+xyo#4u&%(#-_b'
ALLTHATNODE_APIKEY='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
```

2. Build and run container: docker-compose up  --build

3. Populate data: follow instruction from https://github.com/facuzeta/frp-mev-fixed-gas-price-tools/blob/main/populate_data.md

4. Check http://localhost:8000/ 

5. Start cron-job to get osmosis data from allthatnode.com:

```bash
docker-compose exec web service cron start
```

## TODO:

1. Add apache or nginx for production environment (right now is running with runserver)
