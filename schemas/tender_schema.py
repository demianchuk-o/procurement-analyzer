from marshmallow import Schema, fields, post_load, EXCLUDE

from models import Tender
from schemas.common_schemas import ValueSchema, PeriodSchema


class TenderSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Str()
    ocid = fields.Str(data_key="tender_id")
    date_created = fields.DateTime(data_key="date")
    date_modified = fields.DateTime(data_key="dateModified")
    title = fields.Str(allow_none=True)
    value = fields.Nested(ValueSchema(), data_key="value", allow_none=True)
    status = fields.Str()
    enquiry_period = fields.Nested(PeriodSchema(), data_key="enquiryPeriod", allow_none=True)
    tender_period = fields.Nested(PeriodSchema(), data_key="tenderPeriod", allow_none=True)
    auction_period = fields.Nested(PeriodSchema(), data_key="auctionPeriod", allow_none=True)
    award_period = fields.Nested(PeriodSchema(), data_key="awardPeriod", allow_none=True)
    notice_publication_date = fields.DateTime(data_key="noticePublicationDate", allow_none=True)

    @post_load
    def make_tender(self, data, **kwargs):
        value = data.pop('value', None)
        if value:
            data['value_amount'] = value.get('amount')
            data['value_currency'] = value.get('currency')
            data['value_vat_included'] = value.get('vatIncluded')

        enquiry_period = data.pop('enquiry_period', None)
        if enquiry_period:
            data['enquiry_period_start_date'] = enquiry_period.get('startDate')
            data['enquiry_period_end_date'] = enquiry_period.get('endDate')

        tender_period = data.pop('tender_period', None)
        if tender_period:
            data['tender_period_start_date'] = tender_period.get('startDate')
            data['tender_period_end_date'] = tender_period.get('endDate')

        auction_period = data.pop('auction_period', None)
        if auction_period:
            data['auction_period_start_date'] = auction_period.get('startDate')
            data['auction_period_end_date'] = auction_period.get('endDate')

        award_period = data.pop('award_period', None)
        if award_period:
            data['award_period_start_date'] = award_period.get('startDate')
            data['award_period_end_date'] = award_period.get('endDate')

        return Tender(**data)