from flask import Flask, render_template, send_from_directory
import os
from dotenv import load_dotenv
from flask_restful import Api
from sqlalchemy import func
from cache import cache
from models import db, UPLOAD_FOLDER, Invoice
from apis.upload import UploadPDFAPI

load_dotenv()

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DB_URI")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

api = Api(app)
db.init_app(app)
cache.init_app(app)

@app.route("/", methods=["GET"])
def home():
    return render_template("home.html")


@app.route("/upload", methods=["GET"])
def upload():
    return render_template("upload.html")

@app.route("/upload/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

api.add_resource(UploadPDFAPI, "/upload")

@app.route("/records", methods=["GET"])
@cache.cached(timeout=3600)
def records():
    invoices = Invoice.query.order_by(Invoice.invoice_id.desc()).all()
    return render_template("records.html", records=invoices)

@app.route("/duplicates", methods=["GET"])
@cache.cached(timeout=3600)
def duplicates():
    dup_hashes = (Invoice.query.with_entities(Invoice.source_file_hash)
                  .group_by(Invoice.source_file_hash)
                  .having(func.count() > 1)
                  .subquery()
                )
    dup_invoices = Invoice.query.filter(Invoice.source_file_hash.in_(dup_hashes)).all()
    return render_template("duplicates.html", duplicates=dup_invoices)


if __name__ == "__main__":
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    with app.app_context():
        db.create_all()

    app.run()
