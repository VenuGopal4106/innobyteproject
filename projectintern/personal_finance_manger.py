import sqlite3
import hashlib
import getpass
from datetime import datetime
import shutil

# Database Class to handle SQLite operations
class Database:
    def __init__(self, db_name="finance_app.db"):
        self.db_name=db_name
        self.connection = sqlite3.connect(db_name)
        self.cursor = self.connection.cursor()
        self.create_users_table()
        self.create_transactions_table()
        self.create_budgets_table()

    def create_users_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)
        self.connection.commit()
        
    def create_transactions_table(self):
        self.cursor.execute("""
                            CREATE TABLE IF NOT EXISTS transactions(
                                id INTEGER PRIMARY KEY,
                                user_id INTEGER,
                                amount REAL,
                                type TEXT,
                                category TEXT,
                                date TEXT,
                                FOREIGN KEY(user_id) REFERENCES user(id)
                            )""")
        self.connection.commit()
    def create_budgets_table(self):
        self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                category TEXT,
                amount REAL,
                month TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
                )
                """)
        self.connection.commit()
    def backup_data(self, backup_file="finance_backup.db"):
        try:
            shutil.copy(self.db_name, backup_file)
            print(f"Backup created successfully as {backup_file}")
        except Exception as e:
            print(f"Error during backup: {e}")
    def restore_data(self, backup_file="finance_backup.db"):
        """Restore the database from a backup file."""
        try:
            shutil.copy(backup_file, self.db_name)
            print(f"Data restored successfully from {backup_file}")
            # Reconnect to the restored database
            self.connection = sqlite3.connect(self.db_name)
            self.cursor = self.connection.cursor()
        except Exception as e:
            print(f"Error during restore: {e}")

    def close(self):
        self.connection.close()

# Function to register a new user
def register_user(db, username, password):
    # Hash the password for secure storage
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    
    try:
        # Insert the new user into the users table
        db.cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
        db.connection.commit()
        print("Registration successful.")
    except sqlite3.IntegrityError:
        print("Error: Username already exists. Please choose another username.")

# Function to authenticate an existing user
def authenticate_user(db, username, password):
    # Hash the password to compare with stored password hash
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    db.cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, hashed_password))
    user = db.cursor.fetchone()
    
    if user:
        print("Login successful.")
        return True
    else:
        print("Login failed: Incorrect username or password.")
        return False
    
def add_transaction(db, user_id, amount, trans_type, category):
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.cursor.execute("""INSERT INTO transactions (user_id, amount, type, category, date)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, amount, trans_type, category, date))
    db.connection.commit()
    print("Transaction added successfully.")
    

def update_transaction(db,transaction_id,amount,trans_type,category):
    db.cursor.execute("""
                      UPDATE transactions
                      SET  amount=?,type=?,category=?,date=?
                      WHERE id=?
                      """,(amount,trans_type,category,datetime.now().strftime("%Y-%m-%d %H:%M:%S"),transaction_id))
    db.connection.commit()
    print("Transaction updated successfully.")

def delete_transaction(db,transaction_id):
    db.cursor.execute("DELETE FROM transactions WHERE id=?",(transaction_id))
    db.connection.commit()
    print("transaction deleted successfully.")

def view_transactions(db, user_id):
    db.cursor.execute("SELECT * FROM transactions WHERE user_id = ?", (user_id,))
    transactions = db.cursor.fetchall()
    
    if transactions:
        print("\n--- Transactions ---")
        for trans in transactions:
            print(f"ID: {trans[0]}, Amount: {trans[2]}, Type: {trans[3]}, Category: {trans[4]}, Date: {trans[5]}")
    else:
        print("No transactions found.")

def montly_report(db,user_id):
    db.cursor.execute("""
        SELECT
            strftime('%Y-%m', date) AS month,
            SUM(CASE WHEN type = "income" THEN amount ELSE 0 END) AS total_income,
            SUM(CASE WHEN type = "expense" THEN amount ELSE 0 END) AS total_expense
        FROM transactions
        WHERE user_id=?
        GROUP BY month
        ORDER BY month DESC
            """,(user_id,))   
    report=db.cursor.fetchall()
    print("\n--- Monthly Financial Report ---")
    for row in report:
        month,income,expense=row 
        savings=income-expense
        if savings>0:
            s=savings
            print(f"Month: {month}, Income: {income}, Expense: {expense}, Savings: {s}")
        else:
            s=0 
            print(f"Month: {month}, Income: {income}, Expense: {expense}, Savings: {s}") 

def yearly_report(db, user_id):
    db.cursor.execute("""
        SELECT 
            strftime('%Y', date) AS year, 
            SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) AS total_income,
            SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) AS total_expense
        FROM transactions 
        WHERE user_id = ?
        GROUP BY year
        ORDER BY year DESC
    """, (user_id,))
    
    report = db.cursor.fetchall()
    
    print("\n--- Yearly Financial Report ---")
    for row in report:
        year, income, expense = row
        savings = income - expense
        if savings>0:
            s=savings
            print(f"Year: {year}, Income: {income}, Expense: {expense}, Savings: {s}")
        else:
            s=0
            print(f"Year: {year}, Income: {income}, Expense: {expense}, Savings: {s}")

def set_budget(db, user_id, category, amount, month):
    db.cursor.execute("""
        INSERT OR REPLACE INTO budgets (user_id, category, amount, month)
        VALUES (?, ?, ?, ?)
    """, (user_id, category, amount, month))
    db.connection.commit()
    print(f"Budget set for {category} in {month}: ${amount}")


def check_budget(db, user_id, month):
    # Get all budgets for the user for the specified month
    db.cursor.execute("""
        SELECT category, amount FROM budgets
        WHERE user_id = ? AND month = ?
    """, (user_id, month))
    budgets = db.cursor.fetchall()

    print(f"\n--- Budget Check for {month} ---")
    for category, budget_amount in budgets:
        # Calculate total expenses for this category in the given month
        db.cursor.execute("""
            SELECT SUM(amount) FROM transactions
            WHERE user_id = ? AND type = 'expense' AND category = ? AND strftime('%Y-%m', date) = ?
        """, (user_id, category, month))
        total_expense = db.cursor.fetchone()[0] or 0  # Default to 0 if no expenses

        if total_expense > budget_amount:
            print(f"Warning: You exceeded your budget for {category}! Budget: ${budget_amount}, Spent: ${total_expense}")
        else:
            print(f"{category} - Budget: ${budget_amount}, Spent: ${total_expense}, Remaining: ${budget_amount - total_expense}")
        
               
def main():
    db = Database()
    user_id=None

    while True:
        print("\n--- Personal Finance Manager ---")
        print("1. Register")
        print("2. Login")
        print("3. add Transaction")
        print("4. update Transaction")
        print("5. Delete Transaction")
        print("6. view Transactions")
        print("7. Monthly Report")
        print("8. Yearly Report")
        print("9. Set Budget")
        print("10. Check Budget")
        print("11. Backup Data")
        print("12. Restore Data")
        print("13. Exit")
        choice = input("Choose an option: ")

        if choice == "1":
            username = input("Enter username: ")
            password = getpass.getpass("Enter password: ")
            register_user(db, username, password)

        elif choice == "2":
            username = input("Enter username: ")
            password = getpass.getpass("Enter password: ")
            if authenticate_user(db, username, password):
                user_id=db.cursor.execute("SELECT id FROM users WHERE username=?",(username,)).fetchone()[0]
                print("Welcome to your personal finance dashboard!")

        elif choice == "3" and user_id:
            amount = float(input("Enter amount: "))
            trans_type = input("Enter type (income/expense): ")
            category = input("Enter category (e.g., Food, Rent, Salary): ")
            add_transaction(db, user_id, amount, trans_type, category)

        elif choice == "4" and user_id:
            transaction_id = int(input("Enter transaction ID to update: "))
            amount = float(input("Enter new amount: "))
            trans_type = input("Enter new type (income/expense): ")
            category = input("Enter new category: ")
            update_transaction(db, transaction_id, amount, trans_type, category)

        elif choice == "5" and user_id:
            transaction_id = input("Enter transaction ID to delete: ")
            delete_transaction(db, transaction_id)

        elif choice == "6" and user_id:
            if isinstance(user_id, int):
                    view_transactions(db, user_id)
            else:
                print("Error: Invalid user ID. Please log in again.")
        elif choice =="7" and user_id:
            montly_report(db,user_id)
            
        elif choice=="8" and user_id:
            yearly_report(db,user_id)
        
        elif choice == "9" and user_id:
            category = input("Enter category to set budget (e.g., Food, Rent): ")
            amount = float(input("Enter budget amount: "))
            month = input("Enter month (format YYYY-MM): ")
            set_budget(db, user_id, category, amount, month)

        elif choice == "10" and user_id:
            month = input("Enter month to check budget (format YYYY-MM): ")
            check_budget(db, user_id, month)
        elif choice == "11":
            backup_file = input("Enter backup file name (e.g., finance_backup.db): ")
            db.backup_data(backup_file)

        elif choice == "12":
            restore_file = input("Enter restore file name (e.g., finance_backup.db): ")
            db.restore_data(restore_file)
            print("Please log in again after restoring data.")

            
        elif choice == "13":
            print("Exiting the application.")
            db.close()
            break

        else:
            print("Invalid choice or you are not logged in. Please enter a valid option.")

if __name__ == "__main__":
    main()

