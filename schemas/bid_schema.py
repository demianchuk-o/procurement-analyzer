from marshmallow import Schema, fields, post_load, EXCLUDE
from models import Bid

from schemas.common_schemas import ValueSchema

class IdentifierSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Str()
    legal_name = fields.Str(data_key="legalName")

    @post_load
    def make_identifier(self, data, **kwargs):
        return data

class TendererSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    identifier = fields.Nested(IdentifierSchema(), data_key="identifier", allow_none=True)


class BidSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Str()
    date = fields.DateTime()
    status = fields.Str()
    value = fields.Nested(ValueSchema(), data_key="value", allow_none=True)

    tenderers = fields.List(fields.Nested(TendererSchema()), data_key="tenderers", allow_none=True)

    @post_load
    def make_bid(self, data, **kwargs):
        # Extract the value amount from the nested structure
        value = data.pop('value', None)
        if value:
            data['value_amount'] = value.get('amount')

        tenderers = data.pop('tenderers', None)
        if tenderers:
            first_tenderer = tenderers[0] if tenderers else None
            if first_tenderer:
                identifier = first_tenderer.get('identifier')
                if identifier:
                    data['tenderer_id'] = identifier.get('id')
                    data['tenderer_legal_name'] = identifier.get('legal_name')

        return Bid(**data)