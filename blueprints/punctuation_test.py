from flask import Blueprint, render_template, session, jsonify, request
from flask_login import login_required, current_user
from data.tasks import PUNCTUATION_TEST

punctuation_test_bp = Blueprint('punctuation_test', __name__)


@punctuation_test_bp.route('/punctuation-test')
@login_required
def test_list():
    tests = PUNCTUATION_TEST['tasks']
    return render_template('punctuation_test_list.html', 
                         tests=tests,
                         test_name=PUNCTUATION_TEST['name'])


@punctuation_test_bp.route('/punctuation-test/<int:task_id>')
@login_required
def run_test(task_id):
    test = None
    for t in PUNCTUATION_TEST['tasks']:
        if t['id'] == task_id:
            test = t
            break
    
    if not test:
        return redirect('/punctuation-test')

    words = []
    raw_text = test['text']
    parts = raw_text.split(' ')
    current_pos = 0
    for word in parts:
        words.append({
            'text': word,
            'position': current_pos,
            'has_punctuation': False,
            'punctuation': None
        })
        current_pos += 1
    
    session['current_test'] = {
        'id': test['id'],
        'words': words,
        'correct': test['correct_punctuation'],
        'explanation': test['explanation']
    }
    
    return render_template('punctuation_test.html', 
                         test=test,
                         words=words,
                         total=len(PUNCTUATION_TEST['tasks']))


@punctuation_test_bp.route('/api/punctuation/save', methods=['POST'])
@login_required
def save_punctuation():
    data = request.get_json()
    word_index = data.get('word_index')
    punctuation = data.get('punctuation')
    
    if 'current_test' in session:
        session['current_test']['words'][word_index]['punctuation'] = punctuation
        if punctuation:
            session['current_test']['words'][word_index]['has_punctuation'] = True
        else:
            session['current_test']['words'][word_index]['has_punctuation'] = False
        session.modified = True
        return jsonify({'success': True})
    
    return jsonify({'success': False}), 400


@punctuation_test_bp.route('/api/punctuation/check/<int:task_id>', methods=['POST'])
@login_required
def check_punctuation(task_id):
    test_data = session.get('current_test')
    if not test_data:
        return jsonify({'error': 'Тест не найден'}), 404
    
    words = test_data['words']
    correct = test_data['correct']
    explanation = test_data['explanation']
    
    results = []
    errors_count = 0
    
    for i, word in enumerate(words):
        word_text = word['text']
        user_punct = word.get('punctuation', '')
        correct_punct = correct.get(word_text, {}).get('after', '')
        
        is_correct = (user_punct == correct_punct) or (not user_punct and not correct_punct)
        if not is_correct and correct_punct:
            errors_count += 1
        
        results.append({
            'word': word_text,
            'position': i,
            'user_punct': user_punct or '',
            'correct_punct': correct_punct or '',
            'is_correct': is_correct
        })
    
    session.pop('current_test', None)
    
    return jsonify({
        'success': True,
        'results': results,
        'errors_count': errors_count,
        'explanation': explanation,
        'correct_text': explanation['full_text']
    })


@punctuation_test_bp.route('/api/punctuation/reset/<int:task_id>', methods=['POST'])
@login_required
def reset_test(task_id):
    """Сброс теста"""
    if 'current_test' in session:
        session.pop('current_test', None)
    return jsonify({'success': True})
