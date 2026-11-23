"""Regression tests for the security hardening (config, registration, admin seeding)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from config import DevelopmentConfig, ProductionConfig, TestingConfig
from database.data_manager import db
from models.user import UserModel
from utils import seeder


class TestRegistration(unittest.TestCase):

    def _client(self, allow):
        class Cfg(TestingConfig):
            ALLOW_PUBLIC_REGISTRATION = allow
        app = create_app(Cfg)
        ctx = app.app_context()
        ctx.push()
        db.create_all()
        self.addCleanup(ctx.pop)
        self.addCleanup(db.drop_all)
        return app.test_client()

    payload = {'username': 'newbie', 'email': 'newbie@test.fr', 'password': 'Str0ng!pass'}

    def test_registration_closed_by_default(self):
        self.assertEqual(self._client(False).post('/auth/register', json=self.payload).status_code, 403)

    def test_registration_open_when_enabled(self):
        self.assertEqual(self._client(True).post('/auth/register', json=self.payload).status_code, 201)


class TestAuthStatusCodes(unittest.TestCase):
    """With DEBUG/TESTING off (as in production) auth errors must stay 401/422, not 500."""

    def test_missing_and_invalid_token(self):
        class Cfg(TestingConfig):
            TESTING = False
        app = create_app(Cfg)
        with app.app_context():
            db.create_all()
            c = app.test_client()
            self.assertEqual(c.get('/clients/').status_code, 401)
            self.assertEqual(c.get('/clients/', headers={'Authorization': 'Bearer abc'}).status_code, 422)
            db.drop_all()


class TestProductionConfig(unittest.TestCase):

    def _validate(self, **keys):
        class Cfg(ProductionConfig):
            SECRET_KEY = keys.get('secret')
            JWT_SECRET_KEY = keys.get('jwt')
        Cfg.validate()

    def test_refuses_missing_secrets(self):
        with self.assertRaises(RuntimeError):
            self._validate()

    def test_refuses_short_secrets(self):
        with self.assertRaises(RuntimeError):
            self._validate(secret='short', jwt='short')

    def test_accepts_strong_secrets(self):
        self._validate(secret='a' * 64, jwt='b' * 64)

    def test_production_never_debug(self):
        self.assertFalse(ProductionConfig.DEBUG)

    def test_no_hardcoded_secret_in_source(self):
        src = open(os.path.join(os.path.dirname(__file__), '..', 'config.py'), encoding='utf-8').read()
        self.assertNotIn('dev_mode', src)
        self.assertNotIn('dev-secret-key', src)


class TestAdminSeeding(unittest.TestCase):

    def setUp(self):
        self.app = create_app(TestingConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self._env = {k: os.environ.get(k) for k in ('APP_ENV', 'ADMIN_PASSWORD')}
        os.environ.pop('ADMIN_PASSWORD', None)

    def tearDown(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_existing_admin_password_is_not_reset(self):
        admin = seeder._seed_admin()
        before = admin.password_hash
        seeder._seed_admin()
        self.assertEqual(UserModel.query.filter_by(username=admin.username).first().password_hash, before)

    def test_production_requires_admin_password(self):
        os.environ['APP_ENV'] = 'production'
        self.assertIsNone(seeder._seed_admin())
        self.assertEqual(UserModel.query.count(), 0)

    def test_production_uses_given_password(self):
        os.environ['APP_ENV'] = 'production'
        os.environ['ADMIN_PASSWORD'] = 'Given-Pass-123!'
        admin = seeder._seed_admin()
        self.assertTrue(admin.check_password('Given-Pass-123!'))

    def test_no_default_password_anywhere(self):
        self.assertFalse(hasattr(DevelopmentConfig, 'ADMIN_PASSWORD'))
        src = open(seeder.__file__, encoding='utf-8').read()
        self.assertNotIn('Admin@1234', src)


if __name__ == '__main__':
    unittest.main()
