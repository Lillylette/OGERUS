from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    return "Страница входа (в разработке)"

@app.route('/register')
def register():
    return "Страница регистрации (в разработке)"

@app.route('/profile')
def profile():
    return "Личный кабинет (в разработке)"

@app.route('/tasks')
def tasks():
    return "Каталог заданий (в разработке)"

@app.route('/theory')
def theory():
    return "Теория к ОГЭ (в разработке)"

if __name__ == '__main__':
    app.run(debug=True)