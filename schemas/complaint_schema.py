from marshmallow import Schema, fields, post_load, EXCLUDE
from models import Complaint

class ComplaintSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Str()
    status = fields.Str()
    title = fields.Str(allow_none=True)
    description = fields.Str(allow_none=True)
    date = fields.DateTime()
    date_submitted = fields.DateTime(data_key="dateSubmitted", allow_none=True)
    date_answered = fields.DateTime(data_key="dateAnswered", allow_none=True)
    type = fields.Str(default="complaint")

    @post_load
    def make_complaint(self, data, **kwargs):
        return Complaint(**data)