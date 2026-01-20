from flask import request, redirect, url_for
from flask_restful import Resource
from werkzeug.utils import secure_filename
import os

from models import db, UploadedFile, UPLOAD_FOLDER
from utils import genai_utils


class UploadPDFAPI(Resource):
    def post(self):
        files = request.files.getlist("files")
        if not files:
            return {"error": "No files provided"}, 400

        saved = []
        inv_records = []

        for file in files:
            file.filename = secure_filename(file.filename)
            file_path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(file_path)

            record = UploadedFile(
                file_name=file.filename,
                file_path=file_path,
            )

            db.session.add(record)
            db.session.commit()

            saved.append({
                "id": record.id,
                "file_name": record.file_name,
                "file_path": record.file_path,
                "uploaded_at": record.uploaded_at.isoformat(),
            })

        for rec in saved:
            inv_rec = genai_utils.ocr(rec)
            inv_records.append(inv_rec)

        return redirect(url_for("upload",  msg="Upload completed successfully"))
