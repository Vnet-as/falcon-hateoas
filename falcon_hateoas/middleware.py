import json
import decimal
import datetime
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
            for col_name, col in o.__table__.columns.items():
                if hasattr(col, 'isoformat'):
                    d[col_name] = col.isoformat()
                elif isinstance(col, datetime.timedelta):
                    d[col_name] = str(col)
                elif isinstance(col, decimal.Decimal):
                    d[col_name] = float(col)
                else:
                    d[col_name] = col
            return d
        else:
            return super(AlchemyJSONEncoder, self).default(o)


class JsonMiddleware:
    def process_response(self, req, resp, resource):
        resp.set_header('Content-Type', 'application/json; charset=utf-8')
        resp.body = json.dumps(resp.body, cls=AlchemyJSONEncoder)
