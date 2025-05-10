# app.py
from datetime import datetime, timezone, timedelta

from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flask_migrate import Migrate

from api.auth_routes import init_auth_routes
from api.tender_routes import init_tender_routes
from config import Config
import logging

from repositories.user_repository import UserRepository
from repositories.tender_repository import TenderRepository
from services.auth_service import AuthService
from services.password_service import PasswordService
from services.report_generation_service import ReportGenerationService

from util.complaint_text_render import process_complaint_text, format_violation_scores
from util.field_maps import KEYWORD_FIELD_MAP
from util.report_helpers import format_entity_change

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from db import db
app = Flask(__name__)
app.config.from_object(Config)

app.jinja_env.globals['process_complaint_text'] = process_complaint_text
app.jinja_env.globals['format_violation_scores'] = format_violation_scores
app.jinja_env.globals['keyword_field_map'] = KEYWORD_FIELD_MAP
app.jinja_env.globals['format_entity_change'] = format_entity_change
app.jinja_env.globals['format_datetime'] = lambda dt: dt.strftime('%Y-%m-%d %H:%M:%S') if dt else None

db.init_app(app)

import models

migrate = Migrate(app, db)


user_repository = UserRepository(db.session)
tender_repository = TenderRepository(db.session)
report_generation_service = ReportGenerationService(db.session)
password_service = PasswordService()
auth_service = AuthService(app, user_repository, password_service)



# Move CrawlerService import and initialization here
def init_crawler_service():
    from services.crawler_service import CrawlerService
    crawler_service = CrawlerService(tender_repository)
    return crawler_service

init_tender_routes(app, tender_repository, user_repository, report_generation_service,
                   init_crawler_service())
init_auth_routes(app, auth_service)

@app.route('/')
def index():
    title_search = request.args.get('title', '').strip()
    ocid_search_param = request.args.get('search_ocid', '').strip()

    page = 1 if title_search or ocid_search_param else request.args.get('page', 1, type=int)
    per_page = 18 # Or your desired number

    search_term_for_repo = title_search
    if ocid_search_param and not title_search:
        search_term_for_repo = ocid_search_param

    if search_term_for_repo:
        tenders, total = tender_repository.search_tenders(search_term_for_repo, page, per_page)
    else:
        tenders, total = tender_repository.get_tenders_short(page, per_page)

    return render_template(
        'index.html',
        tenders=tenders,
        page=page,
        per_page=per_page,
        total=total,
        title_filter=title_search,
        ocid_being_added=ocid_search_param
    )

@app.route('/check_tender_status/<ocid>')
def check_tender_status(ocid):
    tender_short_info = tender_repository.get_short_by_ocid_for_status_check(ocid)

    if tender_short_info:
        return jsonify({"exists": True, "tender_uuid": tender_short_info['id']})
    else:
        return jsonify({"exists": False, "tender_uuid": None})

@app.route('/user_tenders')
def user_tenders():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
    tenders = tender_repository.get_subscribed_tenders(user_id)
    return render_template('user_tenders.html', tenders=tenders)

if __name__ == '__main__':
    app.run(debug=True)