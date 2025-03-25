from marshmallow import Schema, fields


class TenderShortSchema(Schema):
    id = fields.Str()
    date_modified = fields.DateTime(data_key="dateModified", format="iso")

class NextPageSchema(Schema):
    offset = fields.Str()
    path = fields.Str()
    uri = fields.Str()

class TendersPageSchema(Schema):
    data = fields.List(fields.Nested(TenderShortSchema))
    next_page = fields.Nested(NextPageSchema, allow_none=True)