from datetime import datetime, timedelta

from flask import Blueprint, render_template, redirect, url_for, flash, session, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from services.user_service import UserService

tender_bp = Blueprint('tender', __name__)

def init_tender_routes(app,
                       tender_repository,
                       user_repository,
                       report_generation_service,
                       crawler_service):
    user_service = UserService(user_repository, tender_repository)
    @tender_bp.route('/tenders/<tender_id>')
    @jwt_required(optional=True)
    def tender_detail(tender_id):
        try:
            tender = tender_repository.get_by_id(tender_id)
            if not tender:
                tender = tender_repository.get_by_ocid(tender_id)
            if not tender:
                return "Tender not found", 404

            report_data = report_generation_service.generate_tender_report(tender_id=tender_id,
                                                                           new_since=datetime.now() - timedelta(hours=1),
                                                                           changes_since=None)
            user_id = get_jwt_identity()
            subscribed = False
            if user_id:
                found_sub = user_repository.find_subscription(session['user_id'], tender_id)
                subscribed = found_sub is not None

            return render_template('tender_detail.html', tender=tender, report_data=report_data,
                                   subscribed=subscribed)
        except Exception as e:
            app.logger.error(f"Error fetching tender details: {e}", exc_info=True)
            flash("Сталася помилка при отриманні даних тендеру", "danger")
            return redirect(url_for('index'))


    @tender_bp.route('/add_tender', methods=['GET'])
    def add_tender_page():
        return render_template('add_tender.html')

    @tender_bp.route('/add_tender', methods=['POST'])
    def add_tender():
        tender_ocid = request.form.get('tender_ocid')
        if not tender_ocid:
            flash('Будь ласка, вкажіть OCID', 'danger')
            return redirect(url_for('tender.add_tender_page'))

        try:
            crawler_service.sync_single_tender(tender_ocid)

            flash(f'Тендер {tender_ocid} поставлено в чергу на обробку. Результати з\'являться на головній сторінці.',
                  'info')
            return redirect(url_for('index', search_ocid=tender_ocid))
        except Exception as e:
            app.logger.error(f"Error adding tender: {e}", exc_info=True)
            flash(f"Не вдалося поставити тендер {tender_ocid} в чергу", "danger")
            return redirect(url_for('tender.add_tender_page'))

    @tender_bp.route('/subscribe', methods=['POST'])
    @jwt_required()
    def subscribe():
        user_id = get_jwt_identity()
        tender_id = request.form['tender_id']
        try:
            user_service.subscribe_to_tender(user_id, tender_id)
            flash('Підписано на тендер', 'success')
        except ValueError as e:
            flash(str(e), 'danger')
        return redirect(url_for('tender.tender_detail', tender_id=tender_id))

    @tender_bp.route('/unsubscribe', methods=['POST'])
    @jwt_required()
    def unsubscribe():
        user_id = get_jwt_identity()
        tender_id = request.form['tender_id']
        try:
            user_service.unsubscribe_from_tender(user_id, tender_id)
            flash('Відписано від тендеру', 'success')
        except ValueError as e:
            flash(str(e), 'danger')
        return redirect(url_for('tender.tender_detail', tender_id=tender_id))



    app.register_blueprint(tender_bp, url_prefix='/tender')