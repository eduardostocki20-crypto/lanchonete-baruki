import os
import json
import random
import traceback
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from database import init_db, get_db_connection, get_all_settings

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'bella-napoli-pizzaria-secret-key-2026')

# Initialize DB on startup
with app.app_context():
    init_db()

# Custom Jinja Filter for Currency formatting
@app.template_filter('currency')
def currency_filter(value):
    try:
        val = float(value)
        return f"R$ {val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except (ValueError, TypeError):
        return "R$ 0,00"

def get_cart():
    raw_cart = session.get('cart', [])
    if not isinstance(raw_cart, list):
        raw_cart = []
    cleaned = []
    for item in raw_cart:
        if isinstance(item, dict) and 'name' in item:
            item.setdefault('quantity', 1)
            item.setdefault('unit_price', 0.0)
            item.setdefault('total_price', float(item['quantity']) * float(item['unit_price']))
            item.setdefault('item_id', f"{item.get('product_id', 1)}_{item.get('size', 'g')}_{item.get('crust', 't')}")
            cleaned.append(item)
    session['cart'] = cleaned
    return session['cart']

def save_cart(cart):
    session['cart'] = cart
    session.modified = True

def get_delivery_fee():
    try:
        settings = get_all_settings()
        raw = str(settings.get('delivery_fee', '6.00')).replace(',', '.').strip()
        return float(raw)
    except Exception:
        return 6.00

def calculate_cart_totals(cart, delivery_type='delivery'):
    subtotal = 0.0
    for item in cart:
        if isinstance(item, dict):
            subtotal += float(item.get('total_price', 0.0))
    standard_fee = get_delivery_fee()
    delivery_fee = standard_fee if delivery_type == 'delivery' and len(cart) > 0 else 0.0
    total = subtotal + delivery_fee
    return round(subtotal, 2), round(delivery_fee, 2), round(total, 2)

@app.context_processor
def inject_global_data():
    cart = get_cart()
    total_qty = sum(int(item.get('quantity', 1)) for item in cart if isinstance(item, dict))
    subtotal = sum(float(item.get('total_price', 0.0)) for item in cart if isinstance(item, dict))
    settings = get_all_settings()
    return {
        'cart_count': total_qty,
        'cart_subtotal': subtotal,
        'settings': settings
    }

# ==================== PUBLIC ROUTES ====================

@app.route('/')
def index():
    conn = get_db_connection()
    featured_pizzas = conn.execute(
        "SELECT * FROM products WHERE is_pizza = 1 AND active = 1 LIMIT 6"
    ).fetchall()
    conn.close()
    return render_template('index.html', featured_pizzas=featured_pizzas)

@app.route('/cardapio')
def menu():
    category = request.args.get('categoria', 'todos')
    conn = get_db_connection()
    categories = conn.execute("SELECT * FROM categories").fetchall()
    
    if category and category != 'todos':
        products = conn.execute(
            "SELECT * FROM products WHERE category_slug = ? AND active = 1", (category,)
        ).fetchall()
    else:
        products = conn.execute(
            "SELECT * FROM products WHERE active = 1"
        ).fetchall()
        
    conn.close()
    return render_template('menu.html', products=products, categories=categories, selected_category=category)

@app.route('/rastreio', methods=['GET', 'POST'])
def tracking_lookup():
    if request.method == 'POST':
        query = request.form.get('query', '').strip().replace('#', '')
        if query.isdigit():
            return redirect(url_for('track_order', order_id=int(query)))
        else:
            conn = get_db_connection()
            orders = conn.execute(
                "SELECT * FROM orders WHERE customer_phone LIKE ? ORDER BY id DESC LIMIT 5",
                (f"%{query}%",)
            ).fetchall()
            conn.close()
            if orders:
                if len(orders) == 1:
                    return redirect(url_for('track_order', order_id=orders[0]['id']))
                return render_template('tracking_lookup.html', orders=orders, query=query)
            flash("Nenhum pedido encontrado para o número informado.", "warning")

    return render_template('tracking_lookup.html')

# ==================== CART API ROUTES ====================

@app.route('/api/cart', methods=['GET'])
def api_get_cart():
    cart = get_cart()
    subtotal, fee, total = calculate_cart_totals(cart)
    return jsonify({
        'items': cart,
        'subtotal': subtotal,
        'delivery_fee': fee,
        'total': total,
        'count': sum(int(i.get('quantity', 1)) for i in cart if isinstance(i, dict))
    })

@app.route('/api/cart/add', methods=['POST'])
def api_add_to_cart():
    try:
        data = request.get_json(force=True, silent=True) or request.form.to_dict() or {}
        product_id = int(float(data.get('product_id', 0)))
        size = str(data.get('size', 'grande')).lower().strip()
        crust = str(data.get('crust', 'Tradicional')).strip()
        notes = str(data.get('notes', '')).strip()
        quantity = max(1, int(float(data.get('quantity', 1))))

        if product_id <= 0:
            return jsonify({'success': False, 'message': 'Produto inválido'}), 400

        conn = get_db_connection()
        product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        conn.close()

        if not product:
            return jsonify({'success': False, 'message': 'Produto não encontrado no cardápio'}), 404

        if product['is_pizza']:
            if size == 'media':
                base_price = float(product['price_media'])
            elif size == 'familia':
                base_price = float(product['price_familia'])
            else:
                base_price = float(product['price_grande'])
                size = 'grande'
        else:
            base_price = float(product['price_media'])
            size = 'único'

        crust_price = 0.0
        if product['is_pizza'] and crust in ['Catupiry Original', 'Cheddar Cremoso']:
            crust_price = 8.00
        elif product['is_pizza'] and crust == 'Chocolate':
            crust_price = 12.00

        unit_price = round(base_price + crust_price, 2)
        item_total = round(unit_price * quantity, 2)

        cart = get_cart()
        item_id = f"{product_id}_{size}_{crust}_{notes}".replace(' ', '_').replace('/', '_')

        existing = next((item for item in cart if isinstance(item, dict) and item.get('item_id') == item_id), None)
        if existing:
            existing['quantity'] = int(existing.get('quantity', 1)) + quantity
            existing['total_price'] = round(existing['quantity'] * float(existing.get('unit_price', unit_price)), 2)
        else:
            cart.append({
                'item_id': item_id,
                'product_id': int(product['id']),
                'name': str(product['name']),
                'image_url': str(product['image_url']),
                'size': size.capitalize(),
                'crust': crust,
                'notes': notes,
                'unit_price': unit_price,
                'quantity': quantity,
                'total_price': item_total,
                'is_pizza': bool(product['is_pizza'])
            })

        save_cart(cart)
        subtotal, fee, total = calculate_cart_totals(cart)

        return jsonify({
            'success': True,
            'message': f"{product['name']} adicionado ao carrinho com sucesso!",
            'cart_count': sum(int(i.get('quantity', 1)) for i in cart if isinstance(i, dict)),
            'subtotal': subtotal
        })

    except Exception as err:
        traceback.print_exc()
        return jsonify({'success': False, 'message': f"Erro no servidor: {str(err)}"}), 500

@app.route('/api/cart/update', methods=['POST'])
def api_update_cart():
    try:
        data = request.get_json(force=True, silent=True) or request.form.to_dict() or {}
        item_id = data.get('item_id')
        delta = int(data.get('delta', 0))

        cart = get_cart()
        item = next((i for i in cart if isinstance(i, dict) and i.get('item_id') == item_id), None)

        if item:
            item['quantity'] = int(item.get('quantity', 1)) + delta
            if item['quantity'] <= 0:
                cart = [i for i in cart if isinstance(i, dict) and i.get('item_id') != item_id]
            else:
                item['total_price'] = round(item['quantity'] * float(item.get('unit_price', 0)), 2)

        save_cart(cart)
        subtotal, fee, total = calculate_cart_totals(cart)
        return jsonify({
            'success': True,
            'items': cart,
            'subtotal': subtotal,
            'delivery_fee': fee,
            'total': total,
            'count': sum(int(i.get('quantity', 1)) for i in cart if isinstance(i, dict))
        })
    except Exception as err:
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(err)}), 500

@app.route('/api/cart/remove', methods=['POST'])
def api_remove_from_cart():
    try:
        data = request.get_json(force=True, silent=True) or request.form.to_dict() or {}
        item_id = data.get('item_id')
        cart = [i for i in get_cart() if isinstance(i, dict) and i.get('item_id') != item_id]
        save_cart(cart)
        subtotal, fee, total = calculate_cart_totals(cart)
        return jsonify({
            'success': True,
            'items': cart,
            'subtotal': subtotal,
            'delivery_fee': fee,
            'total': total,
            'count': sum(int(i.get('quantity', 1)) for i in cart if isinstance(i, dict))
        })
    except Exception as err:
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(err)}), 500

# ==================== CHECKOUT & ORDERS ====================

@app.route('/carrinho')
def view_cart():
    cart = get_cart()
    subtotal, delivery_fee, total = calculate_cart_totals(cart)
    return render_template('cart.html', cart=cart, subtotal=subtotal, delivery_fee=delivery_fee, total=total)

@app.route('/finalizar-pedido', methods=['POST'])
def checkout():
    cart = get_cart()
    if not cart:
        flash("Seu carrinho está vazio!", "warning")
        return redirect(url_for('menu'))

    customer_name = request.form.get('customer_name', '').strip()
    customer_phone = request.form.get('customer_phone', '').strip()
    delivery_type = request.form.get('delivery_type', 'delivery')
    address = request.form.get('address', '').strip() if delivery_type == 'delivery' else 'Retirada no Balcão'
    payment_method = request.form.get('payment_method', 'Pix')
    notes = request.form.get('notes', '').strip()

    if not customer_name or not customer_phone:
        flash("Por favor, preencha nome e telefone para contato.", "error")
        return redirect(url_for('view_cart'))

    # Generate 4-digit iFood-style Delivery Security Code PIN
    delivery_code = f"{random.randint(1000, 9999)}"

    subtotal, delivery_fee, total = calculate_cart_totals(cart, delivery_type)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO orders (
            customer_name, customer_phone, delivery_type, 
            address, payment_method, notes, subtotal, delivery_fee, total, status, delivery_code
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pedido Feito', ?)
    ''', (customer_name, customer_phone, delivery_type, address, payment_method, notes, subtotal, delivery_fee, total, delivery_code))
    
    order_id = cursor.lastrowid

    for item in cart:
        cursor.execute('''
            INSERT INTO order_items (
                order_id, product_name, size, crust, quantity, unit_price, item_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            order_id,
            item['name'],
            item.get('size'),
            item.get('crust'),
            int(item.get('quantity', 1)),
            float(item.get('unit_price', 0)),
            item.get('notes')
        ))

    conn.commit()
    conn.close()

    session.pop('cart', None)
    return redirect(url_for('track_order', order_id=order_id))

@app.route('/pedido/<int:order_id>')
def track_order(order_id):
    conn = get_db_connection()
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not order:
        conn.close()
        flash("Pedido não encontrado.", "error")
        return redirect(url_for('tracking_lookup'))

    items = conn.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,)).fetchall()
    conn.close()

    settings = get_all_settings()
    pizzeria_name = settings.get('pizzeria_name', 'Pizzaria')

    delivery_code = order['delivery_code'] or '1234'

    msg_lines = [
        f"🍕 *NOVO PEDIDO #{order['id']} - {pizzeria_name.upper()}*",
        f"🔑 *CÓDIGO DE CONFIRMAÇÃO DE ENTREGA:* {delivery_code}",
        f"👤 *Cliente:* {order['customer_name']}",
        f"📞 *Telefone:* {order['customer_phone']}",
        f"🛵 *Tipo:* {'Entrega em Domicílio' if order['delivery_type'] == 'delivery' else 'Retirada no Balcão'}",
    ]
    if order['delivery_type'] == 'delivery':
        msg_lines.append(f"📍 *Endereço:* {order['address']}")
    msg_lines.append(f"💳 *Pagamento:* {order['payment_method']}")
    if order['notes']:
        msg_lines.append(f"📝 *Obs Geral:* {order['notes']}")
    msg_lines.append("\n📋 *ITENS DO PEDIDO:*")

    for idx, item in enumerate(items, 1):
        line = f"• {item['quantity']}x {item['product_name']}"
        if item['size'] and item['size'] != 'Único':
            line += f" ({item['size']})"
        if item['crust'] and item['crust'] != 'Tradicional':
            line += f" [Borda: {item['crust']}]"
        if item['item_notes']:
            line += f" - Obs: {item['item_notes']}"
        msg_lines.append(line)

    msg_lines.append(f"\n*Total:* R$ {order['total']:.2f}".replace('.', ','))
    msg_lines.append(f"\n_O cliente informará o código *{delivery_code}* ao entregador na chegada._")
    whatsapp_message = "\n".join(msg_lines)

    return render_template('order_tracking.html', order=order, items=items, whatsapp_message=whatsapp_message)

@app.route('/api/pedido/<int:order_id>/status')
def api_order_status(order_id):
    conn = get_db_connection()
    order = conn.execute("SELECT id, status, delivery_code FROM orders WHERE id = ?", (order_id,)).fetchone()
    conn.close()
    if not order:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({
        'id': order['id'],
        'status': order['status'],
        'delivery_code': order['delivery_code']
    })

# ==================== ADMIN DASHBOARD ====================

@app.route('/admin')
def admin_dashboard():
    tab = request.args.get('tab', 'pedidos')
    conn = get_db_connection()
    orders = conn.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 50").fetchall()
    products = conn.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    categories = conn.execute("SELECT * FROM categories").fetchall()
    
    total_sales = conn.execute("SELECT SUM(total) FROM orders WHERE status != 'Cancelado'").fetchone()[0] or 0.0
    pending_count = conn.execute("SELECT COUNT(*) FROM orders WHERE status IN ('Pedido Feito', 'Pedido em Preparo', 'Pedido Coletado')").fetchone()[0] or 0
    total_orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0] or 0

    conn.close()
    return render_template(
        'admin.html', 
        orders=orders, 
        products=products, 
        categories=categories,
        total_sales=total_sales, 
        pending_count=pending_count,
        total_orders=total_orders,
        active_tab=tab
    )

@app.route('/admin/configuracoes', methods=['POST'])
def admin_save_settings():
    conn = get_db_connection()
    fields = [
        'pizzeria_name', 'pizzeria_tagline', 'whatsapp_number', 
        'phone_contact', 'address', 'opening_hours', 'delivery_fee', 
        'delivery_time', 'promo_banner', 'pix_key', 'instagram_url', 
        'google_maps_url', 'about_text'
    ]
    for field in fields:
        val = request.form.get(field, '').strip()
        conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (field, val))
        
    conn.commit()
    conn.close()
    flash("🎉 Informações do comércio atualizadas com sucesso em todo o site!", "success")
    return redirect(url_for('admin_dashboard', tab='config'))

@app.route('/admin/order/<int:order_id>/status', methods=['POST'])
def admin_update_order_status(order_id):
    new_status = request.form.get('status')
    conn = get_db_connection()
    conn.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
    conn.commit()
    conn.close()
    flash(f"Status do pedido #{order_id} alterado para '{new_status}'!", "success")
    return redirect(url_for('admin_dashboard', tab='pedidos'))

@app.route('/admin/product/toggle/<int:product_id>', methods=['POST'])
def admin_toggle_product(product_id):
    conn = get_db_connection()
    conn.execute("UPDATE products SET active = 1 - active WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    flash("Status do produto alterado!", "success")
    return redirect(url_for('admin_dashboard', tab='produtos'))

@app.route('/admin/product/delete/<int:product_id>', methods=['POST'])
def admin_delete_product(product_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    flash("Produto excluído do cardápio!", "success")
    return redirect(url_for('admin_dashboard', tab='produtos'))

@app.route('/admin/product/add', methods=['POST'])
def admin_add_product():
    name = request.form.get('name')
    category_slug = request.form.get('category_slug')
    badge = request.form.get('badge', '')
    description = request.form.get('description', '')
    price_media = float(request.form.get('price_media', 0))
    price_grande = float(request.form.get('price_grande', price_media))
    price_familia = float(request.form.get('price_familia', price_grande))
    image_url = request.form.get('image_url') or 'https://images.unsplash.com/photo-1513104890138-7c749659a591?auto=format&fit=crop&w=800&q=80'
    is_pizza = 1 if request.form.get('is_pizza') == 'on' else 0

    conn = get_db_connection()
    conn.execute('''
        INSERT INTO products (
            name, category_slug, badge, description, 
            price_media, price_grande, price_familia, 
            image_url, is_pizza, active
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
    ''', (name, category_slug, badge, description, price_media, price_grande, price_familia, image_url, is_pizza))
    conn.commit()
    conn.close()

    flash(f"Produto '{name}' adicionado com sucesso!", "success")
    return redirect(url_for('admin_dashboard', tab='produtos'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🍕 Servidor da Pizzaria iniciando em http://localhost:{port} ...")
    app.run(host='0.0.0.0', port=port, debug=False)
