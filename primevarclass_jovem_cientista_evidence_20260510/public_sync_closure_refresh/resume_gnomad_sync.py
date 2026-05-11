"""Resume capped gnomAD GraphQL sync for PrimeVarClass.

This script is intentionally conservative. It reads the pending queue,
queries a small batch, appends a cache file, and stops on rate limits.
"""
from __future__ import annotations

import csv
import json
import time
import urllib.request
from pathlib import Path

QUEUE_PATH = Path(r'''C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_jovem_cientista_evidence_20260510\public_sync_closure_refresh\gnomad_sync_queue.csv''')
CACHE_PATH = Path(r'''C:\Users\Wesley Capucho\Documents\IA dos números primos\primevarclass_jovem_cientista_evidence_20260510\public_sync_closure_refresh\gnomad_sync_cache.csv''')
BATCH_SIZE = 40
SLEEP_SECONDS = 1
ENDPOINT = 'https://gnomad.broadinstitute.org/api'

QUERY = '''
query Variant($variantId: String!, $dataset: DatasetId!) {
  variant(variantId: $variantId, dataset: $dataset) {
    variant_id reference_genome exome { ac an af } genome { ac an af }
  }
}
'''

def post(payload):
    body = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(ENDPOINT, data=body, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.loads(response.read().decode('utf-8'))

rows = list(csv.DictReader(QUEUE_PATH.open('r', encoding='utf-8')))
cached_ids = set()
if CACHE_PATH.exists():
    with CACHE_PATH.open('r', encoding='utf-8', newline='') as cache_handle:
        for cached in csv.DictReader(cache_handle):
            if cached.get('gnomad_variant_id') and cached.get('status') in {'found', 'not_found'}:
                cached_ids.add(cached.get('gnomad_variant_id'))
retry_statuses = {'pending_query', 'graphql_error_retry_later', 'cached_error_retry_later', 'rate_limited_retry_later'}
pending = [row for row in rows if row.get('gnomad_variant_id') not in cached_ids and row.get('gnomad_sync_status') in retry_statuses]
CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
write_header = not CACHE_PATH.exists()
with CACHE_PATH.open('a', encoding='utf-8', newline='') as handle:
    writer = csv.DictWriter(handle, fieldnames=['gnomad_variant_id','status','gene','hgvs_p','variation_id','live_gnomad_af','live_gnomad_ac','live_gnomad_an','error','cached_at'])
    if write_header:
        writer.writeheader()
    for row in pending[:BATCH_SIZE]:
        variant_id = row.get('gnomad_variant_id') or ''
        if not variant_id:
            continue
        try:
            payload = {'query': QUERY, 'variables': {'variantId': variant_id, 'dataset': 'gnomad_r4'}}
            response = post(payload)
            if response.get('errors'):
                error = json.dumps(response.get('errors'))[:500]
                status = 'not_found' if 'Variant not found' in error else 'graphql_error'
                ac = an = af = ''
            else:
                variant = (response.get('data') or {}).get('variant') or {}
                exome = variant.get('exome') or {}
                genome = variant.get('genome') or {}
                preferred = exome if exome.get('an') else genome
                status = 'found' if variant else 'not_found'
                ac, an, af = preferred.get('ac',''), preferred.get('an',''), preferred.get('af','')
                error = ''
        except Exception as exc:
            error = str(exc)
            status = 'query_error'
            ac = an = af = ''
        writer.writerow({'gnomad_variant_id': variant_id, 'status': status, 'gene': row.get('gene'), 'hgvs_p': row.get('hgvs_p'), 'variation_id': row.get('variation_id'), 'live_gnomad_af': af, 'live_gnomad_ac': ac, 'live_gnomad_an': an, 'error': error, 'cached_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())})
        handle.flush()
        if '429' in error or 'Too Many Requests' in error:
            break
        time.sleep(SLEEP_SECONDS)
