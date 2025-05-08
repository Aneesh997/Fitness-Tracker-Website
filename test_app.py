import pytest
from app import app
import mysql.connector
from unittest.mock import patch, MagicMock

# Test Setup
@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        with app.app_context():
            yield client

@pytest.fixture
def auth_client(client):
    """Mock authenticated client"""
    with patch('app.create_connection') as mock_conn:
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {'username': 'testuser'}
        mock_conn.return_value.cursor.return_value = mock_cursor
        
        # Perform login (mocked)
        response = client.post('/login', 
            json={"username": "testuser", "password": "testpass"}
        )
        assert response.status_code == 200
        yield client

# Tests
def test_login_page(client):
    """Test login page loads"""
    response = client.get('/login')
    assert response.status_code == 200
    assert b'Sign in' in response.data

def test_successful_login(client):
    """Test valid login credentials"""
    with patch('app.create_connection') as mock_conn:
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {'username': 'validuser'}
        mock_conn.return_value.cursor.return_value = mock_cursor
        
        response = client.post('/login', 
            json={"username": "validuser", "password": "validpass"}
        )
        assert response.status_code == 200
        assert response.json['success'] is True
        assert 'redirect' in response.json

def test_failed_login(client):
    """Test invalid login credentials"""
    with patch('app.create_connection') as mock_conn:
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.return_value.cursor.return_value = mock_cursor
        
        response = client.post('/login', 
            json={"username": "invalid", "password": "wrong"}
        )
        assert response.status_code == 401
        assert response.json['success'] is False
        assert 'Incorrect' in response.json['message']

def test_database_error_handling(client):
    """Test database error responses"""
    with patch('app.create_connection', side_effect=mysql.connector.Error("DB error")):
        response = client.post('/login',
            json={"username": "test", "password": "test"}
        )
        assert response.status_code == 500
        assert response.json['success'] is False
        assert 'Database' in response.json['message']

def test_missing_credentials(client):
    """Test missing username/password"""
    response = client.post('/login', json={})
    assert response.status_code == 400
    assert response.json['success'] is False
    assert 'required' in response.json['message']

def test_protected_routes(auth_client):
    """Test access to protected routes when authenticated"""
    routes_to_test = [
        '/home',
        '/courses', 
        '/pricing',
        '/tracking',
        '/sleep',
        '/workout',
        '/diet',
        '/contact'
    ]
    
    for route in routes_to_test:
        response = auth_client.get(route)
        assert response.status_code == 200, f"Failed to access {route}"

def test_logout(auth_client):
    """Test logout functionality"""
    response = auth_client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b'Sign in' in response.data