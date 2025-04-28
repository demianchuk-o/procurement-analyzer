TENDER_FIELD_MAP = {
    "date_created": "Дата створення",
    "title": "Назва",
    "value_amount": "Сума",
    "status": "Статус",
    "enquiry_period_start_date": "Початок періоду запитів",
    "enquiry_period_end_date": "Кінець періоду запитів",
    "tender_period_start_date": "Початок періоду тендеру",
    "tender_period_end_date": "Кінець періоду тендеру",
    "auction_period_start_date": "Початок аукціону",
    "auction_period_end_date": "Кінець аукціону",
    "award_period_start_date": "Початок періоду визначення переможця",
    "award_period_end_date": "Кінець періоду визначення переможця",
    "notice_publication_date": "Дата публікації оголошення",
    "general_classifier_id": "General Classifier ID",
}

BID_FIELD_MAP = {
    "date": "Дата подання",
    "status": "Статус",
    "value_amount": "Сума",
    "tenderer_id": "Tenderer ID",
    "tenderer_legal_name": "Ім'я учасника",
}

AWARD_FIELD_MAP = {
    "status": "Статус",
    "title": "Заголовок",
    "value_amount": "Сума",
    "award_date": "Дата присудження",
    "complaint_period_start_date": "Початок періоду оскарження",
    "complaint_period_end_date": "Кінець періоду оскарження",
}

TENDER_DOCUMENT_FIELD_MAP = {
    "document_of": "Документ належить до",
    "title": "Назва",
    "format": "Формат",
    "url": "Посилання",
    "hash": "Хеш",
    "date_published": "Дата публікації",
    "date_modified": "Дата зміни",
}

COMPLAINT_FIELD_MAP = {
    "status": "Статус",
    "title": "Заголовок",
    "description": "Опис",
    "date": "Дата створення",
    "date_submitted": "Дата подання",
    "date_answered": "Дата відповіді",
    "type": "Тип",
}

from typing import Dict


def get_field_map(entity_type_name: str) -> Dict[str, str]:
    """
    Returns the field map for the given model class.
    """
    if entity_type_name == 'tenders':
        return TENDER_FIELD_MAP
    elif entity_type_name == 'bids':
        return BID_FIELD_MAP
    elif entity_type_name == 'awards':
        return AWARD_FIELD_MAP
    elif entity_type_name == 'documents':
        return TENDER_DOCUMENT_FIELD_MAP
    elif entity_type_name == 'complaints':
        return COMPLAINT_FIELD_MAP
    else:
        raise ValueError(f"Unknown model class: {entity_type_name.__name__}")