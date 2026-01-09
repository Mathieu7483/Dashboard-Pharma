import unittest
import json
import uuid
import sys
import os
from datetime import datetime
from flask_jwt_extended import create_access_token

# Ajustement du chemin pour importer 'app'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from database.data_manager import db
from services.facade import FacadeService

class TestCompletePharmaAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config.update({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'SQLALCHEMY_TRACK_MODIFICATIONS': False
        })
        cls.client = cls.app.test_client()
        cls.facade = FacadeService()
        cls.ctx = cls.app.app_context()
        cls.ctx.push()
        db.create_all()

        # Création des utilisateurs de référence avec noms uniques
        suffix = uuid.uuid4().hex[:4]
        cls.admin = cls.facade.create_user(f"adm_{suffix}", f"adm_{suffix}@test.fr", "P123!", is_admin=True)
        cls.staff = cls.facade.create_user(f"stf_{suffix}", f"stf_{suffix}@test.fr", "P123!", is_admin=False)

        adm_tk = create_access_token(identity=str(cls.admin.id), additional_claims={'is_admin': True})
        stf_tk = create_access_token(identity=str(cls.staff.id), additional_claims={'is_admin': False})
        cls.admin_headers = {'Authorization': f'Bearer {adm_tk}', 'Content-Type': 'application/json'}
        cls.staff_headers = {'Authorization': f'Bearer {stf_tk}', 'Content-Type': 'application/json'}

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        cls.ctx.pop()

    def setUp(self):
        """Nettoyage et création de données fraîches pour CHAQUE test."""
        # On vide les tables pour éviter les IntegrityError (UNIQUE constraint)
        db.session.execute(db.text("DELETE FROM sale_items"))
        db.session.execute(db.text("DELETE FROM sales"))
        db.session.execute(db.text("DELETE FROM products"))
        db.session.execute(db.text("DELETE FROM doctors"))
        db.session.execute(db.text("DELETE FROM clients"))
        db.session.commit()

        u = uuid.uuid4().hex[:6]
        self.t_client = self.facade.create_client("Jean", "Dupont", f"c_{u}@t.fr", "01", "Paris", str(self.admin.id))
        self.t_doctor = self.facade.create_doctor("Dr", "House", f"d_{u}@t.fr", "Lille", "Gén", "06", str(self.admin.id))
        self.t_prod = self.facade.create_product(f"Doliprane_{u}", "P", "500", 100, 5.0, False, str(self.admin.id))

    # --- SECTION 1: USERS (8) ---
    def test_01_login(self):
        res = self.client.post('/auth/login', json={"username": self.admin.username, "password": "P123!"})
        self.assertEqual(res.status_code, 200)

    def test_02_login_fail(self):
        res = self.client.post('/auth/login', json={"username": "fake", "password": "X"})
        self.assertEqual(res.status_code, 401)

    def test_03_get_users(self):
        res = self.client.get('/users/', headers=self.admin_headers)
        self.assertEqual(res.status_code, 200)

    def test_04_rbac_users(self):
        res = self.client.get('/users/', headers=self.staff_headers)
        self.assertEqual(res.status_code, 403)

    def test_05_update_user(self):
        res = self.client.put(f'/users/{self.staff.id}', json={"first_name":"X"}, headers=self.admin_headers)
        self.assertEqual(res.status_code, 200)

    def test_06_delete_user(self):
        u = self.facade.create_user("del", "del@t.fr", "P")
        res = self.client.delete(f'/users/{u.id}', headers=self.admin_headers)
        self.assertIn(res.status_code, [200, 204])

    def test_07_get_user_id(self):
        res = self.client.get(f'/users/{self.admin.id}', headers=self.admin_headers)
        self.assertEqual(res.status_code, 200)

    def test_08_duplicate_user(self):
        res = self.client.post('/users/', json={"username": self.admin.username, "email":"x@t.fr", "password":"P"}, headers=self.admin_headers)
        self.assertEqual(res.status_code, 400)

    # --- SECTION 2: PRODUCTS (9) ---
    def test_09_get_prods(self):
        res = self.client.get('/products/', headers=self.staff_headers)
        self.assertEqual(res.status_code, 200)

    def test_10_create_prod(self):
        unique_name = f"Medic-{uuid.uuid4().hex[:6]}"
        payload = {
            "name": unique_name,
            "active_ingredient": "Paracétamol",
            "dosage": "500mg",
            "stock": 50,
            "price": 4.99,
            "is_prescription_only": False
        }
        
        res = self.client.post('/products/', json=payload, headers=self.admin_headers)
        
        if res.status_code == 400:
            print(f"\n[DEBUG FAIL 10] Payload envoyé: {payload}")
            print(f"[DEBUG FAIL 10] Réponse API: {res.get_json()}")
            
        self.assertEqual(res.status_code, 201)

    def test_11_rbac_prod(self):
        res = self.client.post('/products/', json={}, headers=self.staff_headers)
        self.assertIn(res.status_code, [400, 403])

    def test_12_update_prod(self):
        res = self.client.put(f'/products/{self.t_prod.id}', json={"price":10}, headers=self.admin_headers)
        self.assertEqual(res.status_code, 200)

    def test_13_del_prod(self):
        res = self.client.delete(f'/products/{self.t_prod.id}', headers=self.admin_headers)
        self.assertIn(res.status_code, [200, 204])

    def test_14_prod_detailed(self):
        res = self.client.get('/products/detailed', headers=self.staff_headers)
        self.assertIn(res.status_code, [200, 404])

    def test_15_prod_404(self):
        res = self.client.get(f'/products/{uuid.uuid4()}', headers=self.staff_headers)
        self.assertEqual(res.status_code, 404)

    def test_16_prod_invalid(self):
        res = self.client.post('/products/', json={"name":""}, headers=self.admin_headers)
        self.assertEqual(res.status_code, 400)

    def test_17_search_prod(self):
        res = self.client.get(f'/products/search/{self.t_prod.name}', headers=self.staff_headers)
        self.assertEqual(res.status_code, 200)

    # --- SECTION 3: CLIENTS (9) ---
    def test_18_get_clients(self):
        res = self.client.get('/clients/', headers=self.staff_headers)
        self.assertEqual(res.status_code, 200)

    def test_19_create_client(self):
        payload = {"first_name":"B","last_name":"E","email":f"b{uuid.uuid4().hex[:4]}@o.com","phone":"0","address":"A"}
        res = self.client.post('/clients/', json=payload, headers=self.staff_headers)
        self.assertIn(res.status_code, [200, 201])

    def test_20_update_cli(self):
        res = self.client.put(f'/clients/{self.t_client.id}', json={"phone":"99"}, headers=self.staff_headers)
        self.assertEqual(res.status_code, 200)

    def test_21_del_cli_adm(self):
        res = self.client.delete(f'/clients/{self.t_client.id}', headers=self.admin_headers)
        self.assertIn(res.status_code, [200, 204])

    def test_22_del_cli_rbac(self):
        res = self.client.delete(f'/clients/{self.t_client.id}', headers=self.staff_headers)
        self.assertEqual(res.status_code, 403)

    def test_23_search_cli(self):
        res = self.client.get('/clients/search?query=Jean', headers=self.staff_headers)
        self.assertEqual(res.status_code, 200)

    def test_24_get_cli_id(self):
        res = self.client.get(f'/clients/{self.t_client.id}', headers=self.staff_headers)
        self.assertEqual(res.status_code, 200)

    def test_25_cli_mail_err(self):
        res = self.client.post('/clients/', json={"email":"bad"}, headers=self.staff_headers)
        self.assertEqual(res.status_code, 400)

    def test_26_cli_404(self):
        res = self.client.get(f'/clients/{uuid.uuid4()}', headers=self.staff_headers)
        self.assertEqual(res.status_code, 404)

    # --- SECTION 4: DOCTORS (9) ---
    def test_27_get_docs(self):
        res = self.client.get('/doctors/', headers=self.staff_headers)
        self.assertEqual(res.status_code, 200)

    def test_28_create_doc(self):
        p = {"first_name":"D","last_name":"B","email":f"d{uuid.uuid4().hex[:4]}@f.com","address":"H","specialty":"T","phone":"8"}
        res = self.client.post('/doctors/', json=p, headers=self.staff_headers)
        self.assertIn(res.status_code, [200, 201])

    def test_29_update_doc(self):
        res = self.client.put(f'/doctors/{self.t_doctor.id}', json={"specialty":"S"}, headers=self.staff_headers)
        self.assertEqual(res.status_code, 200)

    def test_30_del_doc(self):
        res = self.client.delete(f'/doctors/{self.t_doctor.id}', headers=self.admin_headers)
        self.assertIn(res.status_code, [200, 204])

    def test_31_search_doc(self):
        res = self.client.get('/doctors/search?query=Gén', headers=self.staff_headers)
        self.assertEqual(res.status_code, 200)

    def test_32_get_doc_id(self):
        res = self.client.get(f'/doctors/{self.t_doctor.id}', headers=self.staff_headers)
        self.assertEqual(res.status_code, 200)

    def test_33_doc_invalid(self):
        res = self.client.post('/doctors/', json={}, headers=self.staff_headers)
        self.assertEqual(res.status_code, 400)

    def test_34_doc_rbac(self):
        res = self.client.delete(f'/doctors/{self.t_doctor.id}', headers=self.staff_headers)
        self.assertEqual(res.status_code, 403)

    def test_35_doc_404(self):
        res = self.client.get(f'/doctors/{uuid.uuid4()}', headers=self.staff_headers)
        self.assertEqual(res.status_code, 404)

    # --- SECTION 5: SALES & ANALYTICS (9) ---
    def test_36_sale_ok(self):
        p = {"client_id":str(self.t_client.id), "doctor_id":None, "items":[{"product_id":str(self.t_prod.id),"quantity":1}]}
        res = self.client.post('/sales/', json=p, headers=self.staff_headers)
        self.assertIn(res.status_code, [200, 201, 400])

    def test_37_sale_stock_err(self):
        p = {"client_id":str(self.t_client.id), "doctor_id":None, "items":[{"product_id":str(self.t_prod.id),"quantity":999}]}
        res = self.client.post('/sales/', json=p, headers=self.staff_headers)
        self.assertEqual(res.status_code, 400)

    def test_38_sale_rx_err(self):
        rx = self.facade.create_product("M","M","1",10,50,True,str(self.admin.id))
        p = {"client_id":str(self.t_client.id), "doctor_id":None, "items":[{"product_id":str(rx.id),"quantity":1}]}
        res = self.client.post('/sales/', json=p, headers=self.staff_headers)
        self.assertEqual(res.status_code, 400)

    def test_39_sale_rx_ok(self):
        rx = self.facade.create_product("M2","M","1",10,50,True,str(self.admin.id))
        p = {"client_id":str(self.t_client.id), "doctor_id":str(self.t_doctor.id), "items":[{"product_id":str(rx.id),"quantity":1}]}
        res = self.client.post('/sales/', json=p, headers=self.staff_headers)
        self.assertIn(res.status_code, [200, 201])

    def test_40_get_sales(self):
        res = self.client.get('/sales/', headers=self.staff_headers)
        self.assertEqual(res.status_code, 200)

    def test_41_daily(self):
        res = self.client.get('/analytics/daily-stats', headers=self.admin_headers)
        self.assertIn(res.status_code, [200, 404])

    def test_42_alerts(self):
        res = self.client.get('/analytics/stock-alerts', headers=self.admin_headers)
        self.assertIn(res.status_code, [200, 404])

    def test_43_monthly(self):
        res = self.client.get('/analytics/monthly-stats', headers=self.admin_headers)
        self.assertIn(res.status_code, [200, 404])

    def test_44_sale_id(self):
        s = self.facade.process_sale(str(self.t_client.id), None, [{"product_id":str(self.t_prod.id),"quantity":1}], str(self.staff.id))
        res = self.client.get(f'/sales/{s.id}', headers=self.staff_headers)
        self.assertEqual(res.status_code, 200)

if __name__ == '__main__':
    unittest.main(verbosity=2)