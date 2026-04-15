import csv

from flask import Flask, render_template, request, redirect


app = Flask(__name__)

@app.route("/")                        
def home():                     
    return render_template('index.html')


@app.route("/submit_form", methods=['POST', 'GET'])
def submit_form():
    if request.method == 'POST':
        try:
                
            data = request.form.to_dict()
            addTOdatabase(data)
            return redirect('/thankyou.html')
        except:
            return 'Did not save to the DataBase'
    else:
        return 'Something went wrong'


@app.route("/<string:page>")
def page(page):
    return render_template(page)


def addTOdatabase(data):
    with open('database.csv', mode='a', newline='') as database:
        email = data["email"]
        subject = data["subject"]
        message = data["message"]
        csvW = csv.writer(database, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)  
        csvW.writerow([email,subject,message])        

    