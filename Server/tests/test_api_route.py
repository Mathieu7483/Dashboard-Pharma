import unittest
import json
import uuid
import sys
import os
from flask_jwt_extended import create_access_token

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from database.data_manager import db
from models.user import UserModel
from models.product import ProductModel
from models.client import ClientModel
from models.doctor import DoctorModel

app = create_app()


class TestAPIRoutes(unittest.TestCase):
    """Test suite for API routes."""

    @classmethod
    def setUpClass(cls):
        cls.app = app
        cls.app.config['TESTING'] = True
        cls.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    def setUp(self):
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        
        db.create_all()

        from services.facade import FacadeService
        self.facade = FacadeService()
        
        self.counter = 0
        
        # --- UPDATE: Added first_name, last_name, address fields to User creation ---
        admin_user = self.facade.create_user(
            username="admin_test",
            email="admin@test.com",
            password="Admin123!",
            first_name="Boss",
            last_name="Admin",
            address="Admin Tower",
            is_admin=True
        )
        self.admin_user_id = str(admin_user.id)
        
        employee_user = self.facade.create_user(
            username="employee_test",
            email="employee@test.com",
            password="Employee123!",
            first_name="Work",
            last_name="Employee",
            address="Workplace 1",
            is_admin=False
        )
        self.employee_user_id = str(employee_user.id)
        
        user_to_delete = self.facade.create_user(
            username='delete_me',
            email='delete@pharma.com',
            password='securepass',
            first_name="Delete",
            last_name="Me",
            address="Nowhere",
            is_admin=False
        )
        self.user_to_delete_id = str(user_to_delete.id)

        self.admin_token = create_access_token(
            identity=self.admin_user_id,
            additional_claims={'is_admin': True}
        )
        self.employee_token = create_access_token(
            identity=self.employee_user_id,
            additional_claims={'is_admin': False}
        )

        test_client_obj = self.facade.create_client(
            first_name="Client", 
            last_name="Test", 
            email="client@test.com",
            address="Test Street", 
            user_id=self.admin_user_id
        )
        self.test_client_id = str(test_client_obj.id)

        test_doctor = self.facade.create_doctor(
            first_name="Dr.", 
            last_name="House",
            email="dr.house@test.com",
            address="123 Medical Street",
            specialty="Diagnostician", 
            phone="9876543210", 
            user_id=self.admin_user_id
        )
        self.test_doctor_id = str(test_doctor.id)

        product_to_test = self.facade.create_product(
            name=self.get_unique_name('GenericProduct'),
            active_ingredient='Paracetamol',
            dosage='500mg',
            stock=100,
            price=10.00,
            is_prescription_only=False,
            user_id=self.admin_user_id
        )
        self.product_to_test_id = str(product_to_test.id)
        self.product_to_test_initial_stock = product_to_test.stock

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def get_unique_name(self, base_name):
        self.counter += 1
        return f"{base_name}_{self.counter}_{uuid.uuid4().hex[:6]}"

    def create_product_for_test(self, base_name, stock, rx_required=False):
        product = self.facade.create_product(
            name=self.get_unique_name(base_name),
            active_ingredient='Generic',
            dosage='100mg',
            stock=stock,
            price=10.00,
            is_prescription_only=rx_required,
            user_id=self.admin_user_id
        )
        if product is None:
            raise Exception("Product creation failed")
        return str(product.id), product.stock

    def get_auth_header(self, token):
        return {'Authorization': f'Bearer {token}'}

    # ==================== PRODUCTS ====================

    def test_01_product_get_all(self):
        """GET /products/ - Retrieve all products."""
        response = self.client.get('/products/',
            headers=self.get_auth_header(self.employee_token))
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.get_json(), list)

    def test_02_product_get_by_id(self):
        """GET /products/<id> - Retrieve product by ID."""
        response = self.client.get(f'/products/{self.product_to_test_id}',
            headers=self.get_auth_header(self.employee_token))
        self.assertEqual(response.status_code, 200)

    def test_03_product_get_nonexistent(self):
        """GET /products/<id> - Nonexistent product returns 404."""
        response = self.client.get(f'/products/{uuid.uuid4()}',
            headers=self.get_auth_header(self.employee_token))
        self.assertEqual(response.status_code, 404)

    def test_04_product_create_by_admin(self):
        """POST /products/ - Admin can create a product."""
        product_data = {
            'name': self.get_unique_name('AdminProduct'),
            'active_ingredient': 'Ibuprofen',
            'dosage': '400mg',
            'stock': 50,
            'price': 15.99,
            'is_prescription_only': False
        }
        response = self.client.post('/products/',
            headers=self.get_auth_header(self.admin_token),
            data=json.dumps(product_data),
            content_type='application/json')
        self.assertIn(response.status_code, [200, 201])

    def test_05_product_create_by_employee_forbidden(self):
        """POST /products/ - Employee cannot create a product."""
        product_data = {
            'name': self.get_unique_name('EmployeeProduct'),
            'active_ingredient': 'Test',
            'dosage': '100mg',
            'stock': 10,
            'price': 5.00,
            'is_prescription_only': False
        }
        response = self.client.post('/products/',
            headers=self.get_auth_header(self.employee_token),
            data=json.dumps(product_data),
            content_type='application/json')
        self.assertEqual(response.status_code, 403)

    def test_06_product_update_by_admin(self):
        """PUT /products/<id> - Admin can update a product."""
        response = self.client.put(f'/products/{self.product_to_test_id}',
            headers=self.get_auth_header(self.admin_token),
            data=json.dumps({'price': 99.99, 'stock': 55}),
            content_type='application/json')
        self.assertIn(response.status_code, [200, 204])

    def test_07_product_update_by_employee_forbidden(self):
        """PUT /products/<id> - Employee cannot update a product."""
        response = self.client.put(f'/products/{self.product_to_test_id}',
            headers=self.get_auth_header(self.employee_token),
            data=json.dumps({'price': 99.99}),
            content_type='application/json')
        self.assertEqual(response.status_code, 403)

    def test_08_product_delete_by_admin(self):
        """DELETE /products/<id> - Admin can delete a product."""
        product_id, _ = self.create_product_for_test('ToDelete', 10)
        response = self.client.delete(f'/products/{product_id}',
            headers=self.get_auth_header(self.admin_token))
        self.assertIn(response.status_code, [200, 204])

    def test_09_product_delete_by_employee_forbidden(self):
        """DELETE /products/<id> - Employee cannot delete a product."""
        response = self.client.delete(f'/products/{self.product_to_test_id}',
            headers=self.get_auth_header(self.employee_token))
        self.assertEqual(response.status_code, 403)

    # ==================== SALES ====================

    def test_10_sales_get_all(self):
        """GET /sales/ - Retrieve all sales."""
        response = self.client.get('/sales/',
            headers=self.get_auth_header(self.employee_token))
        self.assertEqual(response.status_code, 200)

    def test_11_sale_create_success(self):
        """POST /sales/ - Multi-item sale and stock check."""
        
        # Product 1: Non-prescription, initial stock = 100
        product_1_id = self.product_to_test_id
        product_1_initial_stock = self.facade.get_product_by_id(product_1_id).stock
        qty_1 = 2
        price_1 = self.facade.get_product_by_id(product_1_id).price

        # Product 2: Prescription required, initial stock = 50
        product_2_id, product_2_initial_stock = self.create_product_for_test(
             'RxProduct', 50, rx_required=True)
        qty_2 = 1
        price_2 = self.facade.get_product_by_id(product_2_id).price
        
        expected_total = (qty_1 * price_1) + (qty_2 * price_2)
        
        # 1. CORRECT PAYLOAD (based on sale_input_model)
        correct_payload = {
            "client_id": self.test_client_id, 
            "doctor_id": self.test_doctor_id,
            "items": [
                { "product_id": product_1_id, "quantity": qty_1 }, 
                { "product_id": product_2_id, "quantity": qty_2 }
            ]
        }
        
        # 2. SEND REQUEST
        response = self.client.post(
            '/sales/', 
            json=correct_payload, 
            headers=self.get_auth_header(self.admin_token)
        )
        
        self.assertEqual(response.status_code, 201, f"Response error: {response.get_json()}")

        # 3. CHECK TRANSACTION SAVED IN DB
        data = response.get_json()
        self.assertIn('id', data)
        self.assertIn('total_amount', data)
        self.assertIsInstance(data['items'], list)
        self.assertEqual(len(data['items']), 2)
        self.assertAlmostEqual(data['total_amount'], expected_total)
        
        # 4. CHECK STOCK DECREMENT
        product_1_after_sale = self.facade.get_product_by_id(product_1_id)
        product_2_after_sale = self.facade.get_product_by_id(product_2_id)
        
        self.assertEqual(product_1_after_sale.stock, product_1_initial_stock - qty_1)
        self.assertEqual(product_2_after_sale.stock, product_2_initial_stock - qty_2)


    def test_11b_sale_create_insufficient_stock_error(self):
        """POST /sales/ - Sale with insufficient stock returns 400."""
        product_id, _ = self.create_product_for_test('LowStock', 5)
        
        low_stock_payload = {
            "client_id": self.test_client_id,
            "doctor_id": self.test_doctor_id,
            "items": [
                { "product_id": product_id, "quantity": 10 } # 10 > 5
            ]
        }
        
        response = self.client.post(
            '/sales/', 
            json=low_stock_payload, 
            headers=self.get_auth_header(self.admin_token)
        )
        
        self.assertEqual(response.status_code, 400)
        self.assertIn("Insufficient stock", response.get_json().get('message'))


    def test_11c_sale_create_prescription_required_error(self):
        """POST /sales/ - Sale without doctor for RX product returns 400."""
        product_3_id, _ = self.create_product_for_test('RxOnly', 10, rx_required=True)
        
        no_doctor_payload = {
            "client_id": self.test_client_id,
            "items": [
                { "product_id": product_3_id, "quantity": 1 }
            ]
        }
        
        response = self.client.post(
            '/sales/', 
            json=no_doctor_payload, 
            headers=self.get_auth_header(self.admin_token)
        )
        
        self.assertEqual(response.status_code, 400)
        self.assertIn("Prescription is required", response.get_json().get('message'))


    # ==================== USERS ====================

    def test_12_user_get_all(self):
        """GET /users/ - Retrieve all users."""
        response = self.client.get('/users/',
            headers=self.get_auth_header(self.admin_token))
        self.assertEqual(response.status_code, 200)

    def test_13_user_get_all_by_employee(self):
        """GET /users/ - Employee can read users."""
        response = self.client.get('/users/',
            headers=self.get_auth_header(self.employee_token))
        self.assertEqual(response.status_code, 200)

    def test_14_user_delete_by_employee_forbidden(self):
        """DELETE /users/<id> - Employee cannot delete a user."""
        response = self.client.delete(f'/users/{self.user_to_delete_id}',
            headers=self.get_auth_header(self.employee_token))
        self.assertEqual(response.status_code, 403)

    def test_15_user_delete_by_admin(self):
        """DELETE /users/<id> - Admin can delete a user."""
        response = self.client.delete(f'/users/{self.user_to_delete_id}',
            headers=self.get_auth_header(self.admin_token))
        self.assertIn(response.status_code, [200, 204])

    def test_16_user_cannot_delete_self(self):
        """DELETE /users/<id> - User cannot delete themselves."""
        response = self.client.delete(f'/users/{self.admin_user_id}',
            headers=self.get_auth_header(self.admin_token))
        self.assertIn(response.status_code, [400, 403])

    # ==================== CLIENTS ====================

    def test_17_client_get_all(self):
        """GET /clients/ - Retrieve all clients."""
        response = self.client.get('/clients/',
            headers=self.get_auth_header(self.employee_token))
        self.assertEqual(response.status_code, 200)

    def test_18_client_get_by_id(self):
        """GET /clients/<id> - Retrieve client by ID."""
        response = self.client.get(f'/clients/{self.test_client_id}',
            headers=self.get_auth_header(self.employee_token))
        self.assertEqual(response.status_code, 200)

    def test_19_client_get_nonexistent(self):
        """GET /clients/<id> - Nonexistent client returns 404."""
        response = self.client.get(f'/clients/{uuid.uuid4()}',
            headers=self.get_auth_header(self.employee_token))
        self.assertEqual(response.status_code, 404)

    def test_20_client_create(self):
        """POST /clients/ - Create a client."""
        client_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': f'john.{uuid.uuid4().hex[:6]}@test.com',
            'address': '123 Test Street'
        }
        response = self.client.post('/clients/',
            headers=self.get_auth_header(self.employee_token),
            data=json.dumps(client_data),
            content_type='application/json')
        self.assertIn(response.status_code, [200, 201])

    def test_21_client_update_by_admin(self):
        """PUT /clients/<id> - Admin can update a client."""
        response = self.client.put(f'/clients/{self.test_client_id}',
            headers=self.get_auth_header(self.admin_token),
            data=json.dumps({'first_name': 'Updated'}),
            content_type='application/json')
        self.assertIn(response.status_code, [200, 204])

    def test_22_client_update_by_employee_forbidden(self):
        """PUT /clients/<id> - Employee cannot update a client."""
        response = self.client.put(f'/clients/{self.test_client_id}',
            headers=self.get_auth_header(self.employee_token),
            data=json.dumps({'first_name': 'Updated'}),
            content_type='application/json')
        self.assertEqual(response.status_code, 403)

    def test_23_client_delete_by_admin(self):
        """DELETE /clients/<id> - Admin can delete a client."""
        new_client = self.facade.create_client(
            first_name="ToDelete", last_name="Client", 
            email=f"del.{uuid.uuid4().hex[:6]}@test.com",
            address="Delete Street", user_id=self.admin_user_id)
        response = self.client.delete(f'/clients/{new_client.id}',
            headers=self.get_auth_header(self.admin_token))
        self.assertIn(response.status_code, [200, 204])

    def test_24_client_delete_by_employee_forbidden(self):
        """DELETE /clients/<id> - Employee cannot delete a client."""
        response = self.client.delete(f'/clients/{self.test_client_id}',
            headers=self.get_auth_header(self.employee_token))
        self.assertEqual(response.status_code, 403)

    # ==================== DOCTORS ====================

    def test_25_doctor_get_all(self):
        """GET /doctors/ - Retrieve all doctors."""
        response = self.client.get('/doctors/',
            headers=self.get_auth_header(self.employee_token))
        self.assertEqual(response.status_code, 200)

    def test_26_doctor_get_by_id(self):
        """GET /doctors/<id> - Retrieve doctor by ID."""
        response = self.client.get(f'/doctors/{self.test_doctor_id}',
            headers=self.get_auth_header(self.employee_token))
        self.assertEqual(response.status_code, 200)

    def test_27_doctor_get_nonexistent(self):
        """GET /doctors/<id> - Nonexistent doctor returns 404."""
        response = self.client.get(f'/doctors/{uuid.uuid4()}',
            headers=self.get_auth_header(self.employee_token))
        self.assertEqual(response.status_code, 404)

    def test_28_doctor_create(self):
        """POST /doctors/ - Create a doctor."""
        doctor_data = {
            'first_name': 'Dr. New',
            'last_name': 'Doctor',
            'email': f'dr.{uuid.uuid4().hex[:6]}@test.com',
            'address': '789 Medical Ave',
            'specialty': 'General Practitioner',
            'phone': '1234567890'
        }
        response = self.client.post('/doctors/',
            headers=self.get_auth_header(self.employee_token),
            data=json.dumps(doctor_data),
            content_type='application/json')
        self.assertIn(response.status_code, [200, 201])

    def test_29_doctor_update(self):
        """PUT /doctors/<id> - Update doctor info."""
        response = self.client.put(f'/doctors/{self.test_doctor_id}',
            headers=self.get_auth_header(self.admin_token),
            data=json.dumps({'specialty': 'Cardiologist'}),
            content_type='application/json')
        self.assertIn(response.status_code, [200, 204])

    def test_30_doctor_delete_by_admin(self):
        """DELETE /doctors/<id> - Admin can delete a doctor."""
        new_doctor = self.facade.create_doctor(
            first_name="ToDelete", last_name="Doctor",
            email=f"del.{uuid.uuid4().hex[:6]}@test.com",
            address="Delete Street", specialty="Surgeon", 
            phone="0000000000", user_id=self.admin_user_id)
        response = self.client.delete(f'/doctors/{new_doctor.id}',
            headers=self.get_auth_header(self.admin_token))
        self.assertIn(response.status_code, [200, 204])

    # ==================== AUTH - Access Control ====================

    def test_31_access_without_token(self):
        """Access without JWT token returns 401."""
        response = self.client.get('/products/')
        self.assertEqual(response.status_code, 401)

    def test_32_access_with_invalid_token(self):
        """Access with invalid token returns 401/422."""
        response = self.client.get('/products/',
            headers={'Authorization': 'Bearer invalid_token'})
        self.assertIn(response.status_code, [401, 422])


class TestAuthAPI(unittest.TestCase):
    """Tests for authentication API (/auth/login, /auth/register)."""

    @classmethod
    def setUpClass(cls):
        cls.app = app
        cls.app.config['TESTING'] = True

    def setUp(self):
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        
        db.create_all()

        from services.facade import FacadeService
        self.facade = FacadeService()
        self.counter = 0
        
        # NOTE: Added first_name, last_name, address fields to stay consistent with FacadeService
        self.test_user = self.facade.create_user(
            username="login_test",
            email="login@test.com",
            password="TestPass123!",
            first_name="Test",
            last_name="Login",
            address="Auth Address",
            is_admin=False
        )
        self.test_user_id = str(self.test_user.id)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def get_unique_email(self):
        self.counter += 1
        return f"user_{self.counter}_{uuid.uuid4().hex[:6]}@test.com"

    # ==================== LOGIN ====================

    def test_01_login_success(self):
        """POST /auth/login - Successful login returns access_token."""
        response = self.client.post('/auth/login',
            data=json.dumps({'username': 'login_test', 'password': 'TestPass123!'}),
            content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('access_token', data)
        self.assertEqual(data['token_type'], 'Bearer')
        self.assertIn('user_id', data)
        self.assertIn('is_admin', data)
        self.assertEqual(data['is_admin'], False)

    def test_02_login_wrong_password(self):
        """POST /auth/login - Wrong password returns 401."""
        response = self.client.post('/auth/login',
            data=json.dumps({'username': 'login_test', 'password': 'WrongPassword!'}),
            content_type='application/json')
        self.assertEqual(response.status_code, 401)

    def test_03_login_nonexistent_user(self):
        """POST /auth/login - Nonexistent user returns 401."""
        response = self.client.post('/auth/login',
            data=json.dumps({'username': 'nonexistent', 'password': 'SomePassword!'}),
            content_type='application/json')
        self.assertEqual(response.status_code, 401)

    # ==================== REGISTER ====================

    def test_04_register_success(self):
        """POST /auth/register - Successful registration returns 201."""
        response = self.client.post('/auth/register',
            data=json.dumps({
                'username': 'new_user',
                'email': self.get_unique_email(),
                'password': 'NewPass123!'
            }),
            content_type='application/json')
        
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn('user_id', data)

    def test_05_register_duplicate_username(self):
        """POST /auth/register - Duplicate username returns 409 or 500."""
        response = self.client.post('/auth/register',
            data=json.dumps({
                'username': 'login_test',
                'email': self.get_unique_email(),
                'password': 'NewPass123!'
            }),
            content_type='application/json')
        
        self.assertIn(response.status_code, [409, 500])

    def test_06_register_duplicate_email(self):
        """POST /auth/register - Duplicate email returns 409 or 500."""
        response = self.client.post('/auth/register',
            data=json.dumps({
                'username': 'different_user',
                'email': 'login@test.com',
                'password': 'NewPass123!'
            }),
            content_type='application/json')
        
        self.assertIn(response.status_code, [409, 500])

    def test_07_register_missing_username(self):
        """POST /auth/register - Missing username returns 400."""
        response = self.client.post('/auth/register',
            data=json.dumps({
                'email': self.get_unique_email(),
                'password': 'NewPass123!'
            }),
            content_type='application/json')
        
        self.assertEqual(response.status_code, 400)

    def test_08_register_missing_email(self):
        """POST /auth/register - Missing email returns 400."""
        response = self.client.post('/auth/register',
            data=json.dumps({
                'username': 'some_user',
                'password': 'NewPass123!'
            }),
            content_type='application/json')
        
        self.assertEqual(response.status_code, 400)

    def test_09_register_missing_password(self):
        """POST /auth/register - Missing password returns 400."""
        response = self.client.post('/auth/register',
            data=json.dumps({
                'username': 'some_user',
                'email': self.get_unique_email()
            }),
            content_type='application/json')
        
        self.assertEqual(response.status_code, 400)

    def test_10_register_creates_non_admin_user(self):
        """POST /auth/register - New user is non-admin by default."""
        email = self.get_unique_email()
        
        register_response = self.client.post('/auth/register',
            data=json.dumps({
                'username': 'regular_user',
                'email': email,
                'password': 'RegularPass123!'
            }),
            content_type='application/json')
        
        self.assertEqual(register_response.status_code, 201)
        
        login_response = self.client.post('/auth/login',
            data=json.dumps({
                'username': 'regular_user',
                'password': 'RegularPass123!'
            }),
            content_type='application/json')
        
        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(login_response.get_json()['is_admin'], False)


if __name__ == '__main__':
    unittest.main(verbosity=2)