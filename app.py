from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import json

app = Flask(__name__, template_folder='templates')
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(
    os.path.abspath(os.path.dirname(__file__)), 'ogers.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


# === МОДЕЛИ ===

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    progress = db.relationship('UserProgress', backref='user', uselist=False)
    completed_tasks = db.relationship('UserTask', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class UserProgress(db.Model):
    __tablename__ = 'user_progress'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    theme1_completed = db.Column(db.Boolean, default=False)  # Синтаксис
    theme2_completed = db.Column(db.Boolean, default=False)  # Пунктуация
    theme3_completed = db.Column(db.Boolean, default=False)  # Орфография
    theme4_completed = db.Column(db.Boolean, default=False)  # Лексика


class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    question = db.Column(db.Text, nullable=False)
    options = db.Column(db.Text)
    correct_answer = db.Column(db.String(10), nullable=False)
    explanation = db.Column(db.Text)
    category = db.Column(db.String(100))
    difficulty = db.Column(db.String(20), default="Средний")
    points = db.Column(db.Integer, default=1)


class UserTask(db.Model):
    __tablename__ = 'user_tasks'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    user_answer = db.Column(db.String(10))
    is_correct = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# === СОЗДАНИЕ ТАБЛИЦ И ТЕСТОВЫХ ЗАДАНИЙ ===
with app.app_context():
    db.create_all()
    if Task.query.count() == 0:
        sample_tasks = [
            # Орфография
            Task(title="Н/НН в прилагательных",
                 description="Выберите правильный вариант написания",
                 question="В каком слове на месте пропуска пишется НН?",
                 options=json.dumps(["А) кожа...ый", "Б) ветре...ый", "В) карма...ый", "Г) гуси...ый"]),
                 correct_answer="В",
                 explanation="В суффиксах -ЕНН-, -ОНН- пишется НН. Карманный – от карман + н.",
                 category="Орфография",
                 difficulty="Высокий"),
            Task(title="Н/НН в причастиях",
                 description="Выберите правильный вариант написания",
                 question="В каком слове пишется Н?",
                 options=json.dumps(["А) жарен...ая картошка", "Б) решён...ая задача", "В) крашен...ый забор", "Г) куплен...ый билет"]),
                 correct_answer="В",
                 explanation="Отглагольное прилагательное без зависимых слов – крашеный (одна Н).",
                 category="Орфография",
                 difficulty="Средний"),
            Task(title="Корни с чередованием",
                 description="Выберите правильную букву",
                 question="В каком слове пишется буква А?",
                 options=json.dumps(["А) заг...реть", "Б) прик...снуться", "В) р...сток", "Г) выр...щенный"]),
                 correct_answer="Г",
                 explanation="В корне -раст-/-ращ- пишется А перед СТ и Щ.",
                 category="Орфография",
                 difficulty="Средний"),
            Task(title="Правописание приставок ПРЕ-/ПРИ-",
                 description="Выберите правильный вариант",
                 question="В каком слове пишется приставка ПРЕ-?",
                 options=json.dumps(["А) пр...морский", "Б) пр...одолеть", "В) пр...клеить", "Г) пр...встать"]),
                 correct_answer="Б",
                 explanation="ПРЕ- в значении 'очень' или 'пере-': преодолеть = переодолеть.",
                 category="Орфография",
                 difficulty="Средний"),
            Task(title="Правописание суффиксов -К- и -СК-",
                 description="Выберите правильный вариант",
                 question="В каком слове пишется суффикс -СК-?",
                 options=json.dumps(["А) матрос...ий", "Б) немец...ий", "В) турист...ий", "Г) казац...ий"]),
                 correct_answer="В",
                 explanation="Суффикс -СК- пишется в относительных прилагательных (туристский).",
                 category="Орфография",
                 difficulty="Низкий"),
            # Пунктуация
            Task(title="Пунктуация при вводных словах",
                 description="Расставьте знаки препинания",
                 question="В каком варианте ответа правильно указаны все цифры, на месте которых должны стоять запятые?",
                 options=json.dumps(["А) Конечно(1) вы(2) правы.", "Б) Конечно(1) вы(2) правы."]),
                 correct_answer="А",
                 explanation="Вводное слово 'конечно' выделяется запятой (цифра 1).",
                 category="Пунктуация",
                 difficulty="Средний"),
            Task(title="Знаки препинания при однородных членах",
                 description="Расставьте запятые",
                 question="В каком предложении нужно поставить одну запятую?",
                 options=json.dumps(["А) И днём и ночью кот учёный всё ходит по цепи кругом.", "Б) Он был ни жив ни мёртв.", "В) В саду росли и яблони и груши и сливы.", "Г) Мал золотник да дорог."]),
                 correct_answer="Г",
                 explanation="Противопоставление с союзом 'да' (=но) – ставится запятая.",
                 category="Пунктуация",
                 difficulty="Средний"),
            Task(title="Пунктуация в сложносочинённом предложении",
                 description="Укажите правильную расстановку запятых",
                 question="На месте каких цифр должны стоять запятые? 'Солнце уже спряталось(1) и ночные тени надвигались(2) но мы(3) всё ещё сидели на берегу(4) и смотрели на воду.'",
                 options=json.dumps(["А) 1,2,3,4", "Б) 1,2", "В) 2,3", "Г) 1,2,4"]),
                 correct_answer="Б",
                 explanation="Запятая между частями ССП перед 'и' (1), и перед 'но' (2).",
                 category="Пунктуация",
                 difficulty="Высокий"),
            Task(title="Пунктуация при причастном обороте",
                 description="Найдите предложение с обособленным определением",
                 question="В каком предложении причастный оборот выделяется запятыми?",
                 options=json.dumps(["А) Дорога освещённая луной казалась таинственной.", "Б) Освещённая луной дорога казалась таинственной.", "В) Дорога освещённая луной казалась таинственной.", "Г) Дорога, освещённая луной, казалась таинственной."]),
                 correct_answer="Г",
                 explanation="Причастный оборот, стоящий после определяемого слова, обособляется.",
                 category="Пунктуация",
                 difficulty="Средний"),
            # Синтаксис
            Task(title="Виды подчинительной связи",
                 description="Определите тип связи в словосочетании",
                 question="Какое словосочетание построено по типу 'примыкание'?",
                 options=json.dumps(["А) читать книгу", "Б) очень интересный", "В) дом из дерева", "Г) мой друг"]),
                 correct_answer="Б",
                 explanation="Примыкание – связь по смыслу с неизменяемым словом (наречием).",
                 category="Синтаксис",
                 difficulty="Средний"),
            Task(title="Грамматическая основа предложения",
                 description="Найдите грамматическую основу",
                 question="Какая пара слов является грамматической основой в предложении: 'Всё в доме было готово к приезду гостей.'?",
                 options=json.dumps(["А) всё было", "Б) всё было готово", "В) было готово", "Г) всё готово"]),
                 correct_answer="Б",
                 explanation="Подлежащее 'всё', составное именное сказуемое 'было готово'.",
                 category="Синтаксис",
                 difficulty="Низкий"),
            Task(title="Односоставные предложения",
                 description="Определите тип предложения",
                 question="Какое предложение является безличным?",
                 options=json.dumps(["А) Люблю грозу в начале мая.", "Б) Мне не спится.", "В) В дверь постучали.", "Г) Цыплят по осени считают."]),
                 correct_answer="Б",
                 explanation="Безличное предложение выражает состояние, нет и не может быть подлежащего.",
                 category="Синтаксис",
                 difficulty="Средний"),
            # Лексика
            Task(title="Синонимы и антонимы",
                 description="Подберите синоним",
                 question="Какое слово является синонимом к слову 'алчный'?",
                 options=json.dumps(["А) щедрый", "Б) жадный", "В) добрый", "Г) скупой"]),
                 correct_answer="Б",
                 explanation="Алчный – стремящийся к наживе, жадный.",
                 category="Лексика",
                 difficulty="Низкий"),
            Task(title="Фразеологизмы",
                 description="Замените выражение синонимичным фразеологизмом",
                 question="Каким фразеологизмом можно заменить слово 'бездельничать'?",
                 options=json.dumps(["А) бить баклуши", "Б) вешать лапшу на уши", "В) брать быка за рога", "Г) вставлять палки в колёса"]),
                 correct_answer="А",
                 explanation="Бить баклуши – бездельничать.",
                 category="Лексика",
                 difficulty="Низкий"),
            # Средства выразительности
            Task(title="Тропы и фигуры речи",
                 description="Определите средство выразительности",
                 question="Какое средство выразительности использовано в выражении 'горькая радость'?",
                 options=json.dumps(["А) метафора", "Б) оксюморон", "В) эпитет", "Г) сравнение"]),
                 correct_answer="Б",
                 explanation="Оксюморон – сочетание несочетаемого (горькая радость).",
                 category="Средства выразительности",
                 difficulty="Высокий"),
        ]
        db.session.add_all(sample_tasks)
        db.session.commit()


# === МАРШРУТЫ ===

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')

        if not username or len(username) < 3:
            flash('Имя пользователя должно содержать минимум 3 символа', 'error')
            return render_template('register.html')

        if not email or '@' not in email:
            flash('Введите корректный email', 'error')
            return render_template('register.html')

        if len(password) < 6:
            flash('Пароль должен содержать минимум 6 символов', 'error')
            return render_template('register.html')

        if password != password_confirm:
            flash('Пароли не совпадают', 'error')
            return render_template('register.html')

        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким именем уже существует', 'error')
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('Пользователь с таким email уже зарегистрирован', 'error')
            return render_template('register.html')

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # Создаём запись прогресса
        progress = UserProgress(user_id=user.id)
        db.session.add(progress)
        db.session.commit()

        flash('Регистрация успешна! Теперь вы можете войти.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))

    if request.method == 'POST':
        login_input = request.form.get('login', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter(
            (User.username == login_input) | (User.email == login_input.lower())
        ).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('profile'))
        else:
            flash('Неверное имя пользователя/email или пароль', 'error')

    return render_template('login.html')


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/profile')
@login_required
def profile():
    progress = UserProgress.query.filter_by(user_id=current_user.id).first()
    completed_tasks = UserTask.query.filter_by(user_id=current_user.id, completed=True).all()
    task_details = []
    for ut in completed_tasks:
        task = Task.query.get(ut.task_id)
        if task:
            task_details.append({'task': task, 'is_correct': ut.is_correct, 'completed_at': ut.completed_at})

    if progress:
        themes = [progress.theme1_completed, progress.theme2_completed,
                  progress.theme3_completed, progress.theme4_completed]
        completed = sum(themes)
        percent = int((completed / 4) * 100)
    else:
        percent = 0

    return render_template('profile.html', user=current_user, progress=progress, percent=percent,
                           completed_tasks=task_details)


@app.route('/tasks')
@login_required
def tasks():
    all_tasks = Task.query.all()
    categories = {}
    for task in all_tasks:
        cat = task.category or "Без категории"
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(task)
    return render_template('tasks.html', categories=categories)


@app.route('/task/<int:task_id>')
@login_required
def view_task(task_id):
    task = Task.query.get_or_404(task_id)
    user_task = UserTask.query.filter_by(user_id=current_user.id, task_id=task_id).first()
    options = json.loads(task.options) if task.options else []
    return render_template('task.html', task=task, options=options, user_task=user_task)


@app.route('/task/<int:task_id>/submit', methods=['POST'])
@login_required
def submit_task(task_id):
    task = Task.query.get_or_404(task_id)
    answer = request.form.get('answer')
    is_correct = (answer == task.correct_answer)

    user_task = UserTask.query.filter_by(user_id=current_user.id, task_id=task_id).first()
    if not user_task:
        user_task = UserTask(user_id=current_user.id, task_id=task_id)
        db.session.add(user_task)

    user_task.completed = True
    user_task.user_answer = answer
    user_task.is_correct = is_correct
    user_task.completed_at = datetime.utcnow()
    db.session.commit()

    flash(f'Ответ {"правильный" if is_correct else "неправильный"}. {task.explanation}',
          'success' if is_correct else 'error')
    return redirect(url_for('view_task', task_id=task_id))


@app.route('/update_checklist', methods=['POST'])
@login_required
def update_checklist():
    data = request.get_json()
    theme_id = data.get('theme')
    checked = data.get('checked')
    progress = UserProgress.query.filter_by(user_id=current_user.id).first()
    if progress:
        if theme_id == 'theme1':
            progress.theme1_completed = checked
        elif theme_id == 'theme2':
            progress.theme2_completed = checked
        elif theme_id == 'theme3':
            progress.theme3_completed = checked
        elif theme_id == 'theme4':
            progress.theme4_completed = checked
        db.session.commit()
    return jsonify({'status': 'ok'})


@app.route('/theory')
@login_required
def theory():
    return render_template('theory.html')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)