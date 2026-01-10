"""
API Proxy pour Shopware - Déployé sur Vercel
Contourne le problème CORS
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from requests.auth import HTTPDigestAuth
import os

app = Flask(__name__)
CORS(app, origins=["*"])  # Autoriser tous les domaines

# Configuration Shopware
SHOPWARE_URL = os.getenv('SHOPWARE_URL', 'https://fr.hau.vonaffenfels.de')
API_USERNAME = os.getenv('API_USERNAME', 'odoosync')
API_KEY = os.getenv('API_KEY', 'T8dbJHHQGtrJtG4kGXuxFW2Z4EM7uDMD5cyhlkWf')

@app.route('/api/test', methods=['GET'])
def test():
    """Test simple"""
    return jsonify({'status': 'ok', 'message': 'Proxy Shopware actif'})

@app.route('/api/orders', methods=['POST'])
def get_orders():
    """Récupérer les commandes Shopware"""
    try:
        data = request.json or {}
        limit = data.get('limit', 1000)
        status = data.get('status')
        
        # Appeler Shopware
        url = f"{SHOPWARE_URL}/api/orders"
        response = requests.get(
            url,
            auth=HTTPDigestAuth(API_USERNAME, API_KEY),
            params={'limit': limit},
            timeout=30
        )
        
        if response.status_code != 200:
            return jsonify({
                'success': False,
                'error': f'Erreur Shopware {response.status_code}'
            }), 400
        
        orders_data = response.json()
        all_orders = orders_data.get('data', [])
        
        # Filtrer par statut si nécessaire
        if status is not None:
            filtered_orders = [o for o in all_orders if o.get('status') == status]
        else:
            filtered_orders = all_orders
        
        return jsonify({
            'success': True,
            'total': len(all_orders),
            'filtered': len(filtered_orders),
            'orders': filtered_orders
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/test-connection', methods=['GET'])
def test_connection():
    """Tester la connexion Shopware"""
    try:
        url = f"{SHOPWARE_URL}/api/orders"
        response = requests.get(
            url,
            auth=HTTPDigestAuth(API_USERNAME, API_KEY),
            params={'limit': 1},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            return jsonify({
                'success': True,
                'total': data.get('total', 0)
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Erreur {response.status_code}'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Pour Vercel
if __name__ == '__main__':
    app.run()
