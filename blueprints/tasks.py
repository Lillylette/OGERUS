from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user
from models import db, UserProgress
from data.tasks import TASKS_DATA

tasks_bp = Blueprint('tasks', __name__)

SKILL_MAP = {
    'task5': 'Пунктуация',
    'task6': 'Орфография',
    'task8': 'Анализ текста',
    'task9': 'Анализ текста',
    'essays': 'Сочинение',
    'task2': 'Анализ текста',
    'task3': 'Анализ текста',
    'task4': 'Пунктуация'
}
def build_test_questions():
    """Возвращает список вопросов для теста (по одному из task5, task6, task8, task9)"""
    questions = []
    
    task5 = TASKS_DATA.get('task5', {}).get('tasks', [])
    if task5:
        q = task5[0]  # первое задание
        questions.append({
            'task_type': 'task5',
            'task_id': q['id'],
            'text': q['text'],
            'answer': q['answer'],
            'description': q.get('description', '')
        })
    
    task6 = TASKS_DATA.get('task6', {}).get('tasks', [])
    if task6:
        q = task6[0]
        questions.append({
            'task_type': 'task6',
            'task_id': q['id'],
            'text': q['text'],
            'answer': q['answer'],
            'description': q.get('description', '')
        })
    
    task8 = TASKS_DATA.get('task8', {}).get('tasks', [])
    if task8:
        q = task8[0]
        questions.append({
            'task_type': 'task8',
            'task_id': q['id'],
            'text': q['text'],
            'answer': q['answer'],
            'description': q.get('description', '')
        })
    
    task9 = TASKS_DATA.get('task9', {}).get('tasks', [])
    if task9:
        q = task9[0]
        questions.append({
            'task_type': 'task9',
            'task_id': q['id'],
            'text': q['text'],
            'answer': q['answer'],
            'description': q.get('description', '')
        })
    
    return questions


@tasks_bp.route('/tasks')
def tasks():
    return render_template('tasks_catalog.html', tasks_data=TASKS_DATA)


@tasks_bp.route('/task/<task_type>/<int:task_id>')
def show_task(task_type, task_id):
    if task_type in TASKS_DATA:
        for task in TASKS_DATA[task_type]['tasks']:
            if task['id'] == task_id:
                return render_template('task_detail.html',
                                       task_type=task_type,
                                       task=task,
                                       task_name=TASKS_DATA[task_type]['name'])
    return redirect(url_for('tasks.tasks'))


@tasks_bp.route('/api/submit_task', methods=['POST'])
@login_required
def submit_task():
    data = request.get_json()
    user_answer = data.get('answer', '').strip().lower()
    correct_answer = data.get('correct_answer', '').strip().lower()
    task_type = data.get('task_type', '')
    topic_id = data.get('topic_id', 0)

    skill = SKILL_MAP.get(task_type, 'Орфография')

    topic_name = ''
    if task_type in TASKS_DATA:
        for task in TASKS_DATA[task_type]['tasks']:
            if task['id'] == topic_id:
                topic_name = task.get('text', '')[:80]
                break
    if not topic_name:
        topic_name = TASKS_DATA.get(task_type, {}).get('name', 'Неизвестная тема')

    is_correct = (user_answer == correct_answer)

    if skill and topic_name:
        progress = UserProgress.query.filter_by(
            user_id=current_user.id,
            topic_id=topic_id,
            skill=skill
        ).first()

        if not progress:
            progress = UserProgress(
                user_id=current_user.id,
                topic_id=topic_id,
                topic_name=topic_name,
                skill=skill,
                total_attempts=0,
                correct_attempts=0,
                completed=False
            )
            db.session.add(progress)

        progress.total_attempts += 1
        if is_correct:
            progress.correct_attempts += 1

        if progress.total_attempts > 0 and progress.correct_attempts == progress.total_attempts:
            progress.completed = True

        db.session.commit()

    if is_correct:
        flash('Верно!', 'success')
    else:
        flash(f'Неверно. Правильный ответ: {correct_answer}', 'error')

    return jsonify({'correct': is_correct, 'correct_answer': correct_answer})



@tasks_bp.route('/test')
@login_required
def start_test():
    questions = build_test_questions()
    if not questions:
        flash('Нет заданий для теста', 'error')
        return redirect(url_for('tasks.tasks'))

    session['test_questions'] = [{
        'task_type': q['task_type'],
        'task_id': q['task_id'],
        'text': q['text'],
        'answer': q['answer'],
        'description': q['description']
    } for q in questions]
    session['test_answers'] = {}        # словарь {индекс: ответ}
    session['test_current'] = 0         # индекс текущего вопроса
    session.modified = True
    return redirect(url_for('tasks.test_question', q_index=0))


@tasks_bp.route('/test/question/<int:q_index>')
@login_required
def test_question(q_index):
    """Показывает вопрос с индексом q_index"""
    questions = session.get('test_questions')
    if not questions or q_index >= len(questions):
        return redirect(url_for('tasks.test_finish'))
    
    question = questions[q_index]
    total = len(questions)
    return render_template('test_question.html',
                           question=question,
                           q_index=q_index,
                           current=q_index+1,
                           total=total)


@tasks_bp.route('/api/test/submit', methods=['POST'])
@login_required
def submit_test_answer():
    data = request.get_json()
    q_index = data.get('index')
    answer = data.get('answer', '').strip()
    
    questions = session.get('test_questions')
    if not questions or q_index >= len(questions):
        return jsonify({'error': 'Invalid question index'}), 400
    
    if 'test_answers' not in session:
        session['test_answers'] = {}
    session['test_answers'][str(q_index)] = answer
    session.modified = True
    
    next_index = q_index + 1
    if next_index >= len(questions):
        return jsonify({'finished': True})
    else:
        return jsonify({'finished': False, 'next_index': next_index})


@tasks_bp.route('/test/finish')
@login_required
def test_finish():
    questions = session.get('test_questions')
    user_answers = session.get('test_answers', {})
    
    if not questions:
        return redirect(url_for('tasks.tasks'))

    correct_count = 0
    results = []
    for i, q in enumerate(questions):
        user_ans = user_answers.get(str(i), '')
        is_correct = (user_ans.lower() == q['answer'].lower())
        if is_correct:
            correct_count += 1
        results.append({
            'task_type': q['task_type'],
            'text': q['text'],
            'user_answer': user_ans,
            'correct_answer': q['answer'],
            'is_correct': is_correct,
            'description': q.get('description', '')
        })
    
    session.pop('test_questions', None)
    session.pop('test_answers', None)
    session.pop('test_current', None)
    session.modified = True
    
    for i, q in enumerate(questions):
        skill = SKILL_MAP.get(q['task_type'], 'Орфография')
        topic_name = q['text'][:80] if q['text'] else q['description']
        is_correct = results[i]['is_correct']
        
        progress = UserProgress.query.filter_by(
            user_id=current_user.id,
            topic_id=q['task_id'] + 1000,
            skill=skill
        ).first()
        if not progress:
            progress = UserProgress(
                user_id=current_user.id,
                topic_id=q['task_id'] + 1000,
                topic_name=topic_name,
                skill=skill,
                total_attempts=0,
                correct_attempts=0,
                completed=False
            )
            db.session.add(progress)
        progress.total_attempts += 1
        if is_correct:
            progress.correct_attempts += 1
        if progress.total_attempts > 0 and progress.correct_attempts == progress.total_attempts:
            progress.completed = True
    db.session.commit()
    
    return render_template('test_result.html',
                           results=results,
                           correct=correct_count,
                           total=len(questions))
