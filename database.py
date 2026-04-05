import sqlite3
from datetime import datetime
from typing import List, Dict

class Database:
    def __init__(self, db_name='finance.db'):
        self.connection = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.connection.cursor()
        self.create_tables()
    
    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                date TEXT NOT NULL,
                is_income INTEGER DEFAULT 0
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                keywords TEXT
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS income_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                keywords TEXT
            )
        ''')
        
        self.connection.commit()
        self.init_categories()
        self.init_income_categories()
    
    def init_categories(self):
        default_categories = [
            ('Продукты', 'продукты,еда,магазин,супермаркет,пятёрочка,лента,перекрёсток,дикси,ашан,молоко,хлеб,мясо,овощи,фрукты,колбаса,сыр,яйца'),
            ('Транспорт', 'метро,такси,яндекс такси,uber,автобус,трамвай,троллейбус,электричка,поезд,самолёт,билет,каршеринг'),
            ('Авто', 'бензин,азс,заправка,ремонт авто,запчасти,мойка,шиномонтаж,шиномантаж,то,техосмотр,масло,антифриз,парковка,штраф,колёса,резина,автосервис'),
            ('Маркетплейсы', 'озон,ozon,вайлдберриз,wildberries,wb,яндекс маркет,aliexpress,алиэкспресс,сбермегамаркет,мегамаркет,amazon'),
            ('Кафе/Рестораны', 'кафе,ресторан,макдональдс,кфс,бургер,пицца,суши,бар,кофе,столовая,доставка еды,обед,ужин,завтрак,ланч,бизнес-ланч,фастфуд,шаурма,роллы'),
            ('Развлечения', 'кино,театр,концерт,игры,подписка,netflix,spotify,youtube,steam,боулинг,клуб,бильярд,квест,парк,зоопарк,музей'),
            ('Здоровье', 'аптека,врач,лекарства,больница,анализы,стоматолог,клиника,витамины,медикаменты,таблетки,мазь'),
            ('Красота', 'салон,парикмахерская,стрижка,маникюр,педикюр,ногти,косметика,крем,шампунь,маска,спа,массаж,барбершоп,брови,ресницы,эпиляция,солярий,уход,визажист,макияж'),
            ('Одежда', 'одежда,обувь,zara,h&m,nike,adidas,джинсы,куртка,платье,кроссовки,футболка,штаны,пальто,шапка'),
            ('Дом', 'квартплата,коммунальные,свет,вода,газ,интернет,мебель,техника,уборка,ремонт,электричество,отопление'),
            ('Кредиты', 'ипотека,кредит,кредитка,микрозайм,займ,долг,рассрочка,платёж по кредиту,банк'),
            ('Питомцы', 'кот,кошка,кошки,собака,собаки,пёс,щенок,котёнок,корм,ветеринар,ветклиника,вет,лоток,наполнитель,поводок,ошейник,груминг,питомец,животное,хомяк,попугай,рыбки,аквариум'),
            ('Другое', '')
        ]
        
        self.cursor.execute('DELETE FROM categories')
        
        for category, keywords in default_categories:
            self.cursor.execute(
                'INSERT INTO categories (name, keywords) VALUES (?, ?)',
                (category, keywords)
            )
        
        self.connection.commit()
    
    def init_income_categories(self):
        income_categories = [
            ('Зарплата', 'зарплата,зп,аванс,оклад'),
            ('Подработка', 'подработка,фриланс,халтура,заказ'),
            ('Кэшбэк', 'кэшбэк,cashback,возврат'),
            ('Подарок', 'подарок,подарили,дарили'),
            ('Перевод', 'перевод,переводом,скинули'),
            ('Другой доход', '')
        ]
        
        self.cursor.execute('DELETE FROM income_categories')
        
        for category, keywords in income_categories:
            self.cursor.execute(
                'INSERT INTO income_categories (name, keywords) VALUES (?, ?)',
                (category, keywords)
            )
        
        self.connection.commit()
    
    def add_expense(self, user_id: int, amount: float, category: str, description: str = '', is_income: bool = False):
        date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.cursor.execute(
            'INSERT INTO expenses (user_id, amount, category, description, date, is_income) VALUES (?, ?, ?, ?, ?, ?)',
            (user_id, amount, category, description, date, 1 if is_income else 0)
        )
        self.connection.commit()
        return self.cursor.lastrowid
    
    def get_month_expenses(self, user_id: int, year: int, month: int) -> List[Dict]:
        self.cursor.execute('''
            SELECT amount, category, description, date, is_income
            FROM expenses 
            WHERE user_id = ? 
            AND strftime('%Y', date) = ? 
            AND strftime('%m', date) = ?
            AND is_income = 0
            ORDER BY date DESC
        ''', (user_id, str(year), f'{month:02d}'))
        
        rows = self.cursor.fetchall()
        return [
            {
                'amount': row[0],
                'category': row[1],
                'description': row[2],
                'date': row[3]
            }
            for row in rows
        ]
    
    def get_month_income(self, user_id: int, year: int, month: int) -> List[Dict]:
        self.cursor.execute('''
            SELECT amount, category, description, date
            FROM expenses 
            WHERE user_id = ? 
            AND strftime('%Y', date) = ? 
            AND strftime('%m', date) = ?
            AND is_income = 1
            ORDER BY date DESC
        ''', (user_id, str(year), f'{month:02d}'))
        
        rows = self.cursor.fetchall()
        return [
            {
                'amount': row[0],
                'category': row[1],
                'description': row[2],
                'date': row[3]
            }
            for row in rows
        ]
    
    def get_category_keywords(self) -> Dict[str, List[str]]:
        self.cursor.execute('SELECT name, keywords FROM categories')
        result = {}
        for name, keywords in self.cursor.fetchall():
            if keywords:
                result[name] = [k.strip() for k in keywords.split(',')]
            else:
                result[name] = []
        return result
    
    def get_income_category_keywords(self) -> Dict[str, List[str]]:
        self.cursor.execute('SELECT name, keywords FROM income_categories')
        result = {}
        for name, keywords in self.cursor.fetchall():
            if keywords:
                result[name] = [k.strip() for k in keywords.split(',')]
            else:
                result[name] = []
        return result
    
    def get_last_expenses(self, user_id: int, limit: int = 10) -> List[Dict]:
        self.cursor.execute('''
            SELECT id, amount, category, description, date, is_income
            FROM expenses 
            WHERE user_id = ? 
            ORDER BY date DESC
            LIMIT ?
        ''', (user_id, limit))
        
        rows = self.cursor.fetchall()
        return [
            {
                'id': row[0],
                'amount': row[1],
                'category': row[2],
                'description': row[3],
                'date': row[4],
                'is_income': row[5]
            }
            for row in rows
        ]
    
    def get_expense_by_id(self, expense_id: int, user_id: int) -> Dict:
        self.cursor.execute('''
            SELECT id, amount, category, description, date, is_income
            FROM expenses 
            WHERE id = ? AND user_id = ?
        ''', (expense_id, user_id))
        
        row = self.cursor.fetchone()
        if row:
            return {
                'id': row[0],
                'amount': row[1],
                'category': row[2],
                'description': row[3],
                'date': row[4],
                'is_income': row[5]
            }
        return None
    
    def delete_expense(self, expense_id: int, user_id: int) -> bool:
        self.cursor.execute('''
            DELETE FROM expenses 
            WHERE id = ? AND user_id = ?
        ''', (expense_id, user_id))
        self.connection.commit()
        return self.cursor.rowcount > 0
    
    def update_expense(self, expense_id: int, user_id: int, amount: float = None, 
                       category: str = None, description: str = None) -> bool:
        expense = self.get_expense_by_id(expense_id, user_id)
        if not expense:
            return False
        
        new_amount = amount if amount is not None else expense['amount']
        new_category = category if category is not None else expense['category']
        new_description = description if description is not None else expense['description']
        
        self.cursor.execute('''
            UPDATE expenses 
            SET amount = ?, category = ?, description = ?
            WHERE id = ? AND user_id = ?
        ''', (new_amount, new_category, new_description, expense_id, user_id))
        self.connection.commit()
        return self.cursor.rowcount > 0
    
    def delete_last_expense(self, user_id: int) -> Dict:
        last = self.get_last_expenses(user_id, limit=1)
        if last:
            expense = last[0]
            self.delete_expense(expense['id'], user_id)
            return expense
        return None
    
    def get_month_balance(self, user_id: int, year: int, month: int) -> float:
        self.cursor.execute('''
            SELECT COALESCE(SUM(amount), 0)
            FROM expenses 
            WHERE user_id = ? 
            AND strftime('%Y', date) = ? 
            AND strftime('%m', date) = ?
            AND is_income = 1
        ''', (user_id, str(year), f'{month:02d}'))
        income = self.cursor.fetchone()[0]
        
        self.cursor.execute('''
            SELECT COALESCE(SUM(amount), 0)
            FROM expenses 
            WHERE user_id = ? 
            AND strftime('%Y', date) = ? 
            AND strftime('%m', date) = ?
            AND is_income = 0
        ''', (user_id, str(year), f'{month:02d}'))
        expenses = self.cursor.fetchone()[0]
        
        return income - expenses
    
    def get_total_balance(self, user_id: int, up_to_year: int, up_to_month: int) -> float:
        current_month_start = f"{up_to_year}-{up_to_month:02d}-01"
        
        self.cursor.execute('''
            SELECT COALESCE(SUM(amount), 0)
            FROM expenses 
            WHERE user_id = ? 
            AND date < ?
            AND is_income = 1
        ''', (user_id, current_month_start))
        total_income = self.cursor.fetchone()[0]
        
        self.cursor.execute('''
            SELECT COALESCE(SUM(amount), 0)
            FROM expenses 
            WHERE user_id = ? 
            AND date < ?
            AND is_income = 0
        ''', (user_id, current_month_start))
        total_expenses = self.cursor.fetchone()[0]
        
        return total_income - total_expenses
    
    def close(self):
        self.connection.close()