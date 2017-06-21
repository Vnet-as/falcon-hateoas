import falcon
import json
import sqlalchemy
from .decorators import db_session


class ModelCollection:
    def __init__(self, sessionmaker=None):
        self.sessionmaker = sessionmaker

    @db_session
    def on_get(self, req, resp, dbsession):
        params = {
            'limit': None,
            'offset': 0,
            'order_by': None
        }
        params.update(req.params)
        result = dbsession.query(self.model_class)
        filter = self._prepare_filter(params)
        if len(filter) > 0:
            result = result.filter(*filter)
        if params['order_by'] is not None:
            result = result.order_by(params['order_by'])
        if params['limit'] is not None:
            result = result.limit(params['limit'])
        result = result.offset(params['offset'])
        resp.body = result.all()

    @db_session
    def on_post(self, req, resp, dbsession):
        resource = self.model_class()
        data = json.loads(req.bounded_stream.read().decode())
        for k, v in data.items():
            if hasattr(self.model_class.__table__.columns, k):
                setattr(resource, k, v)
        dbsession.add(resource)
        dbsession.commit()
        dbsession.refresh(resource)
        resp.body = resource

    def _prepare_filter(self, params):
        filter = []
        for k, v in params.items():
            column = getattr(self.model_class.__table__.columns, k, None)
            if column is not None:
                filter.append(column == v)
            else:
                split = k.rsplit('__', 1)
                if len(split) != 2:
                    continue
                else:
                    col = split[0]
                    op = split[1]
                column = getattr(self.model_class.__table__.columns, col, None)
                if column is None:
                    continue
                if isinstance(v, str):
                    if op == 'startswith':
                        filter.append(column.startswith(v))
                    elif op == 'endswith':
                        filter.append(column.endswith(v))
                    elif op == 'contains':
                        filter.append(column.contains(v))
                if op == 'lt':
                    filter.append(column < float(v))
                elif op == 'gt':
                    filter.append(column > float(v))
                elif op == 'lte':
                    filter.append(column <= float(v))
                elif op == 'gte':
                    filter.append(column >= float(v))
        return filter


class ModelResource:
    def __init__(self, sessionmaker=None):
        self.sessionmaker = sessionmaker

    @db_session
    def on_get(self, req, resp, dbsession, **kwargs):
        result = dbsession.query(self.model_class)
        result = result.filter_by(**kwargs)
        try:
            resp.body = result.one()
        except sqlalchemy.orm.exc.NoResultFound:
            raise falcon.HTTPNotFound

    @db_session
    def on_patch(self, req, resp, dbsession, **kwargs):
        result = dbsession.query(self.model_class)
        result = result.filter_by(**kwargs)
        try:
            resource = result.one()
        except sqlalchemy.orm.exc.NoResultFound:
            raise falcon.HTTPNotFound
        data = json.loads(req.bounded_stream.read().decode())
        for k, v in data.items():
            if hasattr(self.model_class.__table__.columns, k):
                setattr(resource, k, v)
            else:
                raise falcon.HTTPBadRequest(
                    description=('Resource does not contain field'
                                 '"{}"'.format(k)))
        dbsession.commit()
