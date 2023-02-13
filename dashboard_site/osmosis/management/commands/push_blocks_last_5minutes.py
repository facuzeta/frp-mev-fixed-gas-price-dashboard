import json
from django.core.management.base import BaseCommand, CommandError
from osmosis.models import *
from osmosis.services_download_and_parse_data import get_data_and_populate, get_last_height_on_chain
from tqdm import tqdm
from django.utils import timezone

# last 5 minutes should have ~ 50-60 blocks
MAX_BLOCKS_TO_PUSH = 60

class Command(BaseCommand):
    help = 'Get data from rcp and lcd and push data to db'

    def handle(self, *args, **options):

        last_block_on_chain = get_last_height_on_chain()
        last_height_on_chain = int(last_block_on_chain['height'])
        last_time_on_chain = str(last_block_on_chain['time'])

        try:
            last_block_we_have = Block.objects.all().order_by('-height').first()
            last_block_we_have_height = last_block_we_have.height
            last_block_we_have_timestamp = last_block_we_have.timestamp
        except:
            last_block_we_have_height = 0
            last_block_we_have_timestamp = 0


        self.stdout.write(str(timezone.now())+'\t Current block on chain: '+str(last_height_on_chain)+'\t'+str(last_time_on_chain))
        self.stdout.write(str(timezone.now())+'\t Current last block we have: '+str(last_block_we_have_height)+'\t'+str(last_block_we_have_timestamp))

        for height in tqdm(range(last_height_on_chain, last_block_we_have_height+1, -1)[:MAX_BLOCKS_TO_PUSH]):
            self.stdout.write(str(timezone.now())+'\t'+str(height))
            try:
                res = get_data_and_populate(height)
                if 'status' not in res:
                    self.stdout.write(json.dumps({'status': 'error'}))
                else:
                    self.stdout.write(json.dumps(res))
            except Exception as e:
                self.stdout.write(str(e))
                self.stdout.write(json.dumps({'status': 'error', 'msg': str(e)}))

