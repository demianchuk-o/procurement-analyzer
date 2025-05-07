from datetime import datetime, timezone, timedelta

from flask import Flask, render_template, request, session
from flask_migrate import Migrate

from api.auth_routes import init_auth_routes
from config import Config
import logging

from repositories.user_repository import UserRepository
from repositories.tender_repository import TenderRepository
from services.auth_service import AuthService
from services.password_service import PasswordService
from services.report_generation_service import ReportGenerationService

from util.complaint_text_render import process_complaint_text
from util.field_maps import KEYWORD_FIELD_MAP
from util.report_helpers import format_entity_change

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from db import db
app = Flask(__name__)
app.config.from_object(Config)

app.jinja_env.filters['process_text'] = process_complaint_text
app.jinja_env.globals['keyword_field_map'] = KEYWORD_FIELD_MAP
app.jinja_env.globals['format_entity_change'] = format_entity_change

db.init_app(app)

import models

migrate = Migrate(app, db)

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    tender_repository = TenderRepository(db.session)
    per_page = 18
    tenders, total = tender_repository.get_tenders_short(page, per_page)
    return render_template('index.html', tenders=tenders, page=page, per_page=per_page, total=total)

@app.route('/tenders/<tender_id>')
def tender_detail(tender_id):
    tender_repository = TenderRepository(db.session)
    user_repo = UserRepository(db.session)
    report_generation_service = ReportGenerationService(db.session)
    tender = tender_repository.get_by_id(tender_id)
    if not tender:
        return "Tender not found", 404

    report_data = report_generation_service.generate_tender_report(tender_id=tender_id,
                                                                   new_since=datetime.now() - timedelta(hours=1),
                                                                   changes_since=None)
    subscribed = False
    if session.get('user_id'):
        found_sub = user_repo.find_subscription(session['user_id'], tender_id)
        subscribed = found_sub is not None

    return render_template('tender_detail.html', tender=tender, report_data=report_data, subscribed=subscribed)

with app.app_context():
    user_repository = UserRepository(db.session)
    password_service = PasswordService()
    auth_service = AuthService(app, user_repository, password_service)


    init_auth_routes(app, auth_service)

if __name__ == '__main__':
    app.run(debug=True)