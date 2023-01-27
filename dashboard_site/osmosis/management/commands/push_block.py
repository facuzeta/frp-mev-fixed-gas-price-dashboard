import json
from django.core.management.base import BaseCommand, CommandError
from osmosis.models import *
from osmosis.services_download_and_parse_data import get_data_and_populate

class Command(BaseCommand):
    help = 'Get data from rcp and lcd and push data to db'

    def add_arguments(self, parser):
        parser.add_argument('height', type=int)

    def handle(self, *args, **options):
        height = options['height']
        self.stdout.write(str(height))
        res = get_data_and_populate(height)
        if 'status' not in res:
            self.stdout.write(json.dumps({'status': 'error'}))
        else:
            self.stdout.write(json.dumps(res))


