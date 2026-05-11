from flask import Blueprint, render_template
from data.tasks import THEORY_TOPICS, COMPREHENSIVE_THEORY_CONTENT

theory_bp = Blueprint('theory', __name__)


@theory_bp.route('/criteria')
def criteria():
    return render_template('criteria.html')


@theory_bp.route('/cheatsheet')
def cheatsheet():
    return render_template('cheatsheet.html')


@theory_bp.route('/theory')
def theory():
    return render_template('theory.html', theory_topics=THEORY_TOPICS)


@theory_bp.route('/theory/<topic>')
def theory_topic(topic):
    content = COMPREHENSIVE_THEORY_CONTENT.get(topic, 'Информация временно недоступна')
    return render_template('theory_detail.html', topic=topic, content=content)