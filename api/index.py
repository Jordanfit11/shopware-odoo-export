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
    """Récupérer les commandes Shopware avec filtres"""
    try:
        data = request.json or {}
        limit = data.get('limit', 1000)
        status = data.get('status')
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        
        print(f"=== EXPORT ORDERS ===")
        print(f"Limite: {limit}")
        print(f"Statut: {status}")
        print(f"Date de: {date_from}")
        print(f"Date à: {date_to}")
        
        # Appeler Shopware
        url = f"{SHOPWARE_URL}/api/orders"
        response = requests.get(
            url,
            auth=HTTPDigestAuth(API_USERNAME, API_KEY),
            params={'limit': limit},
            timeout=60
        )
        
        if response.status_code != 200:
            return jsonify({
                'success': False,
                'error': f'Erreur Shopware {response.status_code}'
            }), 400
        
        orders_data = response.json()
        all_orders = orders_data.get('data', [])
        
        print(f"Commandes récupérées: {len(all_orders)}")
        
        # Filtrer par statut (nom ou numéro)
        filtered_orders = all_orders
        if status is not None and status != "":
            print(f"Filtre statut: {status} (type: {type(status)})")
            
            if status == 'null':
                # Filtrer les commandes avec statut null
                filtered_orders = [o for o in filtered_orders if o.get('status') is None]
            else:
                # Filtrer par nom de statut OU par numéro
                filtered_orders = []
                for o in filtered_orders:
                    order_status_obj = o.get('orderStatus', {})
                    status_name = order_status_obj.get('name') if isinstance(order_status_obj, dict) else None
                    status_num = o.get('status')
                    
                    # Comparer avec le nom OU le numéro
                    if status_name == status or status_num == status:
                        filtered_orders.append(o)
            
            print(f"Après filtre statut: {len(filtered_orders)}")
        
        # Filtrer par date (côté serveur pour optimisation)
        if date_from:
            from datetime import datetime
            date_from_dt = datetime.fromisoformat(date_from)
            filtered_orders = [o for o in filtered_orders 
                             if o.get('orderTime') and datetime.fromisoformat(o['orderTime'][:10]) >= date_from_dt]
            print(f"Après filtre date_from: {len(filtered_orders)}")
        
        if date_to:
            from datetime import datetime
            date_to_dt = datetime.fromisoformat(date_to)
            filtered_orders = [o for o in filtered_orders 
                             if o.get('orderTime') and datetime.fromisoformat(o['orderTime'][:10]) <= date_to_dt]
            print(f"Après filtre date_to: {len(filtered_orders)}")
        
        return jsonify({
            'success': True,
            'total': len(all_orders),
            'filtered': len(filtered_orders),
            'orders': filtered_orders
        })
        
    except Exception as e:
        print(f"Erreur: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/debug-statuses', methods=['GET'])
def debug_statuses():
    """Voir les statuts réels dans Shopware"""
    try:
        url = f"{SHOPWARE_URL}/api/orders"
        response = requests.get(
            url,
            auth=HTTPDigestAuth(API_USERNAME, API_KEY),
            params={'limit': 100},
            timeout=30
        )
        
        if response.status_code != 200:
            return jsonify({'success': False, 'error': f'Erreur {response.status_code}'}), 400
        
        orders = response.json().get('data', [])
        
        # Compter les statuts (numéro ET nom)
        status_counts = {}
        status_examples = {}
        
        for order in orders:
            # Essayer différents champs
            status_num = order.get('status')
            order_status_obj = order.get('orderStatus', {})
            status_name = order_status_obj.get('name') if isinstance(order_status_obj, dict) else None
            
            # Clé combinée
            key = f"{status_num} - {status_name}" if status_name else str(status_num)
            order_number = order.get('number', order.get('id', 'N/A'))
            
            if key not in status_counts:
                status_counts[key] = 0
                status_examples[key] = []
            
            status_counts[key] += 1
            if len(status_examples[key]) < 3:
                status_examples[key].append(order_number)
        
        return jsonify({
            'success': True,
            'status_counts': status_counts,
            'status_examples': status_examples,
            'total_orders': len(orders)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

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
        
        # Options avancées
        order_tag = data.get('order_tag', 'E-shop Shopware')
        default_carrier = data.get('default_carrier')
        default_warehouse = data.get('default_warehouse')
        order_note = data.get('order_note', '')
        auto_confirm = data.get('auto_confirm', False)
        
        print(f"Options: tag={order_tag}, carrier={default_carrier}, warehouse={default_warehouse}, auto_confirm={auto_confirm}")
        
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
        for idx, order_line in enumerate(orders):
            order_num = order_line.get('order_number')
            
            # Si pas de numéro ou "0", créer un ID unique par ligne
            if not order_num or order_num == '0' or order_num == 'NO_NUMBER':
                # Une commande = une ligne
                order_num = f"IMPORT_{order_line.get('customer_email', 'UNKNOWN')}_{idx}"
            
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
                
                print(f"\n=== Traitement commande {order_number} ===")
                
                # Trouver ou créer le client
                customer_email = first_line.get('customer_email')
                customer_name = first_line.get('customer_name', 'Client inconnu')
                
                print(f"Client: {customer_name} ({customer_email})")
                
                partner_id = None
                if customer_email:
                    try:
                        partner_ids = models.execute_kw(
                            odoo_db, uid, odoo_api_key,
                            'res.partner', 'search',
                            [[['email', '=', customer_email]]]
                        )
                        
                        if partner_ids:
                            partner_id = partner_ids[0]
                            print(f"Client trouvé: ID {partner_id}")
                        else:
                            # Créer le client
                            print(f"Création du client...")
                            partner_id = models.execute_kw(
                                odoo_db, uid, odoo_api_key,
                                'res.partner', 'create',
                                [{
                                    'name': customer_name,
                                    'email': customer_email,
                                    'customer_rank': 1
                                }]
                            )
                            print(f"Client créé: ID {partner_id}")
                    except Exception as e:
                        print(f"Erreur création client: {str(e)}")
                        errors.append(f"{order_number}: Erreur client - {str(e)[:200]}")
                        continue
                
                if not partner_id:
                    errors.append(f"{order_number}: Client non trouvé/créé (email manquant)")
                    print("SKIP: Pas de client")
                    continue
                
                # Préparer les lignes de commande
                order_line_data = []
                products_not_found = []
                
                print(f"Traitement de {len(lines)} lignes...")
                
                for line in lines:
                    product_ref = line.get('product_ref_odoo')
                    
                    if not product_ref:
                        print(f"  SKIP ligne: pas de référence Odoo")
                        continue
                    
                    # Trouver le produit
                    try:
                        product_ids = models.execute_kw(
                            odoo_db, uid, odoo_api_key,
                            'product.product', 'search',
                            [[['default_code', '=', product_ref]]]
                        )
                        
                        if not product_ids:
                            print(f"  Produit non trouvé: {product_ref}")
                            products_not_found.append(product_ref)
                            continue
                        
                        print(f"  Produit trouvé: {product_ref} -> ID {product_ids[0]}")
                        
                        order_line_data.append((0, 0, {
                            'product_id': product_ids[0],
                            'product_uom_qty': float(line.get('quantity', 1)),
                            'price_unit': float(line.get('unit_price', 0))
                        }))
                    except Exception as e:
                        print(f"  Erreur recherche produit {product_ref}: {str(e)}")
                        products_not_found.append(f"{product_ref} (erreur)")
                
                if not order_line_data:
                    errors.append(f"{order_number}: Aucun produit trouvé")
                    print("SKIP: Aucun produit")
                    continue
                
                # Créer la commande
                print(f"Création commande avec {len(order_line_data)} lignes...")
                
                try:
                    order_vals = {
                        'partner_id': partner_id,
                        'client_order_ref': order_number,
                        'order_line': order_line_data
                    }
                    
                    # Ajouter les options avancées
                    if default_carrier:
                        order_vals['carrier_id'] = default_carrier
                        print(f"Transporteur: {default_carrier}")
                    
                    if default_warehouse:
                        order_vals['warehouse_id'] = default_warehouse
                        print(f"Entrepôt: {default_warehouse}")
                    
                    if order_note:
                        order_vals['note'] = order_note
                    
                    # Ajouter une étiquette/tag si Odoo le supporte
                    # Note: cela nécessite que le module sale_management soit installé
                    if order_tag:
                        # On va ajouter le tag dans la note pour l'instant
                        tag_note = f"[{order_tag}]"
                        if 'note' in order_vals:
                            order_vals['note'] = f"{tag_note} {order_vals['note']}"
                        else:
                            order_vals['note'] = tag_note
                    
                    # Ajouter la date si disponible (convertir le format)
                    order_date = first_line.get('order_date')
                    if order_date:
                        # Convertir ISO format vers format Odoo
                        # De: 2025-12-01T17:23:37+0100
                        # Vers: 2025-12-01 17:23:37
                        try:
                            import re
                            # Enlever le timezone et remplacer T par espace
                            clean_date = re.sub(r'[+-]\d{4}$', '', order_date)  # Enlever +0100
                            clean_date = clean_date.replace('T', ' ')  # T -> espace
                            order_vals['date_order'] = clean_date
                            print(f"Date convertie: {order_date} -> {clean_date}")
                        except Exception as e:
                            print(f"Erreur conversion date: {e}, date ignorée")
                    
                    order_id = models.execute_kw(
                        odoo_db, uid, odoo_api_key,
                        'sale.order', 'create',
                        [order_vals]
                    )
                    
                    print(f"✅ Commande créée: ID {order_id}")
                    
                    # Confirmer automatiquement si demandé
                    if auto_confirm:
                        try:
                            models.execute_kw(
                                odoo_db, uid, odoo_api_key,
                                'sale.order', 'action_confirm',
                                [[order_id]]
                            )
                            print(f"✅ Commande confirmée automatiquement")
                        except Exception as e:
                            print(f"⚠️ Impossible de confirmer automatiquement: {e}")
                    
                    created_orders.append({
                        'order_number': order_number,
                        'odoo_id': order_id,
                        'lines_count': len(order_line_data),
                        'products_not_found': products_not_found
                    })
                    
                    print(f"✅ Commande créée: ID {order_id}")
                    
                except Exception as e:
                    error_msg = f"{order_number}: Erreur création - {str(e)[:500]}"
                    errors.append(error_msg)
                    print(f"❌ {error_msg}")
                
            except Exception as e:
                error_msg = f"{order_number}: {str(e)[:500]}"
                errors.append(error_msg)
                print(f"❌ Erreur globale: {error_msg}")
        
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
