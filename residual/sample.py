"""Chain-derived sampling frame: distinct transaction signers in a block window, plus ML-DSA-65 enrollments.

The frame is reproducible: it is defined by a pinned head block and a window length, and the draw from it is
seeded by the head block hash. It is a frame of *recently active signers*, not of all NEAR accounts.
"""
import hashlib, time
from .rpc import rpc, RPCError, _block_meta

FULL_PQ_PREFIX = 'ml-dsa-65:'


def _actions(tx):
    """Yield (action, receiver_id, signer_id), unwrapping meta-transaction Delegate actions."""
    for a in tx.get('actions') or []:
        if isinstance(a, dict) and isinstance(a.get('Delegate'), dict):
            da = a['Delegate'].get('delegate_action') or {}
            for inner in da.get('actions') or []:
                yield inner, da.get('receiver_id'), da.get('sender_id')
        else:
            yield a, tx.get('receiver_id'), tx.get('signer_id')


def pq_enrollments(tx, height):
    found = []
    for action, receiver, signer in _actions(tx):
        add = action.get('AddKey') if isinstance(action, dict) else None
        if isinstance(add, dict) and str(add.get('public_key', '')).startswith(FULL_PQ_PREFIX):
            found.append({'account_id': receiver, 'signer_id': signer, 'tx_hash': tx.get('hash'),
                          'block_height': height})
    return found


def window_frame(endpoint, head, n_blocks, delay=0, **kw):
    signers, enrollments = set(), []
    stats = {'blocks_requested': n_blocks, 'blocks_read': 0, 'block_failures': 0,
             'chunks_read': 0, 'chunk_failures': 0, 'transactions': 0}
    cursor, lowest = head['hash'], head['height']
    for _ in range(n_blocks):
        try:
            block = rpc(endpoint, 'block', {'block_id': cursor}, **kw)
            meta = _block_meta(block)
        except RPCError:
            stats['block_failures'] += 1
            break  # without this block's prev_hash the walk cannot continue
        stats['blocks_read'] += 1
        lowest = meta['height']
        for chunk in block.get('chunks', []):
            if chunk.get('height_included') != meta['height']:
                continue  # chunk carried over from an earlier block; already counted there
            try:
                body = rpc(endpoint, 'chunk', {'chunk_id': chunk['chunk_hash']}, **kw)
                stats['chunks_read'] += 1
            except (RPCError, KeyError):
                stats['chunk_failures'] += 1
                continue
            for tx in body.get('transactions', []):
                stats['transactions'] += 1
                if isinstance(tx.get('signer_id'), str):
                    signers.add(tx['signer_id'])
                enrollments.extend(pq_enrollments(tx, meta['height']))
            if delay:
                time.sleep(delay)
        cursor = meta['prev_hash']
        if not cursor:
            break
    frame = {'kind': 'distinct transaction signers in a block window', 'head_height': head['height'],
             'head_hash': head['hash'], 'lowest_height': lowest, 'distinct_signers': len(signers),
             'pq_enrollment_events': len(enrollments),
             'complete': stats['blocks_read'] == n_blocks and not stats['chunk_failures'], **stats}
    return sorted(signers), enrollments, frame


def seeded_draw(ids, seed, n):
    """Deterministic pseudo-random draw: order by sha256(seed + id), take the first n."""
    return sorted(ids, key=lambda x: hashlib.sha256((seed + '\n' + x).encode()).hexdigest())[:n]
