import json
import decimal
import sqlalchemy


class AlchemyJSONEncoder(json.JSONEncoder):
    def _is_alchemy_object(self, obj):
        try:
            sqlalchemy.orm.base.object_mapper(obj)
            return True
        except sqlalchemy.orm.exc.UnmappedInstanceError:
            return False

    def default(self, o):
        if self._is_alchemy_object(o):
            d = {}
            for col in o.__table__.columns.keys():
                if hasattr(getattr(o, col), 'isoformat'):
                    d[col] = getattr(o, col).isoformat()
                elif isinstance(getattr(o, col), decimal.Decimal):
                    d[col] = float(getattr(o, col))
                else:
                    d[col] = getattr(o, col)
            return d
        else:
            return super(AlchemyJSONEncoder, self).default(o)


class JsonMiddleware:
    def process_response(self, req, resp, resource):
        resp.set_header('Content-Type', 'application/json; charset=utf-8')
        resp.body = json.dumps(resp.body, cls=AlchemyJSONEncoder)
