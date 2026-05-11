from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from models import db, UserProgress, ChecklistItem, UserAchievement

api_progress_bp = Blueprint('api_progress', __name__)


@api_progress_bp.route('/api/progress_data')
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


@api_progress_bp.route('/api/problem_topics')
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


@api_progress_bp.route('/api/checklist', methods=['GET'])
@login_required
def get_checklist():
    items = ChecklistItem.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        'id': item.id,
        'topic_id': item.topic_id,
        'topic_name': item.topic_name,
        'checked': item.checked
    } for item in items])


@api_progress_bp.route('/api/checklist/toggle/<int:item_id>', methods=['POST'])
@login_required
def toggle_checklist(item_id):
    item = ChecklistItem.query.filter_by(id=item_id, user_id=current_user.id).first()
    if item:
        item.checked = not item.checked
        db.session.commit()
        return jsonify({'success': True, 'checked': item.checked})
    return jsonify({'success': False, 'error': 'Item not found'}), 404


@api_progress_bp.route('/api/checklist/init', methods=['POST'])
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


@api_progress_bp.route('/api/achievements')
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


@api_progress_bp.route('/api/check_achievements')
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