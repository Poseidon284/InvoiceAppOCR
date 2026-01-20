import uuid
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID, JSONB

db = SQLAlchemy()

UPLOAD_FOLDER = "uploads"


class Invoice(db.Model):
    __tablename__ = "invoices"

    invoice_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_file_name = db.Column(db.String(256))
    source_file_hash = db.Column(db.String(128), index=True)

    raw_text = db.Column(db.Text)
    raw_extracted_json = db.Column(JSONB)

    vendor = db.Column(JSONB)
    invoice = db.Column(JSONB)
    items = db.Column(JSONB)
    amounts = db.Column(JSONB)
    classification = db.Column(JSONB)
    rule_trace = db.Column(JSONB)

    confidence_score = db.Column(db.Float)
    doc_score = db.Column(db.String(15))


class UploadedFile(db.Model):
    __tablename__ = "uploaded_files"

    id = db.Column(db.Integer, primary_key=True)
    file_name = db.Column(db.String(256), nullable=False, index=True)
    file_path = db.Column(db.String(512), nullable=False, index=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.now)
