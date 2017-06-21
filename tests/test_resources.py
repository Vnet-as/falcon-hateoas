import pytest
import json
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.schema import Column
from sqlalchemy.types import Text, Integer
from falcon import testing, API
from falcon_hateoas import resources
from unittest import mock


@pytest.fixture
def sessionmaker():
    sm = mock.MagicMock()
    return sm


@pytest.fixture
def resource_mock(sessionmaker):
    res = resources.ModelResource(sessionmaker)
    filter_by = sessionmaker.return_value.query.return_value.filter_by
    one = filter_by.return_value.one
    one.side_effect = [json.dumps({'some': 'data'}), NoResultFound]
    res.model_class = mock.MagicMock()
    res.model_class.__table__ = mock.DEFAULT
    res.model_class.__table__.columns = mock.DEFAULT
    return res


@pytest.fixture
def collection_mock(sessionmaker):
    res = resources.ModelCollection(sessionmaker)
    query = sessionmaker.return_value.query
    offset = query.return_value.offset
    all = offset.return_value.all
    all.return_value = json.dumps({'some': 'data'})

    order_by = query.return_value.order_by
    limit = order_by.return_value.limit
    offset = limit.return_value.offset
    all = offset.return_value.all
    all.return_value = ''

    filter = query.return_value.filter
    offset = filter.return_value.offset
    all = offset.return_value.all
    all.return_value = ''

    res.model_class = mock.MagicMock()
    res.model_class.__table__ = mock.DEFAULT
    res.model_class.__table__.columns = mock.DEFAULT
    return res


@pytest.fixture
def app(resource_mock, collection_mock):
    app = API()
    app.add_route('/{res_id}', resource_mock)
    app.add_route('/', collection_mock)
    return app


class TestModelResource:
    def test_get(self, app):
        resp = testing.simulate_get(app, '/123')
        assert resp.json == {'some': 'data'}
        resp = testing.simulate_get(app, '/0')
        assert resp.status_code == 404
        resp = testing.simulate_post(app, '/123', body='somedata')
        assert resp.status_code == 405

    def test_patch(self, app):
        res = app._router.find('/123')[0]
        res.model_class.__table__.columns.some_str = str
        session = res.sessionmaker()
        res.sessionmaker.return_value.query.return_value.filter_by\
            .return_value.one.side_effect = None
        # res.sessionmaker.return_value.query.return_value.filter_by\
        #     .return_value.one.return_value = 123
        patch_data = {'some_str': 'thing'}
        resp = testing.simulate_patch(app, '/123', body=json.dumps(patch_data))
        assert resp.status_code == 200
        calls = [
            mock.call.query(res.model_class),
            mock.call.query().filter_by(res_id='123'),
            mock.call.query().filter_by().one(),
            mock.call.commit(),
            mock.call.close()
        ]
        assert session.mock_calls == calls


class TestModelCollection:
    def test_basic_test(self, app):
        resp = testing.simulate_get(app, '/')
        res = app._router.find('/')[0]
        session = res.sessionmaker()
        calls = [
            mock.call.query(res.model_class),
            mock.call.query(res.model_class).offset(0),
            mock.call.query(res.model_class).offset(0).all(),
            mock.call.close()
        ]
        assert session.mock_calls == calls
        assert resp.json == {'some': 'data'}

    def test_meta(self, app):
        params = {
            'limit': 10,
            'offset': 5,
            'order_by': 'some_col'
        }
        res = app._router.find('/')[0]
        session = res.sessionmaker()
        testing.simulate_get(app, '/', params=params)
        query = mock.call.query(res.model_class)
        calls = [
            query,
            query.order_by('some_col'),
            query.order_by('some_col').limit('10'),
            query.order_by('some_col').limit('10').offset('5'),
            query.order_by('some_col').limit('10').offset('5').all(),
            mock.call.close()
        ]
        assert session.mock_calls == calls

    def test_filter(self, app):
        params = {
            'some_col': 'some_val',
            'some_col__startswith': 'some',
            'some_col__endswith': 'val',
            'some_col__contains': '_',
            'some_num__lt': 6,
            'some_num__gt': 4,
            'some_num__lte': 5,
            'some_num__gte': 5,
            'fake_col__contains': 'x'
        }
        res = app._router.find('/')[0]
        session = res.sessionmaker()
        res.model_class.__table__.columns.some_col = Column(Text)
        res.model_class.__table__.columns.some_num = Column(Integer)
        testing.simulate_get(app, '/', params=params)
        query = mock.call.query(res.model_class)
        calls = [
            query,
            query.filter(*([mock.ANY])*8),
            query.filter().offset(0),
            query.filter().offset().all(),
            mock.call.close()
        ]
        assert session.mock_calls == calls

    def test_post(self, app):
        res = app._router.find('/')[0]
        res.model_class.__table__.columns.some_str = str
        session = res.sessionmaker()
        post_data = {
            'some_str': 'data',
            'some_int': 123
        }
        m = res.model_class.return_value
        p1 = mock.PropertyMock()
        setattr(type(m), 'some_str', p1)
        p2 = mock.PropertyMock()
        setattr(type(m), 'some_int', p2)
        m.encode.return_value = json.dumps(post_data).encode()
        rsp = testing.simulate_post(app, '/', body=json.dumps(post_data))
        assert rsp.status_code == 200
        assert res.model_class.called
        assert p1.mock_calls == [mock.call('data')]
        assert p2.mock_calls == []
        calls = [
            mock.call.add(res.model_class()),
            mock.call.commit(),
            mock.call.refresh(res.model_class()),
            mock.call.close()
        ]
        assert session.mock_calls == calls
        assert rsp.json == post_data
