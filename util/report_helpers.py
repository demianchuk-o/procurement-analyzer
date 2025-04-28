from typing import Any, Callable, Dict, Type


from models import Bid, Award, TenderDocument, Complaint, Tender


def format_currency(amount, currency="UAH"):
    if amount is None:
        return "N/A"
    return f"{amount:.2f} {currency}"

def get_bid_short_info(bid: Bid) -> str:
    """Generates a user-friendly Ukrainian short info string for a Bid."""
    amount_str = format_currency(getattr(bid, 'value_amount', None))
    tenderer_name = getattr(bid, 'tenderer_legal_name', 'Невідомий учасник')
    return f"Пропозиція від '{tenderer_name}' ({amount_str})"

def get_award_short_info(award: Award) -> str:
    """Generates a user-friendly Ukrainian short info string for an Award."""
    amount_str = format_currency(getattr(award, 'value_amount', None))

    bid_info = ""
    if hasattr(award, 'bid') and award.bid:
        bid_tenderer = getattr(award.bid, 'tenderer_legal_name', 'Невідомий учасник')
        bid_info = f" (для пропозиції '{bid_tenderer}')"
    # Using award.title if it exists, otherwise fallback
    award_title = getattr(award, 'title', f'Нагорода ID: {award.id}')
    return f"{award_title} ({amount_str}){bid_info}"

def get_document_short_info(doc: TenderDocument) -> str:
    """Generates a user-friendly Ukrainian short info string for a TenderDocument."""
    title = getattr(doc, 'title', 'Без назви')
    doc_format = getattr(doc, 'format')
    return f"Документ: '{title}.{doc_format}'"

def get_complaint_short_info(complaint: Complaint) -> str:
    """Generates a user-friendly Ukrainian short info string for a Complaint."""
    title = getattr(complaint, 'title', 'Без назви')

    complaint_type = getattr(complaint, 'type', "")
    return f"Скарга ({complaint_type}): '{title}'"

def get_tender_short_info(tender: Tender) -> str:
    """Generates a user-friendly Ukrainian short info string for a Tender."""
    title = getattr(tender, 'title', 'Без назви')
    amount_str = format_currency(getattr(tender, 'value_amount', None))
    return f"Тендер: '{title}' ({amount_str})"

# Dictionary mapping model types to their short info functions
ENTITY_SHORT_INFO_FORMATTERS: Dict[Type, Callable[[Any], str]] = {
    Bid: get_bid_short_info,
    Award: get_award_short_info,
    TenderDocument: get_document_short_info,
    Complaint: get_complaint_short_info,
    Tender: get_tender_short_info,
}

def get_entity_short_info(entity: Any) -> str:
    """
    Returns a user-friendly short info string for a given entity
    by looking up the appropriate formatter.
    """
    formatter = ENTITY_SHORT_INFO_FORMATTERS.get(type(entity))
    if formatter:
        return formatter(entity)

    # Fallback if no specific formatter is found
    return f"Об'єкт ID: {getattr(entity, 'id', 'N/A')}"