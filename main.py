from flask import Flask, request, jsonify, render_template, make_response, redirect, url_for, session
from authlib.integrations.flask_client import OAuth
from order_processing import process_order
from product_processing import process_product
from db_interact import query_data
import logging, os
import pandas as pd

app = Flask(__name__)
app.secret_key = 'secret_key'

# Set up logging
logging.basicConfig(filename='app.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Set up OAuth2
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id='193979034931-9vapdt600bnr0ptf8mn8ifc9lvvof6pr.apps.googleusercontent.com',
    client_secret='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',
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',  # This is only needed if using openId to fetch user info
    client_kwargs={'scope': 'openid email profile'},
)

@app.route('/_ah/ready')
def readiness_check():
    return 'OK', 200

@app.route('/commerce7_webhook', methods=['POST'])
def handle_webhook():
    try:
        data = request.get_json()
        process_functions = {
            'Order': process_order,
            'Product': process_product,
        }
        process_function = process_functions.get(data.get('object'))
        if process_function:
            process_function(data)
        return jsonify({'message': 'Received'}), 200
    except Exception as e:
        logging.error(f"Error handling webhook: {e}")

@app.route('/login')
def login():
    redirect_uri = url_for('authorize', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/authorize')
def authorize():
    token = google.authorize_access_token()
    resp = google.get('userinfo')
    user_info = resp.json()
    # Do something with the token and profile
    session['user'] = user_info
    return redirect('/')

@app.route('/')
def home():
    try:
        disp_statement = 'SELECT * FROM "InventoryDisp"'
        data, metadata = query_data(disp_statement)
        df = pd.DataFrame(data, columns=[field.name for field in metadata.row_type.fields])
        table = df.to_html()
        return render_template('index.html', table=table)
    except Exception as e:
        return f"An error occurred: {e}"

@app.route('/export')
def export():
    try:
        disp_statement = 'SELECT * FROM "Inventory"'
        data, metadata = query_data(disp_statement)
        df = pd.DataFrame(data, columns=[field.name for field in metadata.row_type.fields])
        csv = df.to_csv(index=False)
        response = make_response(csv)
        response.headers["Content-Disposition"] = "attachment; filename=inventory.csv"
        response.headers["Content-Type"] = "text/csv"
        return response
    except Exception as e:
        return f"An error occurred: {e}"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.getenv('PORT', 8080)))