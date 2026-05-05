from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from models import db, User, UserProgress, ChecklistItem, UserAchievement
from datetime import datetime
import os
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(
    os.path.abspath(os.path.dirname(__file__)), 'ogers.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.route('/')
def index():
    return render_template('index.html')


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


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))

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

        flash('Регистрация успешна! Теперь вы можете войти.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)


@app.route('/upload_avatar', methods=['POST'])
@login_required
def upload_avatar():
    if 'avatar' not in request.files:
        flash('Файл не выбран', 'error')
        return redirect(url_for('profile'))

    file = request.files['avatar']
    if file.filename == '':
        flash('Файл не выбран', 'error')
        return redirect(url_for('profile'))

    if file:
        ext = file.filename.rsplit('.', 1)[-1].lower()
        filename = secure_filename(f"user_{current_user.id}.{ext}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        current_user.avatar = f'/static/uploads/{filename}'
        db.session.commit()
        flash('Аватар успешно обновлён', 'success')

    return redirect(url_for('profile'))


@app.route('/api/progress_data')
@login_required
def progress_data():
    skills = ['Орфография', 'Пунктуация', 'Анализ текста', 'Изложение', 'Сочинение']
    skill_scores = {}
    total_by_skill = {skill: 0 for skill in skills}
    completed_by_skill = {skill: 0 for skill in skills}

    progress_records = UserProgress.query.filter_by(user_id=current_user.id).all()

    for record in progress_records:
        if record.skill in total_by_skill:
            total_by_skill[record.skill] += 1
            if record.completed:
                completed_by_skill[record.skill] += 1

    for skill in skills:
        if total_by_skill[skill] > 0:
            skill_scores[skill] = round((completed_by_skill[skill] / total_by_skill[skill]) * 100)
        else:
            skill_scores[skill] = 0

    return jsonify(skill_scores)


@app.route('/api/problem_topics')
@login_required
def problem_topics():
    problem_topics = []
    progress_records = UserProgress.query.filter_by(user_id=current_user.id).all()

    for record in progress_records:
        if record.total_attempts > 0:
            success_rate = (record.correct_attempts / record.total_attempts) * 100
            if success_rate < 60 and not record.completed:
                problem_topics.append({
                    'id': record.topic_id,
                    'name': record.topic_name,
                    'success_rate': round(success_rate)
                })

    problem_topics.sort(key=lambda x: x['success_rate'])
    return jsonify(problem_topics[:10])


@app.route('/api/checklist', methods=['GET'])
@login_required
def get_checklist():
    items = ChecklistItem.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        'id': item.id,
        'topic_id': item.topic_id,
        'topic_name': item.topic_name,
        'checked': item.checked
    } for item in items])


@app.route('/api/checklist/toggle/<int:item_id>', methods=['POST'])
@login_required
def toggle_checklist(item_id):
    item = ChecklistItem.query.filter_by(id=item_id, user_id=current_user.id).first()
    if item:
        item.checked = not item.checked
        db.session.commit()
        return jsonify({'success': True, 'checked': item.checked})
    return jsonify({'success': False, 'error': 'Item not found'}), 404


@app.route('/api/checklist/init', methods=['POST'])
@login_required
def init_checklist():
    existing = ChecklistItem.query.filter_by(user_id=current_user.id).first()
    if existing:
        return jsonify({'success': True, 'message': 'Checklist already exists'})

    topics = [
        (1, 'Сжатое изложение'),
        (2, 'Сочинение-рассуждение'),
        (3, 'Выразительные средства лексики и фразеологии'),
        (4, 'Правописание приставок'),
        (5, 'Правописание суффиксов'),
        (6, 'Правописание Н и НН'),
        (7, 'Слитное и раздельное написание НЕ'),
        (8, 'Знаки препинания в простом предложении'),
        (9, 'Знаки препинания в сложном предложении'),
        (10, 'Анализ текста'),
    ]

    for topic_id, topic_name in topics:
        item = ChecklistItem(
            user_id=current_user.id,
            topic_id=topic_id,
            topic_name=topic_name,
            checked=False
        )
        db.session.add(item)

    db.session.commit()
    return jsonify({'success': True})


@app.route('/api/achievements')
@login_required
def get_achievements():
    earned = UserAchievement.query.filter_by(user_id=current_user.id).all()
    earned_ids = [a.achievement_id for a in earned]

    all_achievements = [
        {'id': 1, 'name': 'Первые шаги', 'description': 'Завершено 5 заданий', 'icon': '🌟'},
        {'id': 2, 'name': 'Знаток орфографии', 'description': '100% тем по орфографии', 'icon': '📝'},
        {'id': 3, 'name': 'Мастер пунктуации', 'description': '100% тем по пунктуации', 'icon': '🔖'},
        {'id': 4, 'name': 'Аналитик', 'description': '100% тем по анализу текста', 'icon': '🔍'},
        {'id': 5, 'name': 'Серебряный птенец', 'description': 'Решено 25 заданий', 'icon': '🥈'},
        {'id': 6, 'name': 'Золотой соловей', 'description': 'Решено 50 заданий', 'icon': '🥇'},
        {'id': 7, 'name': 'Трудоголик', 'description': 'Занимался 7 дней подряд', 'icon': '⚡'},
    ]

    achievements_with_status = []
    for ach in all_achievements:
        achievements_with_status.append({
            'id': ach['id'],
            'name': ach['name'],
            'description': ach['description'],
            'icon': ach['icon'],
            'earned': ach['id'] in earned_ids
        })

    return jsonify(achievements_with_status)


@app.route('/api/check_achievements')
@login_required
def check_achievements():
    completed_count = UserProgress.query.filter_by(
        user_id=current_user.id, completed=True
    ).count()

    achievements_to_award = []

    if completed_count >= 5:
        achievements_to_award.append((1, 'Первые шаги', 'Завершено 5 заданий', '🌟'))

    if completed_count >= 25:
        achievements_to_award.append((5, 'Серебряный птенец', 'Решено 25 заданий', '🥈'))

    if completed_count >= 50:
        achievements_to_award.append((6, 'Золотой соловей', 'Решено 50 заданий', '🥇'))

    for ach_id, name, desc, icon in achievements_to_award:
        existing = UserAchievement.query.filter_by(
            user_id=current_user.id, achievement_id=ach_id
        ).first()
        if not existing:
            new_ach = UserAchievement(
                user_id=current_user.id,
                achievement_id=ach_id,
                achievement_name=name,
                achievement_description=desc,
                icon=icon
            )
            db.session.add(new_ach)

    db.session.commit()
    return jsonify({'success': True})


@app.route('/criteria')
def criteria():
    return render_template('criteria.html')


@app.route('/cheatsheet')
def cheatsheet():
    return render_template('cheatsheet.html')


TASKS_DATA = {
    'task5': {
        'name': 'Задание 5 - Пунктуация',
        'description': 'Расставьте знаки препинания. Укажите все цифры, на месте которых должны стоять запятые/тире/двоеточие/кавычки.',
        'tasks': [
            {'id': 1, 'text': 'Суздальский музей деревянного зодчества (1) настоящий городок (2) построенный без единого гвоздя. Мельницы (3) церковь (4) дома (5) амбары и бани (6) всё привезено сюда из разных сёл.', 'answer': '17'},
            {'id': 2, 'text': 'Лабиринты Заяцкого острова (1) настоящая загадка Соловецкого архипелага. Тайна (2) завесу которой пока никто не может приподнять (3) манит к себе туристов.', 'answer': '2689'},
            {'id': 3, 'text': 'Долина гейзеров (1) природная достопримечательность Камчатского края. Уникальные термальные источники (2) грязевые котлы (3) водопады и озёра (4) всё это разбросано по каньону реки.', 'answer': '158'},
            {'id': 4, 'text': 'Красивая природа (1) обилие бурных рек (2) и живописных озёр (3) превращают Русский Север в райский уголок. Каким бы ни был круг ваших интересов (4) оказавшись в этих краях (5) вы почувствуете себя как дома.', 'answer': '1356'},
            {'id': 5, 'text': 'Известный учёный А.В. Ополовников в книге (1) Русский Север (2) писал: (3) Замечательнейшие события нашей истории записаны не только на страницах летописей (4).', 'answer': '1234'},
        ]
    },
    'task6': {
        'name': 'Задание 6 - Орфография',
        'description': 'Укажите варианты ответов, в которых дано ВЕРНОЕ объяснение написания выделенного слова.',
        'tasks': [
            {'id': 1, 'text': '1) СНИМАТЬ (кино) – написание безударной чередующейся гласной в корне слова зависит от места ударения.\n2) КОЛЬЦЕВАЯ (композиция) – в суффиксе имени прилагательного после Ц без ударения пишется буква Е.\n3) ОПРЕДЕЛЯЕМОЕ (слово) – написание буквы Е в суффиксе страдательного причастия настоящего времени определяется принадлежностью к I спряжению глагола.\n4) НОЖНИЦЫ – в окончании имени существительного после Ц пишется буква Ы.\n5) БЕСПОЛЕЗНЫЙ (совет) – на конце приставки перед буквой, обозначающей звонкий согласный звук, пишется буква С.', 'answer': '234'},
            {'id': 2, 'text': '1) ОТПИЛИТЬ – на конце приставки перед буквой, обозначающей глухой согласный звук, пишется буква Т.\n2) БЛЕСТЯЩИЙ – написание безударной гласной в корне проверяется подбором однокоренного слова блеск.\n3) НЕРЯШЛИВЫЙ – НЕ пишется слитно с именем прилагательным, которое не употребляется без НЕ.\n4) ЗЕМЛЯНОЙ – в суффиксе имени прилагательного -ЯН- пишется одна буква Н.\n5) ИЮНЬСКИЙ – буква Ь указывает на мягкость предшествующего согласного.', 'answer': '345'},
            {'id': 3, 'text': '1) (говорит) ПО-ГРУЗИНСКИ – наречие пишется через дефис, так как есть приставка ПО- и суффикс -И.\n2) СЖИМАТЬ (кулаки) – правописание чередующейся гласной в корне определяется наличием суффикса -А-.\n3) НЕ НАМЕРЕН – частица НЕ с кратким страдательным причастием пишется раздельно.\n4) ПЛЕЩУЩИЙСЯ – в действительном причастии настоящего времени, образованном от основы глагола I спряжения, пишется суффикс -УЩ-.\n5) СКОРРЕКТИРОВАТЬ – на конце приставки перед буквой, обозначающей глухой согласный звук, пишется буква С.', 'answer': '124'},
        ]
    },
    'task8': {
        'name': 'Задание 8 - Грамматические нормы',
        'description': 'Раскройте скобки и запишите слово в правильной форме.',
        'tasks': [
            {'id': 1, 'text': '(Пятьдесят) километрами ниже по реке находилась сторожка лесника.', 'answer': 'пятьюдесятью'},
            {'id': 2, 'text': 'По (обе) сторонам дороги цвели яблони.', 'answer': 'обеим'},
            {'id': 3, 'text': 'Бледный язычок (пламя) костра светился в темноте.', 'answer': 'пламени'},
            {'id': 4, 'text': 'Для приготовления десерта понадобится банка консервированных (абрикосы).', 'answer': 'абрикосов'},
            {'id': 5, 'text': 'Установка оборудования для фильтрации воды в будущем (сберечь) здоровье жителей города.', 'answer': 'сбережет'},
        ]
    },
    'task9': {
        'name': 'Задание 9 - Словосочетания',
        'description': 'Замените словосочетание синонимичным с указанной связью.',
        'tasks': [
            {'id': 1, 'text': 'Замените словосочетание «плавательный бассейн» (связь согласование) на синонимичное со связью управление.', 'answer': 'бассейн для плавания'},
            {'id': 2, 'text': 'Замените словосочетание «слушать с вниманием» (связь управление) на синонимичное со связью примыкание.', 'answer': 'слушать внимательно'},
            {'id': 3, 'text': 'Замените словосочетание «гнездо глухаря» (связь управление) на синонимичное со связью согласование.', 'answer': 'глухариное гнездо'},
            {'id': 4, 'text': 'Замените словосочетание «утренняя прогулка» (связь согласование) на синонимичное со связью примыкание.', 'answer': 'прогулка утром'},
            {'id': 5, 'text': 'Замените словосочетание «день без ветра» (связь управление) на синонимичное со связью согласование.', 'answer': 'безветренный день'},
        ]
    },
    'essays': {
        'name': 'Темы сочинений 13.3',
        'description': 'Выберите тему и напишите сочинение-рассуждение.',
        'tasks': [
            {'id': 1, 'text': 'Какого человека можно назвать по-настоящему сильным? (по тексту М. Горького)'},
            {'id': 2, 'text': 'Что могут сказать о человеке его поступки? (по тексту К.Г. Паустовского)'},
            {'id': 3, 'text': 'В каких поступках раскрывается характер человека? (по тексту Ю.Я. Яковлева)'},
            {'id': 4, 'text': 'Чем опасны необдуманные поступки? (по тексту Ю.Я. Яковлева)'},
            {'id': 5, 'text': 'Какова роль справедливости в жизни человека? (по тексту Л. Пантелеева)'},
            {'id': 6, 'text': 'Как в годы войны люди проявляли мужество? (по тексту К.Г. Паустовского)'},
            {'id': 7, 'text': 'Что значит быть добрым? (по тексту Ю.Я. Яковлева)'},
            {'id': 8, 'text': 'В чём проявляется материнская любовь? (по тексту В.П. Астафьева)'},
        ]
    }
}


@app.route('/tasks')
def tasks():
    return render_template('tasks_catalog.html', tasks_data=TASKS_DATA)


@app.route('/task/<task_type>/<int:task_id>')
def show_task(task_type, task_id):
    if task_type in TASKS_DATA:
        for task in TASKS_DATA[task_type]['tasks']:
            if task['id'] == task_id:
                return render_template('task_detail.html', 
                                       task_type=task_type,
                                       task=task,
                                       task_name=TASKS_DATA[task_type]['name'])
    return redirect(url_for('tasks'))


@app.route('/api/submit_task', methods=['POST'])
@login_required
def submit_task():
    data = request.get_json()
    user_answer = data.get('answer', '').strip().lower()
    correct_answer = data.get('correct_answer', '').strip().lower()
    
    is_correct = (user_answer == correct_answer)
    
    if is_correct:
        flash('Верно!', 'success')
    else:
        flash(f'Неверно. Правильный ответ: {correct_answer}', 'error')
    
    return jsonify({'correct': is_correct, 'correct_answer': correct_answer})


@app.route('/theory')
def theory():
    theory_topics = {
        'punctuation': {
            'name': 'Пунктуация',
            'content': 'Тире между подлежащим и сказуемым, обособление определений и приложений, обособление обстоятельств, вводные слова.'
        },
        'grammar': {
            'name': 'Грамматические ошибки',
            'content': 'Синтаксические ошибки: присоединение дополнения, несочетаемые понятия, разные части речи как однородные члены.'
        },
        'sentence_types': {
            'name': 'Типы предложений',
            'content': 'Определённо-личные, неопределённо-личные, обобщённо-личные, безличные, назывные.'
        },
        'bsp': {
            'name': 'Знаки в БСП',
            'content': 'Двоеточие (АЧП): а именно, что, потому что. Тире (КЕПКА): когда, если, поэтому, как, но.'
        },
        'roots': {
            'name': 'Корни-омонимы',
            'content': 'гор- (загорать) НО горевать; кос- (касаться) НО косить; мер- (умереть) НО примерять; мир- (замирать) НО примирять.'
        },
        'spelling': {
            'name': 'Орфография',
            'content': 'Приставки на -З/-С, ПРЕ-/ПРИ-, И/Ы после приставок, пол-/полу-, Н/НН в причастиях и прилагательных.'
        },
        'express': {
            'name': 'Средства выразительности',
            'content': 'Эпитет, метафора, олицетворение, сравнение, гипербола, литота, фразеологизм, антонимы, синонимы.'
        },
        'phrases': {
            'name': 'Словосочетания',
            'content': 'Согласование, управление, примыкание. Правило СУП для замены словосочетаний.'
        }
    }
    return render_template('theory.html', theory_topics=theory_topics)


@app.route('/theory/<topic>')
def theory_topic(topic):
    theory_topics = {
        'punctuation': 'ТИРЕ МЕЖДУ ПОДЛЕЖАЩИМ И СКАЗУЕМЫМ:\n✅ Ставится: Сущ. — Сущ.; н.ф.гл. — н.ф.гл.\n❌ НЕ ставится: есть, как, будто, словно, не, личн.мест.\n\nОБОСОБЛЕНИЕ ОПРЕДЕЛЕНИЙ:\n- Причастный оборот ПОСЛЕ слова → запятые\n- Относится к ЛИЧНОМУ МЕСТОИМЕНИЮ → запятые\n\nОБОСОБЛЕНИЕ ОБСТОЯТЕЛЬСТВ:\n- Деепричастный оборот → запятые\n- Сравнительный оборот (как, словно, будто) → запятые',
        'grammar': 'ЧАСТЫЕ ГРАММАТИЧЕСКИЕ ОШИБКИ:\n\n1. Присоединение к однородным сказуемым дополнения, которое управляется лишь одним из сказуемых\n❌ "Необходимо сохранять и помнить о великих людях"\n✅ "Необходимо сохранять память... и помнить об их подвиге"\n\n2. Соединение несочетаемых понятий\n❌ "Я люблю водоемы и собак в том числе"\n\n3. Разные части речи как однородные\n❌ "Домашние обязанности — мытьё полов, посидеть с братом"\n\n4. Неверное использование местоимений\n❌ "Она одета в шубку, в руке она держит варежку, на ней платок"',
        'sentence_types': 'ТИПЫ ПРЕДЛОЖЕНИЙ ПО СОСТАВУ:\n\nОПРЕДЕЛЁННО-ЛИЧНЫЕ: сказуемое без подлежащего, можно подставить Я, МЫ, ТЫ, ВЫ\nпример: Приходи в гости! Хочу съездить на море.\n\nНЕОПРЕДЕЛЁННО-ЛИЧНЫЕ: можно подставить ОНИ\nпример: В дверь стучат.\n\nОБОБЩЁННО-ЛИЧНЫЕ: пословицы, поговорки\nпример: Любишь кататься — люби и саночки возить.\n\nБЕЗЛИЧНЫЕ: нельзя подставить Я, ТЫ, ОНИ\nпример: Холодает. Меня знобит.\n\nНАЗЫВНЫЕ: только подлежащее\nпример: Поля. Пастбища. Стадо.',
        'bsp': 'БСП: ДВОЕТОЧИЕ И ТИРЕ\n\nДВОЕТОЧИЕ (АЧП):\n1. А именно (пояснение): [В доме тишина]: скрипнула дверь\n2. Что (дополнение): [Все знают]: бережёного Бог бережёт\n3. Почему (причина): [Страшно]: материя обращалась в пыль\n\nТИРЕ (КЕПКА):\n1. Когда: [Настанет утро] — [двинемся в путь]\n2. Если: [Назвался груздем] — [полезай в кузов]\n3. Поэтому: [Солнце встаёт] — [будет жаркий день]\n4. Как: [Молвит слово] — [соловей поёт]\n5. А, НО: [Службу оставил] — [быстро поменял решение]',
        'express': 'СРЕДСТВА ВЫРАЗИТЕЛЬНОСТИ:\n\nЭПИТЕТ: образное определение — "золотая осень"\nМЕТАФОРА: скрытое сравнение — "горит восток зарёю новой"\nОЛИЦЕТВОРЕНИЕ: неживое как живое — "ветер завывал"\nСРАВНЕНИЕ: с союзами как, словно, будто — "лёд, как сахар"\nГИПЕРБОЛА: преувеличение — "сто раз говорил"\nЛИТОТА: преуменьшение — "мальчик с пальчик"\nФРАЗЕОЛОГИЗМ: устойчивое выражение — "повесить нос"'
    }
    content = theory_topics.get(topic, 'Информация временно недоступна')
    return render_template('theory_detail.html', topic=topic, content=content)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)