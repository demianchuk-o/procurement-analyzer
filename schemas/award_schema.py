from marshmallow import Schema, fields, post_load, EXCLUDE
from models import Award

from schemas.common_schemas import ValueSchema, PeriodSchema

class AwardSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Str()
    status = fields.Str()
    title = fields.Str(allow_none=True)
    value = fields.Nested(ValueSchema(), data_key="value", allow_none=True)
    award_date = fields.DateTime(data_key="date")
    complaint_period = fields.Nested(PeriodSchema(), data_key="complaintPeriod", allow_none=True)

    @post_load
    def make_award(self, data, **kwargs):
        value = data.pop('value', None)
        if value:
            data['value_amount'] = value.get('amount')

        complaint_period = data.pop('complaint_period', None)
        if complaint_period:
            data['complaint_period_start_date'] = complaint_period.get('startDate')
            data['complaint_period_end_date'] = complaint_period.get('endDate')

        return Award(**data)