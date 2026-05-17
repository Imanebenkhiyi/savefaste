# merge_pdf_bp.py
import os
import uuid
import json
from functools import wraps
from flask import Blueprint, request, jsonify, send_from_directory, render_template, redirect, url_for, make_response
from PyPDF2 import PdfMerger, PdfReader
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, auth, firestore

# ---- Config ----
merge_pdf_bp = Blueprint('merge_pdf', __name__, template_folder='templates')

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
MERGED_FOLDER = os.path.join(BASE_DIR, 'merged')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(MERGED_FOLDER, exist_ok=True)

# Anonymous cookie name for unregistered users
ANON_COOKIE_NAME = 'anon_id'

# Security limits
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB per file
ALLOWED_EXTENSIONS = {'.pdf'}
MAX_FILES = 20

# Daily limit
DAILY_LIMIT = 3

# Firebase initialization - use local adminn.json file (place it in same folder)
FIREBASE_CRED_PATH = os.path.join(BASE_DIR, "admine.json")  # <-- تأكد من اسم الملف هنا

if os.path.exists(FIREBASE_CRED_PATH):
    cred = credentials.Certificate(FIREBASE_CRED_PATH)
    try:
        firebase_admin.initialize_app(cred)
    except ValueError:
        pass
    db = firestore.client()
else:
    print("❌ adminn.json NOT FOUND — Firebase Admin disabled.")
    db = None

# ---- Utility Helpers ----
def allowed_file(filename):
    _, ext = os.path.splitext(filename.lower())
    return ext in ALLOWED_EXTENSIONS

def get_anonymous_id():
    """Generate a stable anonymous id (UUID) for unauthenticated users stored in cookie."""
    anon_id = request.cookies.get(ANON_COOKIE_NAME)
    if not anon_id:
        anon_id = str(uuid.uuid4())
    return anon_id

def verify_firebase_token(id_token):
    """Return user dict {uid, email, is_premium} or None if invalid. Requires firebase admin setup."""
    if not id_token or not db:
        return None
    try:
        decoded = auth.verify_id_token(id_token)
        uid = decoded.get('uid')
        # Look up user record in Firestore to get subscription info
        user_doc = db.collection('users').document(uid).get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            return {
                'uid': uid,
                'email': user_data.get('email', decoded.get('email')),
                'is_premium': bool(user_data.get('is_premium', False)),
            }
        else:
            # If no document, assume non-premium registered user
            return {'uid': uid, 'email': decoded.get('email'), 'is_premium': False}
    except Exception as e:
        # token invalid or verification failed
        # print("Token verify failed:", e)
        return None

def get_usage_doc_ref_for_user(uid):
    return db.collection('usage').document(f"user:{uid}")

def get_usage_doc_ref_for_anon(anon_id):
    return db.collection('usage').document(f"anon:{anon_id}")

# Updated: track daily usage with 'uses' and 'date' fields
def increment_usage_for_ref(doc_ref):
    """Atomically increment daily usage and return new value. Firestore required."""
    if not db:
        return None
    try:
        def _tx(transaction, ref):
            snap = ref.get(transaction=transaction)
            today = datetime.utcnow().strftime("%Y-%m-%d")
            if snap.exists:
                data = snap.to_dict()
                last_date = data.get('date')
                uses = int(data.get('uses', 0))
                if last_date != today:
                    uses = 0
                uses += 1
                transaction.set(ref, {
                    'uses': uses,
                    'date': today,
                    'last_use': firestore.SERVER_TIMESTAMP
                }, merge=True)
                return uses
            else:
                transaction.set(ref, {
                    'uses': 1,
                    'date': today,
                    'first_use': firestore.SERVER_TIMESTAMP,
                    'last_use': firestore.SERVER_TIMESTAMP
                })
                return 1

        transaction = db.transaction()
        uses = transaction.call(_tx, doc_ref)
        return uses
    except Exception as e:
        # print("increment_usage_for_ref error:", e)
        return None

def get_usage_count_for_ref(doc_ref):
    """Return today's usage count or 0. Returns None on DB error."""
    if not db:
        return None
    try:
        snap = doc_ref.get()
        if not snap.exists:
            return 0
        data = snap.to_dict()
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if data.get('date') != today:
            return 0
        return int(data.get('uses', 0))
    except Exception as e:
        # print("get_usage_count_for_ref error:", e)
        return None


# ---- Session tracking helpers (for progress UI) ----
def create_session_doc(session_id, owner_meta):
    """Create a session document in Firestore to track progress."""
    if not db:
        return
    doc_ref = db.collection('sessions').document(session_id)
    doc_ref.set({
        'status': 'created',
        'progress': 0,
        'message': 'Created',
        'owner': owner_meta,
        'created_at': firestore.SERVER_TIMESTAMP,
    }, merge=True)

def update_session_doc(session_id, status=None, progress=None, message=None, merged_filename=None):
    if not db:
        return
    doc_ref = db.collection('sessions').document(session_id)
    data = {}
    if status:
        data['status'] = status
    if progress is not None:
        data['progress'] = progress
    if message:
        data['message'] = message
    if merged_filename:
        data['merged_filename'] = merged_filename
    data['updated_at'] = firestore.SERVER_TIMESTAMP
    doc_ref.set(data, merge=True)


# ---- Enforcement decorator ----
def enforce_usage_limit(f):
    """
    Decorator that enforces: 3 uses/day limit for unregistered users (anon) and for registered non-premium users.
    Registered premium users: unlimited.
    If limit exceeded:
      - if registered & not premium -> respond with JSON directing to /premium
      - if not registered -> respond with JSON directing to /signup then /premium
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # 1) try to verify Firebase token from Authorization header (Bearer) or cookie "firebase_token"
        id_token = None
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            id_token = auth_header.split(' ', 1)[1].strip()
        else:
            id_token = request.cookies.get('firebase_token')

        user = verify_firebase_token(id_token) if id_token else None

        if user:
            uid = user['uid']
            is_premium = user.get('is_premium', False)
            if is_premium:
                # premium users: no limit
                return f(*args, **kwargs)
            # registered non-premium
            if db:
                ref = get_usage_doc_ref_for_user(uid)
                current_uses = get_usage_count_for_ref(ref)
                if current_uses is None:
                    # Firestore error - permissive
                    return f(*args, **kwargs)
                if current_uses >= DAILY_LIMIT:
                    # prompt to upgrade
                    return jsonify({
                        "success": False,
                        "message": "You have reached the free daily merge limit.",
                        "action": "upgrade",
                        "redirect": "/premium"
                    }), 402
                # else allow; the actual increment happens after successful merge to avoid counting failed attempts
                kwargs['_usage_doc_ref'] = ref
                kwargs['_user_meta'] = {'type': 'registered', 'uid': uid}
                return f(*args, **kwargs)
            else:
                # no db configured: permissive
                return f(*args, **kwargs)
        else:
            # anonymous user
            anon_id = get_anonymous_id()
            if db:
                ref = get_usage_doc_ref_for_anon(anon_id)
                current_uses = get_usage_count_for_ref(ref)
                if current_uses is None:
                    # Firestore error - permissive with cookie set
                    resp = f(*args, **kwargs)
                    if isinstance(resp, (tuple, list)):
                        response = make_response(resp[0], resp[1] if len(resp) > 1 else 200)
                    else:
                        response = make_response(resp)
                    response.set_cookie(ANON_COOKIE_NAME, anon_id, max_age=60*60*24*365, httponly=True, samesite='Lax')
                    return response
                if current_uses >= DAILY_LIMIT:
                    # ask to signup then upgrade
                    return jsonify({
                        "success": False,
                        "message": "You have reached the free daily merge limit. Please sign up and choose a plan to continue.",
                        "action": "signup",
                        "redirect": "/signup",
                        "next": "/premium"
                    }), 402
                # allow; pass refs to handler to increment on success
                kwargs['_usage_doc_ref'] = ref
                kwargs['_anon_id'] = anon_id
                kwargs['_user_meta'] = {'type': 'anon', 'anon_id': anon_id}
                return f(*args, **kwargs)
            else:
                # no db: allow and set cookie
                resp = f(*args, **kwargs)
                if isinstance(resp, (tuple, list)):
                    response = make_response(resp[0], resp[1] if len(resp) > 1 else 200)
                else:
                    response = make_response(resp)
                response.set_cookie(ANON_COOKIE_NAME, anon_id, max_age=60*60*24*365, httponly=True, samesite='Lax')
                return response

    return decorated


# ---- Routes ----
@merge_pdf_bp.route('/')
def home():
    return redirect(url_for('merge_pdf.serve_merge_html'))

@merge_pdf_bp.route('', methods=['GET'])
def serve_merge_html():
    return render_template('mergepdf.html')


@merge_pdf_bp.route('/start-merge', methods=['POST'])
@enforce_usage_limit
def start_merge(_usage_doc_ref=None, _anon_id=None, _user_meta=None):
    """
    Main merge route. The decorator ensures we haven't exceeded free-use limits.
    This route accepts multipart form 'pdfs' files via fetch/XHR and returns JSON {success: True, session_id: ...}
    It updates a sessions collection in Firestore to track progress.
    """
    if 'pdfs' not in request.files:
        return jsonify({"success": False, "message": "No files uploaded"}), 400

    files = request.files.getlist('pdfs')
    if len(files) < 2:
        return jsonify({"success": False, "message": "Please upload at least two PDF files."}), 400

    # Basic file count and size checks (security)
    if len(files) > MAX_FILES:
        return jsonify({"success": False, "message": f"Too many files. Max allowed is {MAX_FILES}."}), 400

    session_id = str(uuid.uuid4())
    session_folder = os.path.join(UPLOAD_FOLDER, session_id)
    os.makedirs(session_folder, exist_ok=True)

    # create session doc
    owner_meta = _user_meta or {'type': 'unknown'}
    create_session_doc(session_id, owner_meta)
    update_session_doc(session_id, status='uploading', progress=0, message='Uploading files')

    merger = PdfMerger()
    saved_filepaths = []
    try:
        total_files = len(files)
        for idx, file in enumerate(files, start=1):
            filename = secure_filename(file.filename)
            if not allowed_file(filename):
                update_session_doc(session_id, status='error', message=f"Not a PDF: {filename}")
                return jsonify({"success": False, "message": f"Only PDF files are allowed: {filename}"}), 400

            # Check file length (werkzeug FileStorage has stream)
            file.stream.seek(0, os.SEEK_END)
            size = file.stream.tell()
            file.stream.seek(0)
            if size > MAX_FILE_SIZE_BYTES:
                update_session_doc(session_id, status='error', message=f"File too large: {filename}")
                return jsonify({"success": False, "message": f"File {filename} exceeds the maximum size of {MAX_FILE_SIZE_BYTES} bytes."}), 400

            filepath = os.path.join(session_folder, filename)
            # Save file
            file.save(filepath)
            saved_filepaths.append(filepath)

            # Optional: check that file is a readable PDF (PyPDF2)
            try:
                PdfReader(filepath)
            except Exception:
                # cleanup
                for p in saved_filepaths:
                    try:
                        os.remove(p)
                    except Exception:
                        pass
                update_session_doc(session_id, status='error', message=f"Uploaded file {filename} is not a valid PDF.")
                return jsonify({"success": False, "message": f"Uploaded file {filename} is not a valid PDF."}), 400

            # update upload progress
            upload_progress = int((idx / total_files) * 50)  # upload is 0-50%
            update_session_doc(session_id, progress=upload_progress, message=f"Uploaded {idx}/{total_files}")

            # append to merger (we'll do in next loop or here; append here but merging progress updated after)
            merger.append(filepath)

        # merging step
        update_session_doc(session_id, status='merging', message='Merging files', progress=60)
        # simulate incremental progress as we write pages (approx)
        # PyPDF2 doesn't provide per-page progress easily, so we interpolate:
        update_session_doc(session_id, progress=75, message='Finalizing merge')

        merged_filename = f"{session_id}.pdf"
        merged_path = os.path.join(MERGED_FOLDER, merged_filename)
        merger.write(merged_path)
        merger.close()

        # finalize session doc
        update_session_doc(session_id, status='done', progress=100, message='Completed', merged_filename=merged_filename)

        # Increment usage AFTER successful merge
        if db and _usage_doc_ref is not None:
            try:
                increment_usage_for_ref(_usage_doc_ref)
            except Exception:
                # fail silently - do not block user for DB write issues
                pass

        response = jsonify({"success": True, "session_id": session_id})
        # If anon, ensure anon cookie is set in response
        if _user_meta and _user_meta.get('type') == 'anon' and _anon_id:
            resp = make_response(response)
            resp.set_cookie(ANON_COOKIE_NAME, _anon_id, max_age=60*60*24*365, httponly=True, samesite='Lax')
            return resp

        return response
    except Exception as e:
        # cleanup partial files on error
        for p in saved_filepaths:
            try:
                os.remove(p)
            except Exception:
                pass
        try:
            merger.close()
        except Exception:
            pass
        update_session_doc(session_id, status='error', message=str(e))
        return jsonify({"success": False, "message": str(e)}), 500

@merge_pdf_bp.route('/progress')
def progress():
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({"success": False, "message": "Missing session_id"}), 400

    # ---- FIRST: Check using Firestore or local fallback ----
    if not db:
        # Local mode (no Firestore)
        merged_path = os.path.join(MERGED_FOLDER, f"{session_id}.pdf")
        if os.path.exists(merged_path):
            status = "done"
            progress_value = 100
        else:
            status = "pending"
            progress_value = 0

    else:
        # Firestore mode
        doc_ref = db.collection('sessions').document(session_id)
        snap = doc_ref.get()

        if not snap.exists:
            return jsonify({"success": False, "message": "Session not found"}), 404
        
        data = snap.to_dict()
        status = data.get("status", "pending")
        progress_value = int(data.get("progress", 0))

    # ---- IF MERGE NOT DONE → return JSON (polling response) ----
    if status != "done":
        return jsonify({
            "success": True,
            "status": status,
            "progress": progress_value,
            "message": data.get("message") if db else "",
            "merged_filename": None
        })

    # ---- MERGE DONE → Render success HTML ----
    merged_path = os.path.join(MERGED_FOLDER, f"{session_id}.pdf")
    if not os.path.exists(merged_path):
        return jsonify({"success": False, "message": "Merged file missing"}), 500

    download_link = url_for('merge_pdf.download_file', filename=f"{session_id}.pdf")

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>PDF Merge Success</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css"/>
  <style>
    body {{
      margin: 0;
      padding: 0;
      background: linear-gradient(135deg, #e0f7fa, #f1f8ff);
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      min-height: 100vh;
      display: flex;
      justify-content: center;
      align-items: center;
    }}
    .container {{
      background-color: #ffffff;
      border-radius: 20px;
      padding: 50px 40px;
      width: 95%;
      max-width: 700px;
      box-shadow: 0 8px 30px rgba(0,0,0,0.1);
      display: flex;
      flex-direction: column;
      align-items: center;
    }}
    .header {{
      width: 100%;
      text-align: center;
      margin-bottom: 25px;
    }}
    .header h1 {{
      font-size: 2.4rem;
      color: #333;
      margin-bottom: 10px;
    }}
    .header p {{
      color: #555;
      font-size: 1rem;
    }}
    .success-icon {{
      color: #28a745;
      font-size: 4rem;
      margin-bottom: 25px;
    }}
    .file-info {{
      background-color: #f8f9fa;
      border-radius: 12px;
      padding: 20px;
      width: 100%;
      text-align: left;
      margin-bottom: 30px;
      box-shadow: inset 0 1px 3px rgba(0,0,0,0.05);
    }}
    .file-info p {{
      margin: 10px 0;
      font-size: 1rem;
      color: #444;
    }}
    .buttons {{
      display: flex;
      gap: 20px;
      flex-wrap: wrap;
      justify-content: center;
      margin-top: 10px;
    }}
    .btn {{
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 14px 24px;
      font-size: 1rem;
      border-radius: 10px;
      text-decoration: none;
      font-weight: bold;
      transition: all 0.3s ease;
      box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }}
    .btn-download {{
      background-color: #007bff;
      color: white;
    }}
    .btn-download:hover {{
      background-color: #0056b3;
    }}
    .btn-new {{
      background-color: #6c757d;
      color: white;
    }}
    .btn-new:hover {{
      background-color: #495057;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>🎉 PDF Merged Successfully!</h1>
      <p>Your document is now ready to download and use.</p>
    </div>

    <div class="success-icon">
      <i class="fa-solid fa-circle-check"></i>
    </div>

    <div class="file-info">
      <p><strong>📄 File Name:</strong> {session_id}.pdf</p>
      <p><strong>📦 Estimated Size:</strong> ~1-3 MB</p>
      <p><strong>⏱ Created At:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    </div>

    <div class="buttons">
      <a href="{download_link}" class="btn btn-download" download>
        <i class="fa-solid fa-download"></i> Download PDF
      </a>
      <a href="/mergepdf" class="btn btn-new">
        <i class="fa-solid fa-file-circle-plus"></i> Merge New Files
      </a>
    </div>
  </div>
</body>
</html>
"""


@merge_pdf_bp.route('/download/<filename>')
def download_file(filename):
    # security: ensure filename looks like uuid.pdf
    if '..' in filename or '/' in filename:
        return "Invalid filename", 400
    file_path = os.path.join(MERGED_FOLDER, filename)
    if not os.path.exists(file_path):
        return f"❌ File not found.", 404
    return send_from_directory(MERGED_FOLDER, filename, as_attachment=True)