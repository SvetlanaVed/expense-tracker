# from typing import Annotated
import sqlite3, datetime
from fastapi import FastAPI, Request, Form, HTTPException
from pydantic import BaseModel
from decimal import Decimal
from pprint import pprint
import uvicorn
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse

CATEGORIES = {
    "food": "Food",
    "rent": "Rent",
    "health": "Health",
    "fun": "Fun",
    "auto": "Auto",
    "work": "Work/Education",
    "other": "Other",
}

class Expense(BaseModel):
    category: str
    amount: Decimal
    date: str

class ExpenseRepository:
    def __init__(self, path: str):
        self.connection = self.create_connection(path)

        self.create_scheme()

    def create_connection(self, path:str):
        connection = None
        try:
            connection = sqlite3.connect(path, isolation_level=None)
            print("DB is ready")

        except sqlite3.Error as error:
            raise error

        connection.row_factory = sqlite3.Row

        return connection

    def create_scheme(self):
        cursor = self.connection.cursor()

        cursor.execute('''
                    CREATE TABLE IF NOT EXISTS expenses(
                    id INTEGER PRIMARY KEY,
                    category TEXT,
                    amount REAL,
                    date TEXT
                    )
                    ''')

    def create_expense(self, expense: Expense):
        sql = '''INSERT INTO expenses (category, amount, date) VALUES (?, ?, ?) RETURNING id;'''
        cursor = self.connection.cursor()
        res = cursor.execute(sql, (expense.category, float(expense.amount), expense.date))
        print(res)
        row = cursor.fetchone()
        (inserted_id,) = row if row else None

        self.connection.commit()

        return self.get_expense_by_id(inserted_id)

    def get_expenses(self):
        cursor = self.connection.cursor()
        res = cursor.execute('SELECT * FROM expenses ORDER BY datetime(date) DESC')
        expenses = cursor.fetchall()

        for expense in expenses:
            print(expense)

        return expenses

    def get_total(self):
        cursor = self.connection.cursor()
        cursor.execute('SELECT SUM(amount) AS total FROM expenses')
        total_exp = cursor.fetchone()

        print('Row total expense', total_exp[0])
        # print('Row total expense', total_exp['total'])
        return total_exp[0]

    def get_expense_by_id(self, id:int):
        cursor = self.connection.cursor()
        res = cursor.execute('SELECT * FROM expenses WHERE id=?', [id])

        return res.fetchone()

    def delete_expenses(self, id:int):
        cursor = self.connection.cursor()
        deleted_expense = cursor.execute('DELETE FROM expenses WHERE id=?', [id])
        print(deleted_expense)

        return

def get_db():
    db = ExpenseRepository('expenses.db')
    return db

app = FastAPI()

templates = Jinja2Templates(directory="templates")

def is_date_valid(date: str):
    try:
        datetime.datetime.fromisoformat(date)
    except Exception as e:
        print(e)
        return False
    return True

# my_expenses = []
# total_exp = 0
# expense_counter = 0
# storage = {"expenses": [], "counter": 0}
# current_date = datetime.date.today().isoformat()
# print(current_date)


# def create_connection(path: str):
#     connection = None
#     try:
#         connection = sqlite3.connect(path)
#         print("DB esta lista")
#
#     except sqlite3.Error as error:
#         print("Bla", error)
#
#     return connection


# def create_expenses(connection, expenses):
#     sql = '''INSERT INTO expenses (id, category, amount) VALUES (?, ?, ?)'''
#     cursor = connection.cursor()
#     cursor.execute(sql, expenses)
#     connection.commit()
#
#     return cursor.lastrowid


# def main():
#     database = 'expenses.db'
#
#     connection = create_connection(database)



    # cursor.executemany('INSERT INTO Expenses (id, category, amount) VALUES (?, ?, ?)', my_expenses)



# @app.get('/')
# async def root():
#     return {'test': 'Testing the test', 'data': 0}

@app.get('/expenses')
def get_expenses():
    res2 = get_db().get_expenses()
    return {'data': res2}

def controller_add_expense(expense: Expense):
    if expense.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount > 0")
    if expense.category not in CATEGORIES:
        raise HTTPException(status_code=400, detail="Invalid category")
    if not is_date_valid(expense.date):
        raise HTTPException(status_code=400, detail="Invalid date format")

    return get_db().create_expense(expense)

@app.post('/expenses')
def add_expenses(expense: Expense):
    return controller_add_expense(expense)
    # e = expense.model_dump()
    # my_expenses.append(e)


# @app.post("/add-expense", response_class=HTMLResponse)
# async def add_expense(request: Request, category: Annotated[str, Form()], amount: Annotated[Decimal, Form()]):
#     e = {"category": category, "amount": amount}
#     my_expenses.append(e)
#     return templates.TemplateResponse("list.html", {"request": request, "expenses": my_expenses})

@app.post("/add-expense")
# async def add_expense(request: Request, category: Annotated[str, Form()], amount: Annotated[Decimal, Form()]):
async def add_expense(request: Request, category: str = Form(), amount: Decimal = Form(), date: str = Form()):
    expense = Expense(category=category, amount=amount, date=date)
    controller_add_expense(expense)
    # get_db().create_expense(expense)
    # global expense_counter
    # expense_counter += 1
    # storage["counter"] += 1
    # e = {"category": category, "amount": amount, "id": storage["counter"]}
    # my_expenses.append(e)
    # pprint(e)
    return RedirectResponse("/list", status_code=301)

@app.get("/delete-expense/{id}")
async def delete_expense_by_link (id: int):
    get_db().delete_expenses(id)

    return RedirectResponse("/list", status_code=301)

# Delete expenses
@app.delete("/expenses/{id}")
def delete_expense(id: int):
    res = get_db().delete_expenses(id)
    print(res)
    return res


@app.get("/list", response_class=HTMLResponse)
async def list_expenses(request: Request):
    my_expenses = get_db().get_expenses()
    total_exp = get_db().get_total()
    print('Your total is:', total_exp)
    # ADD TOTAL
    return templates.TemplateResponse("list.html", {
        "request": request,
        "expenses": my_expenses,
        "total_exp": total_exp,
        "CATEGORIES": CATEGORIES
    })


app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8000)
