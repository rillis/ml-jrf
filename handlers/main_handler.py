from cfg import config
from utils import db
from handlers import debug, messages, orders_v2, post_purchase, questions


def handle(req):
    try:
        data = req.get_json(silent=True)
        
        if config.DEBUG: print(f'topic: {data.get("topic", "-")}, resource: {data.get("resource", "-")}')

        if data.get('topic', '-') == 'post_purchase' and len(data.get('actions', []))>=1 and data['actions'][0] == 'claims_actions':
            return {'Status': 'Not Supported'}, 400
        if data.get('topic', '-') == 'items':
            return {'Status': 'Not Supported'}, 400

        with db.DBConnection() as conn:
            sql = "INSERT INTO posts (engine, post_time, url, content) VALUES (%s, now(), %s, %s)"
            val = (config.CONTA, str(dict(req.headers)['Host']), str(data).replace("'", "'"))
            conn.execute(sql, val=val)

        if not data or 'resource' not in data.keys():
            print(f'Request rejeitado, sem resource ou None')
            debug.handle(data)
            return {'Status': 'Without Resource or empty data'}, 400
        
        if data['topic'] == 'orders_v2':
            return orders_v2.handle(data)
        if data['topic'] == 'messages':
            return messages.handle(data)
        if data['topic'] == 'questions':
            return questions.handle(data)
        if data['topic'] == 'post_purchase' and len(data['actions'])>=1 and data['actions'][0] == 'claims':
            return post_purchase.handle(data)
        
        debug.handle(data)
        return {"status": "Wrong pattern"}, 400
    except ValueError:
        print(f'Request rejeitado, não é json')
        debug.handle(data)
        return {'Status': 'Not JSON'}, 400

    