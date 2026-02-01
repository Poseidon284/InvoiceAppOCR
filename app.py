from flask import Flask, render_template
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

api.add_resource(UploadPDFAPI, "/upload", "/upload/<path:filename>", endpoint='upload')

@app.route("/records", methods=["GET"])
@cache.cached(timeout=3600)
def records():
    invoices = (db.session.scalars(db.select(Invoice).order_by(Invoice.invoice_id.desc())).all())
    return render_template("records.html", records=invoices)

@app.route("/duplicates", methods=["GET"])
@cache.cached(timeout=3600)
def duplicates():
    dup_hashes = (
        db.select(Invoice.source_file_hash).group_by(Invoice.source_file_hash).having(func.count() > 1).subquery()
    )

    dup_invoices = (
        db.session.scalars(
            db.select(Invoice).where(Invoice.source_file_hash.in_(db.select(dup_hashes.c.source_file_hash)))
        ).all()
    )
    return render_template("duplicates.html", duplicates=dup_invoices)


if __name__ == "__main__":
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    with app.app_context():
        db.create_all()

    app.run()
