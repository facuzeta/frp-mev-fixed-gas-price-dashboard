
1. Enter into the container

```docker-compose exec web "/bin/bash"```

2. Make migrations and apply them

```bash
cd /code/dashboard_site/;
python manage.py makemigrations;
python manage.py makemigrations terra_classic;
python manage.py makemigrations osmosis;
python manage.py migrate;
python manage.py createcachetable;
```

3. Get and populate the Terra Classic data: 

Small dataset (~350 MB):
```bash
mkdir -p /code/small_data/;
cd /code/small_data/;
wget https://frp-terra.s3.us-east-2.amazonaws.com/subset_small/terra_classic_dump_blocks.csv;
wget https://frp-terra.s3.us-east-2.amazonaws.com/subset_small/terra_classic_dump_arbs.csv;
wget https://frp-terra.s3.us-east-2.amazonaws.com/subset_small/terra_classic_dump_txs.csv.zip;
unzip terra_classic_dump_txs.csv.zip;
psql postgres://postgres:postgres@db:5432/postgres;
```

Big dataset (~7.5 GB):

```bash
mkdir -p /code/small_data/;
cd /code/small_data/;
wget https://frp-terra.s3.us-east-2.amazonaws.com/terra_classic_dump_blocks.csv;
wget https://frp-terra.s3.us-east-2.amazonaws.com/terra_classic_dump_arbs.csv;
wget https://frp-terra.s3.us-east-2.amazonaws.com/terra_classic_dump_txs.csv.zip; 
unzip terra_classic_dump_txs.csv.zip;
psql postgres://postgres:postgres@db:5432/postgres;
```



4. Then copy in psql the followings commands:
```
\copy terra_classic_block (height, timestamp, number_of_txs, number_of_txs_with_execute_contract_msg, number_of_txs_with_succeded_arbs)  FROM 'terra_classic_dump_blocks.csv' DELIMITER ';' CSV ENCODING 'UTF8' QUOTE '"';
\copy terra_classic_txcontractexecution (hash, "order", success, fee, fee_token, memo, sender, contract, execute_msg, gas_wanted, gas_used, block_id, "timestamp")  FROM 'terra_classic_dump_txs.csv' DELIMITER ';' CSV ENCODING 'UTF8' QUOTE '"';
\copy terra_classic_arb (id, success, profit, profit_rate, amount_in, amount_out, token_in, path,  tx_id, "timestamp")  FROM 'terra_classic_dump_arbs.csv' DELIMITER ';' CSV ENCODING 'UTF8' QUOTE '"';
```




