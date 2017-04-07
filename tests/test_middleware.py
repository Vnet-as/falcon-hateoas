import falcon
from falcon.testing import TestCase, SimpleTestResource

import decimal
import datetime
from unittest import mock

from falcon_hateoas.middleware import JsonMiddleware


class TestJsonMiddleware(TestCase):

    def setUp(self):
        self.api = falcon.API(middleware=JsonMiddleware())

    def test_basic_data(self):
        self.api.add_route('/', SimpleTestResource(body={'a': 1}))
        resp = self.simulate_get()
        assert resp.json == {'a': 1}

    @mock.patch('sqlalchemy.ext.declarative.DeclarativeMeta')
    def test_alchemy_model(self, alchemy_mock):
        testdate = datetime.datetime.today()
        alchemy_mock.__table__ = mock.Mock()
        alchemy_mock.__table__.columns = {
            'testdate': testdate,
            'testdecimal': decimal.Decimal('10.1'),
            'teststr': 'teststring'
        }
        alchemy_mock.__dict__.update(alchemy_mock.__table__.columns)

        self.api.add_route('/', SimpleTestResource(body=alchemy_mock))
        resp = self.simulate_get()
        assert resp.json == {
                'testdate': testdate.isoformat(),
                'testdecimal': 10.1,
                'teststr': 'teststring'
        }
