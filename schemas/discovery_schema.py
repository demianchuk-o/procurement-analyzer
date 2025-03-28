from marshmallow import Schema, fields, post_load, EXCLUDE

class SearchTenderShortSchema(Schema):
    tenderID = fields.Str(required=True) # OCID identifier used as primary id in discovery api

    class Meta:
        # The sole purpose of this schema is to extract tenderID
        unknown = EXCLUDE

    @post_load
    def extract_tender_id(self, data, **kwargs):
        # Return just the tenderID string after loading
        return data['tenderID']

# Schema for the overall /search/tenders/ page structure
class SearchPageSchema(Schema):
    data = fields.List(fields.Nested(SearchTenderShortSchema), required=True)
    page = fields.Int(required=True)
    per_page = fields.Int(required=True)
    total = fields.Int(required=True)

    class Meta:
        unknown = EXCLUDE

class GeneralClassifierSchema(Schema):
    scheme = fields.Str(required=True)
    description = fields.Str(required=True)

    class Meta:
        unknown = EXCLUDE

# All tender details needed from discovery API
class TenderBridgeInfoSchema(Schema):
    id = fields.Str(required=True) # 32-char UUID
    tenderID = fields.Str(required=True) # OCID
    generalClassifier = fields.Nested(GeneralClassifierSchema, required=True, data_key='generalClassifier')
    dateModified = fields.DateTime(required=True, data_key='dateModified', format='iso')

    class Meta:
        unknown = EXCLUDE