"""Read-only NEAR JSON-RPC adapter: pinned-block access-key reads with bounded retries."""
import json, time, urllib.error, urllib.request

DEFAULT_ENDPOINT = 'https://rpc.mainnet.fastnear.com'
RETRYABLE_HTTP = {408, 425, 429, 500, 502, 503, 504}


class RPCError(Exception):
    def __init__(self, message, code='RPC_ERROR'):
        super().__init__(message)
        self.code = code


def _error_code(err):
    text = json.dumps(err).lower() if not isinstance(err, str) else err.lower()
    if 'unknown_account' in text or 'does not exist while viewing' in text:
        return 'ACCOUNT_NOT_FOUND'
    return 'RPC_ERROR'


def rpc(endpoint, method, params, timeout=15, api_key=None, retries=3, backoff=1.0, sleep=time.sleep):
    data = json.dumps({'jsonrpc': '2.0', 'id': 'residual', 'method': method, 'params': params}).encode()
    headers = {'Content-Type': 'application/json', 'User-Agent': 'Residual-NEAR/1.1'}
    if api_key:
        headers['Authorization'] = 'Bearer ' + api_key
    last = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(endpoint, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as res:
                result = json.load(res)
        except urllib.error.HTTPError as exc:
            last = RPCError('HTTP %s' % exc.code)
            if exc.code not in RETRYABLE_HTTP:
                raise last from exc
        except (OSError, ValueError) as exc:
            last = RPCError(str(exc)[:200])
        else:
            if 'error' in result:
                raise RPCError(str(result['error'])[:300], _error_code(result['error']))
            if 'result' not in result:
                raise RPCError('missing result')
            inner = result['result']
            if isinstance(inner, dict) and isinstance(inner.get('error'), str):  # older query error shape
                raise RPCError(inner['error'][:300], _error_code(inner['error']))
            return inner
        if attempt < retries:
            sleep(backoff * (2 ** attempt))
    raise last


def network_info(endpoint, **kw):
    s = rpc(endpoint, 'status', [], **kw)
    return {'chain_id': s.get('chain_id'), 'protocol_version': s.get('protocol_version'),
            'node_version': (s.get('version') or {}).get('version')}


def _block_meta(b):
    h = b.get('header', {}) if isinstance(b, dict) else {}
    if not h.get('hash') or h.get('height') is None:
        raise RPCError('invalid block header')
    return {'hash': h['hash'], 'height': h['height'], 'prev_hash': h.get('prev_hash'),
            'timestamp_nanosec': h.get('timestamp_nanosec'),
            'latest_protocol_version': h.get('latest_protocol_version')}


def finalized_block(endpoint, **kw):
    return _block_meta(rpc(endpoint, 'block', {'finality': 'final'}, **kw))


def scan(endpoint, ids, delay=0, block=None, **kw):
    """Read every account's access keys at ONE block. Failures stay in the output with a status."""
    block = block or finalized_block(endpoint, **kw)
    output = []
    for account in ids:
        try:
            r = rpc(endpoint, 'query', {'request_type': 'view_access_key_list', 'account_id': account,
                                        'block_id': block['hash']}, **kw)
            if r.get('block_hash') and r['block_hash'] != block['hash']:
                raise RPCError('inconsistent block hash')
            if not isinstance(r.get('keys'), list):
                raise RPCError('missing keys')
            output.append({'account_id': account, 'keys': r['keys'], 'status': 'OK'})
        except RPCError as exc:
            status = 'ACCOUNT_NOT_FOUND' if exc.code == 'ACCOUNT_NOT_FOUND' else 'RPC_ERROR'
            output.append({'account_id': account, 'keys': None, 'status': status, 'error': str(exc)[:300]})
        if delay:
            time.sleep(delay)
    return block, output
