from marshmallow import Schema, fields, post_load, EXCLUDE
from models import TenderDocument

class TenderDocumentSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Str()
    document_of = fields.Str(data_key="documentOf")
    title = fields.Str(allow_none=True)
    format = fields.Str(allow_none=True)
    url = fields.Str(allow_none=True)
    hash = fields.Str(allow_none=True)
    date_published = fields.DateTime(data_key="datePublished", allow_none=True)
    date_modified = fields.DateTime(data_key="dateModified", allow_none=True)

    @post_load
    def make_document(self, data, **kwargs):
        return TenderDocument(**data)