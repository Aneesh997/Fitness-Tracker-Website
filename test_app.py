import pytest
from app import app
import mysql.connector
from unittest.mock import patch, MagicMock

# Test Setup
@pytest.fixture
def client():
    # Critical: Configure app for testing
    app.config.update({
        'TESTING': True,
        'SECRET_KEY': 'test-secret-key-123',  # Required for sessions
        'WTF_CSRF_ENABLED': False,
    })
    with app.test_client() as client:
        with app.app_context():
            yield client

@pytest.fixture
def auth_client(client):
    """Mock authenticated client with session"""
    with client.session_transaction() as sess:
        sess['user'] = 'testuser'  # Bypass login by setting session directly
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

def test_protected_routes(auth_client):
    """Test access to protected routes"""
    routes = [
        '/home',
        '/courses',
        '/pricing',
        '/contact'
    ]
    for route in routes:
        response = auth_client.get(route)
        assert response.status_code == 200, f"Failed on {route}"

def test_logout(auth_client):
    """Test logout clears session"""
    response = auth_client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b'Sign in' in response.data