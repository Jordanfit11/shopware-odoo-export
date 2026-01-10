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
        
        print(f"Récupération commandes - Limite: {limit}, Statut: {status}")
        
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
        
        print(f"Commandes récupérées: {len(all_orders)}")
        
        # Filtrer par statut si nécessaire
        if status is not None and status != "":
            try:
                status_int = int(status)
                filtered_orders = [o for o in all_orders if o.get('status') == status_int]
                print(f"Après filtre statut {status_int}: {len(filtered_orders)} commandes")
            except (ValueError, TypeError):
                filtered_orders = all_orders
        else:
            filtered_orders = all_orders
        
        return jsonify({
            'success': True,
            'total': len(all_orders),
            'filtered': len(filtered_orders),
            'orders': filtered_orders
        })
        
    except Exception as e:
        print(f"Erreur: {str(e)}")
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

@app.route('/api/import-to-odoo', methods=['POST'])
def import_to_odoo():
    """Importer les commandes dans Odoo via API XML-RPC"""
    try:
        import xmlrpc.client
        
        data = request.json or {}
        orders = data.get('orders', [])
        odoo_url = data.get('odoo_url')
        odoo_db = data.get('odoo_db')
        odoo_username = data.get('odoo_username')
        odoo_api_key = data.get('odoo_api_key')
        
        if not all([odoo_url, odoo_db, odoo_username, odoo_api_key]):
            return jsonify({
                'success': False,
                'error': 'Credentials Odoo manquants'
            }), 400
        
        if not orders:
            return jsonify({
                'success': False,
                'error': 'Aucune commande à importer'
            }), 400
        
        print(f"Import Odoo - {len(orders)} lignes à traiter")
        
        # Connexion Odoo
        try:
            common = xmlrpc.client.ServerProxy(f'{odoo_url}/xmlrpc/2/common')
            uid = common.authenticate(odoo_db, odoo_username, odoo_api_key, {})
            
            if not uid:
                return jsonify({
                    'success': False,
                    'error': 'Authentification Odoo échouée'
                }), 401
            
            print(f"Connecté à Odoo - UID: {uid}")
            
            models = xmlrpc.client.ServerProxy(f'{odoo_url}/xmlrpc/2/object')
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Connexion Odoo impossible: {str(e)}'
            }), 500
        
        # Grouper par commande
        orders_grouped = {}
        for order_line in orders:
            order_num = order_line.get('order_number')
            if order_num not in orders_grouped:
                orders_grouped[order_num] = []
            orders_grouped[order_num].append(order_line)
        
        print(f"Création de {len(orders_grouped)} commandes")
        
        created_orders = []
        errors = []
        
        # Créer chaque commande
        for order_number, lines in orders_grouped.items():
            try:
                first_line = lines[0]
                
                # Trouver ou créer le client
                customer_email = first_line.get('customer_email')
                customer_name = first_line.get('customer_name', 'Client inconnu')
                
                partner_id = None
                if customer_email:
                    partner_ids = models.execute_kw(
                        odoo_db, uid, odoo_api_key,
                        'res.partner', 'search',
                        [[['email', '=', customer_email]]]
                    )
                    
                    if partner_ids:
                        partner_id = partner_ids[0]
                    else:
                        # Créer le client
                        partner_id = models.execute_kw(
                            odoo_db, uid, odoo_api_key,
                            'res.partner', 'create',
                            [{
                                'name': customer_name,
                                'email': customer_email,
                                'customer_rank': 1
                            }]
                        )
                
                if not partner_id:
                    errors.append(f"{order_number}: Client non trouvé/créé")
                    continue
                
                # Préparer les lignes de commande
                order_line_data = []
                products_not_found = []
                
                for line in lines:
                    product_ref = line.get('product_ref_odoo')
                    
                    if not product_ref:
                        continue
                    
                    # Trouver le produit
                    product_ids = models.execute_kw(
                        odoo_db, uid, odoo_api_key,
                        'product.product', 'search',
                        [[['default_code', '=', product_ref]]]
                    )
                    
                    if not product_ids:
                        products_not_found.append(product_ref)
                        continue
                    
                    order_line_data.append((0, 0, {
                        'product_id': product_ids[0],
                        'product_uom_qty': float(line.get('quantity', 1)),
                        'price_unit': float(line.get('unit_price', 0))
                    }))
                
                if not order_line_data:
                    errors.append(f"{order_number}: Aucun produit trouvé")
                    continue
                
                # Créer la commande
                order_vals = {
                    'partner_id': partner_id,
                    'client_order_ref': order_number,
                    'order_line': order_line_data
                }
                
                # Ajouter la date si disponible
                order_date = first_line.get('order_date')
                if order_date:
                    order_vals['date_order'] = order_date
                
                order_id = models.execute_kw(
                    odoo_db, uid, odoo_api_key,
                    'sale.order', 'create',
                    [order_vals]
                )
                
                created_orders.append({
                    'order_number': order_number,
                    'odoo_id': order_id,
                    'lines_count': len(order_line_data),
                    'products_not_found': products_not_found
                })
                
                print(f"Commande {order_number} créée - ID: {order_id}")
                
            except Exception as e:
                error_msg = f"{order_number}: {str(e)}"
                errors.append(error_msg)
                print(f"Erreur: {error_msg}")
        
        return jsonify({
            'success': True,
            'imported': len(created_orders),
            'errors_count': len(errors),
            'total_orders': len(orders_grouped),
            'created_orders': created_orders[:10],  # 10 premiers pour éviter payload trop gros
            'errors': errors[:10]  # 10 premières erreurs
        })
        
    except Exception as e:
        print(f"Erreur globale: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Pour Vercel
if __name__ == '__main__':
    app.run()
