import os
from flask import Flask, render_template, request, redirect, url_for, session
import MySQLdb
import bcrypt
from flask_mail import Mail, Message
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os.path
import pickle

app = Flask(__name__)
app.secret_key = 'your_secret_key'
SCOPES = ['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive']
db = MySQLdb.connect("localhost", "root", "Yash2611", "bank")
cur = db.cursor()

# Configure Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'yash.burad22@spit.ac.in'
app.config['MAIL_PASSWORD'] = 'yash@2611'

mail = Mail(app)


def get_credentials():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # Check if the credentials are valid.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=8082)  # Use port 8082 for OAuth flow
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return creds


def create_and_share_document(company_users):
    creds = get_credentials()
    service = build('docs', 'v1', credentials=creds)
    document = service.documents().create().execute()
    document_id = document.get('documentId')

    # Share the document with each email in company_users
    for email in company_users:
        share_document(document_id, email)

    document_link = f"https://docs.google.com/document/d/{document_id}"
    return document_link

def share_document(file_id, email):
    creds = get_credentials()
    drive_service = build('drive', 'v3', credentials=creds)
    user_permission = {
        'type': 'user',
        'role': 'writer',
        'emailAddress': email
    }
    drive_service.permissions().create(
        fileId=file_id,
        body=user_permission,
        fields='id',
    ).execute()


@app.route('/')
def index():
    return render_template("index.html")

@app.route('/registerCompany', methods=['GET', 'POST'])
def registerCompany():
    if request.method == 'POST':
        comp_id = request.form['comp_id']
        company_name = request.form['company_name']
        contact_name = request.form['contact_name']
        contact_email = request.form['contact_email']
        contact_phone = request.form['contact_phone']
        industry = request.form['industry']
        comp_password = request.form['comp_password']
        
        hashed_password = bcrypt.hashpw(comp_password.encode('utf-8'), bcrypt.gensalt())

        cur.execute("INSERT INTO basic_company_information (comp_id, company_name, contact_name, contact_email, contact_phone, industry, comp_password) VALUES (%s, %s, %s, %s, %s, %s, %s)", (comp_id, company_name, contact_name, contact_email, contact_phone, industry, hashed_password))
        db.commit()

        # Initialize the timeline for the company
        cur.execute("INSERT INTO timeline (comp_id, statuss) VALUES (%s, %s)", (comp_id, 0))
        db.commit()

        return redirect(url_for('loginCompany'))
    return render_template('registerCompany.html')


@app.route('/loginCompany', methods=['GET', 'POST'])
def loginCompany():
    if request.method == 'POST':
        comp_id = request.form['comp_id']
        comp_password = request.form['comp_password']
        cur.execute("SELECT * FROM basic_company_information WHERE comp_id = %s", (comp_id,))
        company = cur.fetchone()
        if company and bcrypt.checkpw(comp_password.encode('utf-8'), company[6].encode('utf-8')):
            if comp_id == 'admin123' and comp_password == 'major@123':
                session['comp_id'] = comp_id
                session['is_admin'] = True
                return redirect(url_for('admin_dashboard'))
            else:
                session['comp_id'] = comp_id
                session['is_admin'] = False
                return redirect(url_for('comp_dashboard'))
        else:
            return 'Invalid username/password'
    return render_template('loginCompany.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    return render_template("admin_dashboard.html")


# Define your timeline stages and corresponding URLs
timeline_stages = [
    {"name": "Decision to Issue IPO", "url": "/decision-IPO"},
    {"name": "Hire Investment Bank", "url": "/hire-IB"},
    {"name": "Underwriting", "url": "/underwriting"},
    {"name": "Filing DRHP", "url": "/filing-DRHP"},
    {"name": "Comply Rules", "url": "/comply-rules"},
    {"name": "SEBI Approval", "url": "/SEBI-approval"},
    {"name": "Finalizing RHP", "url": "/finalizing-RHP"},
    {"name": "Roadshows", "url": "/roadshows"},
    {"name": "Price Building", "url": "/price-building"},
    {"name": "Open for Subscription", "url": "/open-subscription"},
    {"name": "Share Allotment", "url": "/share-allotment"},
    {"name": "Stock Listing", "url": "/stock-listing"}
]
@app.route('/company/dashboard')
def comp_dashboard():
    if 'comp_id' not in session:
        return redirect(url_for('loginCompany'))
    
    # Number of completed stages (this can be dynamically fetched based on your application logic)
    comp_id = session['comp_id']
    cur.execute("SELECT statuss FROM timeline WHERE comp_id = %s", (comp_id,))
    completed_stages = cur.fetchone()[0]    
    

    return render_template('timeline.html', timeline_stages=timeline_stages, completed_stages=completed_stages, comp_id=comp_id)

# Define dynamic routes for each timeline stage
@app.route('/company/<stage_url>')
def stage_redirect(stage_url):
    if 'comp_id' not in session:
        return redirect(url_for('loginCompany'))

    # Fetch the comp_id from session
    comp_id = session['comp_id']

    # Determine the completed stage index from the URL
    for i, stage in enumerate(timeline_stages):
        if stage['url'] == f'/{stage_url}':
            completed_stages = i + 1  # Increment by 1 because completed_stages is 1-based
            break
    else:
        return redirect(url_for('comp_dashboard'))  # Redirect to dashboard if stage_url is not found

    # For rendering dynamic stage pages
    render_template(f'timelineFolder/{stage_url}.html', comp_id=comp_id, completed_stages=completed_stages)






@app.route('/admin/view_requests')
def view_requests():
    if 'is_admin' in session and session['is_admin']:
        cur.execute("SELECT comp_id, company_name, contact_name, contact_email, contact_phone, industry FROM basic_company_information")
        requests = cur.fetchall()
        return render_template("view_requests.html", requests=requests)
    else:
        return redirect(url_for('loginCompany'))

@app.route('/admin/accept_request/<comp_id>')
def accept_request(comp_id):
    cur.execute("SELECT contact_email FROM basic_company_information WHERE comp_id = %s", (comp_id,))
    email = cur.fetchone()[0]
    
    msg = Message("IPO Request Accepted", sender="yash.burad22@spit.ac.in", recipients=[email])
    msg.body = f"Hello {comp_id},\n\nYour request for an IPO has been accepted. Please enter detailed information here: http://127.0.0.1:5000/detailedINFO/{comp_id}"
    mail.send(msg)
    
    return redirect(url_for('view_requests'))
@app.route('/detailedINFO/<comp_id>', methods=['GET', 'POST'])
def detailed_info(comp_id):
    if 'comp_id' not in session or session['comp_id'] != comp_id:
        return redirect(url_for('loginCompany'))
    
    if request.method == 'POST':
        # Process form data
        form_fields = [
            'company_performance', 'financial_condition', 'future_outlook', 'business_model',
            'products_services', 'market_position', 'legal_issues', 'regulatory_issues',
            'management_team', 'use_of_proceeds', 'market_risks', 'operational_risks',
            'board_of_directors', 'governance_structure'
        ]
        
        # Collect only the filled fields
        data = {field: request.form.get(field) for field in form_fields if request.form.get(field)}
        
        if data:
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['%s'] * len(data))
            values = tuple(data.values())
            
            query = f"INSERT INTO detailed_info (comp_id, {columns}) VALUES (%s, {placeholders})"
            cur.execute(query, (comp_id, *values))
            db.commit()
        
        # Process file uploads
        upload_folder = os.path.join('uploads', comp_id)
        try:
            os.makedirs(upload_folder, exist_ok=True)
        except OSError as e:
            return f"Error creating directory: {e}", 500
        
        sections = {
            'financial_docs': 'Financial Documents',
            'business_docs': 'Business Documents',
            'legal_docs': 'Legal Documents',
            'management_docs': 'Management Documents',
            'proceeds_docs': 'Proceeds Documents',
            'risk_docs': 'Risk Documents',
            'governance_docs': 'Governance Documents'
        }

        for section, description in sections.items():
            files = request.files.getlist(section)
            if not files:
                print(f"No files uploaded for {description}")
            for file in files:
                if file:
                    try:
                        file_path = os.path.join(upload_folder, file.filename)
                        file.save(file_path)
                        print(f"Saved file {file.filename} to {file_path}")
                    except Exception as e:
                        print(f"Error saving file {file.filename} in section {description}: {e}")

        return redirect(url_for('comp_dashboard'))

    return render_template('detailed_info.html', comp_id=comp_id)


@app.route('/decision-IPO', methods=['GET', 'POST'])
def decision_ipo():
    if 'comp_id' not in session:
        return redirect(url_for('loginCompany'))
    
    if request.method == 'POST':
        comp_id = session['comp_id']
        reason = request.form.get('reason')
        
        # Insert the data into the database
        cur.execute("INSERT INTO ipoDecision (comp_id, reason) VALUES (%s, %s)", (comp_id, reason))
        cur.execute("UPDATE timeline SET statuss = %s WHERE comp_id = %s", (1, comp_id))
        db.commit()
        
        # Redirect back to the company dashboard or any other page as needed
        return redirect(url_for('comp_dashboard'))
    
    # Render the decision-IPO.html template if it's a GET request
    return render_template('timelineFolder/decision-IPO.html', comp_id=session['comp_id'])

@app.route('/hire-IB', methods=['GET', 'POST'])
def hire_ib():
    if 'comp_id' not in session:
        return redirect(url_for('loginCompany'))
    if request.method == 'POST':
        comp_id = session['comp_id']
        
        # Update the timeline status
        cur.execute("UPDATE timeline SET statuss = %s WHERE comp_id = %s", (2, comp_id))
        db.commit()

        return redirect(url_for('comp_dashboard'))
    
    return render_template('timelineFolder/hire-IB.html', comp_id=session['comp_id'])


@app.route('/underwriting', methods=['GET', 'POST'])
def underwriting():
    if 'comp_id' not in session:
        return redirect(url_for('loginCompany'))

    document_link = None  # Initialize document_link

    if request.method == 'POST':
        # Get company ID from session
        comp_id = session['comp_id']

        # Process form data
        emails = request.form.getlist('email')
        document_link = create_and_share_document(emails)

        # Store data in MySQL database
        cur.execute("INSERT INTO underwritingDocs (comp_id, document_link, emails) VALUES (%s, %s, %s)",
                    (comp_id, document_link, ','.join(emails)))
        cur.execute("UPDATE timeline SET statuss = %s WHERE comp_id = %s", (3, comp_id))
        db.commit()

        return redirect(url_for('underwriting'))

    # GET request: fetch existing document_link if available
    comp_id = session['comp_id']
    cur.execute("SELECT document_link FROM underwritingDocs WHERE comp_id = %s", (comp_id,))
    result = cur.fetchone()
    if result:
        document_link = result[0]

    return render_template('timelineFolder/underwriting.html', comp_id=comp_id, document_link=document_link)




@app.route('/filing-DRHP')
def filing_drhp():
    if 'comp_id' not in session:
        return redirect(url_for('loginCompany'))
    return render_template('timelineFolder/filing-DRHP.html', comp_id=session['comp_id'])

@app.route('/comply-rules')
def comply_rules():
    if 'comp_id' not in session:
        return redirect(url_for('loginCompany'))
    return render_template('timelineFolder/comply-rules.html', comp_id=session['comp_id'])

@app.route('/SEBI-approval')
def sebi_approval():
    if 'comp_id' not in session:
        return redirect(url_for('loginCompany'))
    return render_template('timelineFolder/SEBI-approval.html', comp_id=session['comp_id'])

@app.route('/finalizing-RHP')
def finalizing_rhp():
    if 'comp_id' not in session:
        return redirect(url_for('loginCompany'))
    return render_template('timelineFolder/finalizing-RHP.html', comp_id=session['comp_id'])

@app.route('/roadshows')
def roadshows():
    if 'comp_id' not in session:
        return redirect(url_for('loginCompany'))
    return render_template('timelineFolder/roadshows.html', comp_id=session['comp_id'])

@app.route('/price-building')
def price_building():
    if 'comp_id' not in session:
        return redirect(url_for('loginCompany'))
    return render_template('timelineFolder/price-building.html', comp_id=session['comp_id'])

@app.route('/open-subscription')
def open_subscription():
    if 'comp_id' not in session:
        return redirect(url_for('loginCompany'))
    return render_template('timelineFolder/open-subscription.html', comp_id=session['comp_id'])

@app.route('/share-allotment')
def share_allotment():
    if 'comp_id' not in session:
        return redirect(url_for('loginCompany'))
    return render_template('timelineFolder/share-allotment.html', comp_id=session['comp_id'])

@app.route('/stock-listing')
def stock_listing():
    if 'comp_id' not in session:
        return redirect(url_for('loginCompany'))
    return render_template('timelineFolder/stock-listing.html', comp_id=session['comp_id'])


if __name__ == '__main__':
    app.run(debug=True)
