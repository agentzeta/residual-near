"""Five-state classification of NEAR account access keys (observed access-key layer only)."""
import hashlib, json, math

STATES = ('CLASSICAL_ONLY', 'INCOMPLETE_WEAKEST_LINK', 'COMPLETE', 'PQ_FUNCTION_ONLY', 'UNDETERMINED')

# Key forms that view_access_key_list can return, with the decoded byte length of the base58 payload.
# NEP-645: ML-DSA-65 entries are listed only as a handle, the base58 of a 32-byte SHA3-256 digest.
KEY_FORMS = (('ml-dsa-65-hash:', 'PQ', 32), ('ed25519:', 'CLASSICAL', 32), ('secp256k1:', 'CLASSICAL', 64))
FULL_PQ_PREFIX = 'ml-dsa-65:'  # full ML-DSA public keys never appear in list responses
CLASSICAL = ('ed25519:', 'secp256k1:')
PQ = 'ml-dsa-65-hash:'

_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
_INDEX = {c: i for i, c in enumerate(_ALPHABET)}


def b58decode(text):
    if not text:
        raise ValueError('empty base58 string')
    n = 0
    for ch in text:
        if ch not in _INDEX:
            raise ValueError('invalid base58 character')
        n = n * 58 + _INDEX[ch]
    body = n.to_bytes((n.bit_length() + 7) // 8, 'big') if n else b''
    return b'\0' * (len(text) - len(text.lstrip('1'))) + body


def b58encode(raw):
    n, out = int.from_bytes(raw, 'big'), ''
    while n:
        n, r = divmod(n, 58)
        out = _ALPHABET[r] + out
    return '1' * (len(raw) - len(raw.lstrip(b'\0'))) + out


def inspect_key(entry):
    """Return (key_type, issue). key_type is e.g. 'PQ_FULL' or 'UNKNOWN'; issue explains UNKNOWN."""
    if not isinstance(entry, dict) or not isinstance(entry.get('public_key'), str):
        return 'UNKNOWN', 'MISSING_PUBLIC_KEY'
    key = entry['public_key']
    access_key = entry.get('access_key')
    permission = access_key.get('permission') if isinstance(access_key, dict) else None
    if permission == 'FullAccess':
        access = 'FULL'
    elif isinstance(permission, dict) and isinstance(permission.get('FunctionCall'), dict):
        access = 'FUNCTION'
    else:
        return 'UNKNOWN', 'UNRECOGNIZED_PERMISSION'
    for prefix, kind, size in KEY_FORMS:
        if key.startswith(prefix):
            try:
                decoded = b58decode(key[len(prefix):])
            except ValueError:
                return 'UNKNOWN', 'MALFORMED_KEY'
            if len(decoded) != size:
                return 'UNKNOWN', 'WRONG_KEY_LENGTH'
            return kind + '_' + access, None
    if key.startswith(FULL_PQ_PREFIX):
        return 'UNKNOWN', 'UNEXPECTED_FULL_PQ_KEY'
    return 'UNKNOWN', 'UNSUPPORTED_KEY_TYPE'


def classify_key(entry):
    return inspect_key(entry)[0]


_STATUS_REASON = {'ACCOUNT_NOT_FOUND': 'ACCOUNT_NOT_FOUND'}


def classify_account(account_id, entries, status='OK'):
    base = {'account_id': account_id, 'status': status, 'key_types': [], 'notes': []}
    if status != 'OK':
        return {**base, 'state': 'UNDETERMINED', 'reason_code': _STATUS_REASON.get(status, 'RPC_ERROR'),
                'reason': 'RPC read unavailable; kept in the denominator as unresolved'}
    if not isinstance(entries, list):
        return {**base, 'state': 'UNDETERMINED', 'reason_code': 'MALFORMED_RESPONSE',
                'reason': 'Access-key list missing or malformed'}
    inspected = [inspect_key(k) for k in entries]
    types = [t for t, _ in inspected]
    issues = sorted({i for _, i in inspected if i})
    base['key_types'] = types
    if issues:
        base['notes'] = issues
    code = None
    if not types:
        state, code = 'UNDETERMINED', 'NO_ACCESS_KEYS'
    elif 'UNKNOWN' in types:
        state, code = 'UNDETERMINED', 'UNRECOGNIZED_KEY'
    elif 'CLASSICAL_FULL' in types and 'PQ_FULL' in types:
        state = 'INCOMPLETE_WEAKEST_LINK'
    elif 'CLASSICAL_FULL' in types:
        state = 'CLASSICAL_ONLY'
    elif 'PQ_FULL' in types:
        state = 'COMPLETE'
    elif 'PQ_FUNCTION' in types:
        state = 'PQ_FUNCTION_ONLY'
    else:
        state, code = 'UNDETERMINED', 'CLASSICAL_FUNCTION_ONLY'
    if state in ('COMPLETE', 'PQ_FUNCTION_ONLY') and 'CLASSICAL_FUNCTION' in types:
        base['notes'] = base['notes'] + ['RESIDUAL_CLASSICAL_FUNCTION_KEYS']
    if code == 'UNRECOGNIZED_KEY' and 'CLASSICAL_FULL' in types:
        base['notes'] = base['notes'] + ['CLASSICAL_FULL_ACCESS_OBSERVED']
    return {**base, 'state': state, 'reason_code': code,
            'reason': 'Observed access-key layer only; not a claim of quantum safety'}


def wilson(k, n, z=1.959963984540054):
    """95% Wilson score interval for k successes out of n, or None when n == 0."""
    if not n:
        return None
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [max(0.0, centre - half), min(1.0, centre + half)]


def summarize(accounts, random_draw=False):
    counts = {s: 0 for s in STATES}
    reasons = {}
    for a in accounts:
        counts[a['state']] += 1
        if a['state'] == 'UNDETERMINED':
            code = a.get('reason_code') or 'UNSPECIFIED'
            reasons[code] = reasons.get(code, 0) + 1
    n = len(accounts)
    resolved = n - counts['UNDETERMINED']
    pq_present = sum(('PQ_FULL' in a['key_types']) or ('PQ_FUNCTION' in a['key_types']) for a in accounts)
    classical_full = sum('CLASSICAL_FULL' in a['key_types'] for a in accounts)
    pq_full = counts['COMPLETE'] + counts['INCOMPLETE_WEAKEST_LINK']
    summary = {
        'requested': n, 'resolved': resolved, 'unresolved': counts['UNDETERMINED'],
        'unresolved_by_reason': dict(sorted(reasons.items())), 'counts': counts,
        'pq_key_present': pq_present, 'classical_full_access_present': classical_full,
        'complete_share_of_requested': counts['COMPLETE'] / n if n else None,
        'complete_share_of_resolved': counts['COMPLETE'] / resolved if resolved else None,
        'complete_share_of_pq_full_access': counts['COMPLETE'] / pq_full if pq_full else None,
        'population_inference': False, 'scope': 'observed access-key layer only',
    }
    if random_draw:
        summary['interval_95'] = {
            'note': 'Wilson interval for a seeded random draw from the stated sampling frame only; '
                    'not an estimate for all NEAR accounts',
            'pq_key_present_share_of_resolved': wilson(pq_present, resolved),
            'classical_full_access_share_of_resolved': wilson(classical_full, resolved),
            'complete_share_of_resolved': wilson(counts['COMPLETE'], resolved),
        }
    return summary


def canonical_digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
