import unittest
import json
from langserver.langserver import app, db

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

    def test_add_token(self):
        response = self.app.post('/add-token/testuser')
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertIn('token', data)

    def test_list_tokens(self):
        self.app.post('/add-token/testuser')
        response = self.app.get('/list-tokens')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)

    def test_revoke_token(self):
        add_response = self.app.post('/add-token/testuser')
        token_data = json.loads(add_response.data)
        revoke_response = self.app.post('/revoke-token', json={'token': token_data['token']})
        self.assertEqual(revoke_response.status_code, 200)

    def test_regenerate_token(self):
        self.app.post('/add-token/testuser')
        response = self.app.post('/regenerate-token', json={'id': 'testuser'})
        self.assertEqual(response.status_code, 200)

    def test_generate_speech(self):
        self.app.post('/add-token/testuser')
        response = self.app.post('/generate-speech', headers={'Authorization': 'your-token'}, json={'text': 'hello', 'language': 'en', 'translations': ['zh-TW']})
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()

