import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'pizzaria.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn

def get_all_settings():
    try:
        conn = get_db_connection()
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
        conn.close()
        return {row['key']: row['value'] for row in rows}
    except Exception as e:
        print(f"Aviso ao ler settings: {e}")
        return {}

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category_slug TEXT NOT NULL,
            badge TEXT,
            description TEXT,
            price_media REAL NOT NULL,
            price_grande REAL NOT NULL,
            price_familia REAL NOT NULL,
            image_url TEXT,
            is_pizza INTEGER DEFAULT 1,
            active INTEGER DEFAULT 1
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            delivery_type TEXT NOT NULL,
            address TEXT,
            payment_method TEXT NOT NULL,
            notes TEXT,
            subtotal REAL NOT NULL,
            delivery_fee REAL NOT NULL,
            total REAL NOT NULL,
            status TEXT DEFAULT 'Pedido Feito',
            delivery_code TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Migration: Add delivery_code column if table already existed without it
    try:
        cursor.execute("ALTER TABLE orders ADD COLUMN delivery_code TEXT")
    except sqlite3.OperationalError:
        pass

    # Ensure existing orders have a 4-digit code
    cursor.execute("UPDATE orders SET delivery_code = '4892' WHERE delivery_code IS NULL OR delivery_code = ''")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            size TEXT,
            crust TEXT,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            item_notes TEXT,
            FOREIGN KEY (order_id) REFERENCES orders (id)
        )
    ''')

    # Default Settings Seed
    cursor.execute('SELECT COUNT(*) FROM settings')
    if cursor.fetchone()[0] == 0:
        default_settings = [
            ('pizzeria_name', 'Bella Napoli'),
            ('pizzeria_tagline', 'Pizzaria Artesanal no Forno a Lenha'),
            ('whatsapp_number', '5511999999999'),
            ('phone_contact', '(11) 3333-3333'),
            ('address', 'Rua das Pizzas, 742 - Jardins, São Paulo - SP'),
            ('opening_hours', 'Terça a Domingo: das 18h00 às 23h30 (Segunda fechado)'),
            ('delivery_fee', '6.00'),
            ('delivery_time', '30-45 min'),
            ('promo_banner', 'Terça a Quinta: Borda de Catupiry ou Cheddar grátis em qualquer Pizza Grande!'),
            ('pix_key', '11999999999 (Celular)'),
            ('instagram_url', 'https://instagram.com'),
            ('google_maps_url', 'https://maps.google.com'),
            ('about_text', 'Massa de fermentação natural de 48 horas, farinha italiana tipo 00, molho de tomates San Marzano e queijos artesanais frescos assados a 450°C.')
        ]
        cursor.executemany('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', default_settings)

    cursor.execute('SELECT COUNT(*) FROM categories')
    if cursor.fetchone()[0] == 0:
        categories = [
            ('tradicionais', 'Pizzas Tradicionais'),
            ('especiais', 'Pizzas Especiais'),
            ('doces', 'Pizzas Doces'),
            ('bebidas', 'Bebidas')
        ]
        cursor.executemany('INSERT INTO categories (slug, name) VALUES (?, ?)', categories)

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Banco de dados SQLite inicializado com coluna de código de entrega!")
