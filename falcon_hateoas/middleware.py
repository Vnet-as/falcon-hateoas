import json
import decimal
import datetime


class AlchemyJSONEncoder(json.JSONEncoder):
    def default(self, o):
        d = {}
        for col in o.__table__.columns.keys():
            value = getattr(o, col)
            if hasattr(value, 'isoformat'):
                d[col] = value.isoformat()
            elif isinstance(value, datetime.timedelta):
                d[col] = str(value)
            elif isinstance(value, decimal.Decimal):
                d[col] = float(value)
            else:
                d[col] = value
        return d


class JsonMiddleware:
    def process_response(self, req, resp, resource):
        resp.set_header('Content-Type', 'application/json; charset=utf-8')
        resp.body = json.dumps(resp.body, cls=AlchemyJSONEncoder)
