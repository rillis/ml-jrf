from scripts.migrate import keys_from_recent


def test_keys_from_recent(tmp_path):
    f = tmp_path / 'recent.log'
    f.write_text(str([
        '/orders/1', '/questions/2', '01a1b6738e7b',
        '/post-purchase/v1/claims/9-0', '/post-purchase/v1/claims/9-3', '/post-purchase/v1/claims/9-1',
    ]))
    rows = set(keys_from_recent(f))
    assert rows == {
        ('/orders/1', 'orders_v2', 'orders_v2', None),
        ('/questions/2', 'questions', 'questions', None),
        ('01a1b6738e7b', 'messages', 'messages', None),
        ('/post-purchase/v1/claims/9', 'post_purchase', 'claims', '3'),
    }


def test_dedup_key():
    from app.queue import dedup_key
    data = {'_id': 'n1', 'resource': '/orders/1'}
    assert dedup_key(data, 'orders_v2', False) == '/orders/1'
    assert dedup_key(data, 'debug', False) == 'debug:n1'
    a, b = dedup_key(data, 'orders_v2', True), dedup_key(data, 'orders_v2', True)
    assert a != b and a.startswith('/orders/1#debug-')
