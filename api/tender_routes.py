from datetime import datetime, timedelta

from flask import Blueprint, render_template, redirect, url_for, flash, session

from repositories.tender_repository import TenderRepository
from repositories.user_repository import UserRepository
from services.report_generation_service import ReportGenerationService
from util.db_context_manager import session_scope

tender_bp = Blueprint('tender', __name__)

def init_tender_routes(app):
    @tender_bp.route('/tenders/<tender_id>')
    def tender_detail(tender_id):
        with session_scope() as db_session:
            tender_repository = TenderRepository(db_session)
            user_repo = UserRepository(db_session)
            report_generation_service = ReportGenerationService(db_session)
            try:
                tender = tender_repository.get_by_id(tender_id)
                if not tender:
                    return "Tender not found", 404

                report_data = report_generation_service.generate_tender_report(tender_id=tender_id,
                                                                               new_since=datetime.now() - timedelta(
                                                                                   hours=1),
                                                                               changes_since=None)
                subscribed = False
                if session.get('user_id'):
                    found_sub = user_repo.find_subscription(session['user_id'], tender_id)
                    subscribed = found_sub is not None

                return render_template('tender_detail.html', tender=tender, report_data=report_data,
                                       subscribed=subscribed)
            except Exception as e:
                app.logger.error(f"Error fetching tender details: {e}", exc_info=True)
                flash("Сталася помилка при отриманні даних тендеру", "danger")
                return redirect(url_for('index'))

    app.register_blueprint(tender_bp, url_prefix='/tender')