from marshmallow import Schema, EXCLUDE, fields


class ValueSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    amount = fields.Float(allow_none=True)


class PeriodSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    startDate = fields.DateTime(allow_none=True)
    endDate = fields.DateTime(allow_none=True)
