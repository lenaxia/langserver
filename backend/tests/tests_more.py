import unittest
import json
from langserver.langserver import app, db, APIToken

class FlaskAppTestCase(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
        with app.app_context():
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_add_token_success(self):
        response = self.app.post('/add-token/testuser')
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertIn('token', data)

    def test_add_token_invalid_id(self):
        response = self.app.post('/add-token/invalid#id')
        self.assertEqual(response.status_code, 400)

    def test_list_tokens_empty(self):
        response = self.app.get('/list-tokens')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 0)

    def test_list_tokens_non_empty(self):
        self.app.post('/add-token/testuser')
        response = self.app.get('/list-tokens')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)

    def test_revoke_token_valid(self):
        add_response = self.app.post('/add-token/testuser')
        token_data = json.loads(add_response.data)
        revoke_response = self.app.post('/revoke-token', json={'token': token_data['token']})
        self.assertEqual(revoke_response.status_code, 200)

    def test_revoke_token_invalid(self):
        response = self.app.post('/revoke-token', json={'token': 'nonexistent'})
        self.assertEqual(response.status_code, 404)

    def test_regenerate_token_valid(self):
        self.app.post('/add-token/testuser')
        response = self.app.post('/regenerate-token', json={'id': 'testuser'})
        self.assertEqual(response.status_code, 200)

    def test_regenerate_token_invalid(self):
        response = self.app.post('/regenerate-token', json={'id': 'nonexistent'})
        self.assertEqual(response.status_code, 404)

    def test_generate_speech_valid(self):
        # Assuming 'your-token' is a valid token
        self.app.post('/add-token/testuser')
        response = self.app.post('/generate-speech', headers={'Authorization': 'your-token'}, json={'text': 'hello', 'language': 'en', 'translations': ['zh-TW']})
        self.assertEqual(response.status_code, 200)

    def test_generate_speech_invalid_json(self):
        # Assuming 'your-token' is a valid token
        self.app.post('/add-token/testuser')
        response = self.app.post('/generate-speech', headers={'Authorization': 'your-token'}, json={'invalid': 'data'})
        self.assertEqual(response.status_code, 400)

    # Additional tests can be added here for other scenarios

if __name__ == '__main__':
    unittest.main()

