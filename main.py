from flask import Flask, request, jsonify, render_template, make_response, redirect, url_for, session
from authlib.integrations.flask_client import OAuth
from scripts.order_processing import process_order
from scripts.product_processing import process_product
from scripts.db_interact import query_data, schedule_transfer, process_transfer
from datetime import datetime
import logging, os
import pandas as pd
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DateField, IntegerField
from wtforms.validators import DataRequired, NumberRange

app = Flask(__name__)
app.secret_key = 'secret_key'

# Set up forms

class TransferForm(FlaskForm):
    from_location = SelectField('From', choices=[('Groskopf', 'Groskopf'), ('Copper Peak', 'Copper Peak'), ('Donum', 'Donum')], validators=[DataRequired()])
    to_location = SelectField('To', choices=[('Groskopf', 'Groskopf'), ('Copper Peak', 'Copper Peak'), ('Donum', 'Donum')], validators=[DataRequired()])
    transfer_date = DateField('Transfer Date', format='%Y-%m-%d', validators=[DataRequired()])
    sku = StringField('SKU', validators=[DataRequired()])
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1)])

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
        products = df.to_dict('records')  # Convert DataFrame to list of dictionaries
        return render_template('index.html', products=products)
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
    
@app.route('/transfer', methods=['POST'])
def transfer():
    form = TransferForm(request.form)
    if form.validate():
        # Form data is valid, you can process it
        transfer = (
            form.sku.data,
            form.from_location.data,
            form.to_location.data,
            datetime.strptime(form.transfer_date.data, '%Y-%m-%d'),
            form.quantity.data,
            'pending'
        )
        schedule_transfer(*transfer)

        # Process the new transfer if the date is on or before the current date
        process_transfer(transfer)

        # Redirect to the inventory page
        return redirect(url_for('home'))
    else:
        # Form data is invalid, return an error message
        return "Error: The form data is invalid."

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.getenv('PORT', 8080)))