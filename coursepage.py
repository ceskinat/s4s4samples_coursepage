from flask import Flask, render_template, request, session, redirect, url_for, send_file, make_response, Response, jsonify

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SECRET_KEY'] = 'KeB/9349q58vkdfjgkjc'

S4S4_ADDRESS = 'http://localhost:5010/routing_form'
API_CLIENTID = "coursepage1"
API_KEY = "solus98765" 




from flask_session import Session  # https://pythonhosted.org/Flask-Session
Session(app)

import json

from pymongo import MongoClient
client = MongoClient() 

import re
import requests

def get_courses(user):
	db = client.netkent_lectures
	return [{"code": x["ders_kodu"], "name": x["ders_adi"]} for x in db.courses.find()] 

def get_course_lectures(code):
	db = client.netkent_lectures
	return list(db.lectures.find({"course": code}))

def get_course_titles(code):
	db = client.netkent_lectures
	return list(db.titles.find({"course": code}))

@app.route('/', methods=["GET", "POST"])
def course_page():
	if not session.get("user"):
		session["user"] = {"userid": "test",
		                   "username": "test user",
		                   "email": "test.pluralist.team"}

	courses = get_courses(session["user"])
	params = {}

	if request.method == "POST": #course selected
		crs_code = request.form["slct-course"]
		params["lectures"] = get_course_lectures(crs_code)
		params["titles"] = get_course_titles(crs_code)

	return render_template("coursepage.html",
							courselist=courses,
							lectures=params.get("lectures", []),
							titles=params.get("titles", []),
							s4s4_address=S4S4_ADDRESS

							)

@app.route('/add_title', methods=["POST"])
def add_title():
	db = client.netkent_lectures
	course = request.form["inp-course"]
	baslik = request.form["newtitle"]
	if db.titles.find_one({"course": course, 
							"title": re.compile(baslik, re.I)}):
		return "Bu başlık bu ders için daha önce yaratılmış"
	db.titles.insert_one({"course": course,
							"title": baslik,
							"description": request.form.get("description", "")})
	courses = get_courses()
	crs_code = request.form["inp-course"]
	params = {"lectures": get_course_lectures(crs_code)}
	params["titles"] = get_course_titles(crs_code)

	return render_template("coursepage.html",
						courselist=courses,
						lectures=params.get("lectures", []),
						titles=params.get("titles", [])
							)

@app.route('/usr_list', methods=["POST"])
def usr_list():
	db = client.netkent_lectures
	inp = request.form.get("name", "")
	lst = []
	for ogr in db.ogrenci.find({"$or": [{"ad": re.compile(inp, re.I)},
										{"soyad": re.compile(inp, re.I)}]}):
		name = ogr["ad"] + " " + ogr["soyad"]
		oid = str(ogr["ogrenci_no"]) + "|*|*" + name + "|*|*" + ogr["email"]
		lst.append({"id": oid,
					"name": name})
	return json.dumps(lst)	


@app.route('/change_user', methods=["POST"])
def change_user():
	user_ary = request.form.get("obj_id", " |*|* |*|* ").split("|*|*")
	session["user"] = {"userid": user_ary[0],
	                   "username": user_ary[1],
	                   "email": user_ary[2]}
	return redirect("/")


@app.route('/get-auth-code', methods=['GET'])
def api_code():
	return jsonify({"api_key": API_KEY,
					"client_id": API_CLIENTID})

""" secure call proxy not relevant anymore
@app.route('/call_s4s4', methods=['POST'])
def submit_form():

	S4S4_ADDRESS = 'http://localhost:5010/routing_form'
	API_KEY = "solus98765" #

    # Extract form data from client submission
	form_data = request.form.to_dict()
    # Forward the form data to the external API with the API key in the headers

	response = requests.post(S4S4_ADDRESS, 
								headers={'Authorization': f'Bearer {API_KEY}',
										'Accept': "text/html"}, 
								data=form_data)
    
	# Return the response to the client
	#return jsonify(response.json()), response.status_code
	return response.text
"""
""" interface api routes """


@app.route('/interfaces/coursepage/object_list', methods=['POST'])
def obj_lst():
    # user is a dictionary containing username, userid, email
    # returns a list of objects
 
    inp = request.form.get("inp", "")
    userid = request.form.get("user", {})

    print("Userid: ", userid, " Input: ", inp)

    dbn = client.netkent
    db = client.netkent_lectures
    doc = db.s4s4rights.find_one({"userid": userid})
    if not doc or doc["role"] == "student":
        courselist = [x["ders_kodu"] for x in dbn.courselist.find({"ogrenci_no": userid})]
    elif doc.get("role") == "master":
        courselist = [x["ders_kodu"] for x in db.courses.find()]

    elif doc.get("role") == "lecturer":
        courselist = doc["courses"]



    lst = []

    #courses
    for crs in db.courses.find({"ders_kodu": {"$in": courselist},
                                "$or": [{"ders_kodu": re.compile(inp, re.I)},
                                        {"ders_adi": re.compile(inp, re.I)}]}):
        lst.append({"id": {"id": ["ders", str(crs["ders_kodu"])], "name": crs["ders_adi"]},
                    "name": "ders" + ":" + crs["ders_adi"]})

    #lectures
    for lect in db.lectures.find({"course": {"$in": courselist},
                                    "$or": [{"course": re.compile(inp, re.I)},
                                        {"description": re.compile(inp, re.I)}]}):
        lst.append({"id": {"id": ["oturum", lect["course"] + "*!*!" + lect["session_no"]], "name": lect["description"]},
                    "name": "oturum" + ":" + lect["description"]})

    #titles
    for title in db.titles.find({"course": {"$in": courselist},
                                    "$or": [{"course": re.compile(inp, re.I)},
                                            {"title": re.compile(inp, re.I)}]}):
        lst.append({"id": {"id": ["başlık", title["course"] + "*!*!" + title["title"]], "name": title["title"]},
                    "name": "başlık" + ":" + title["course"] + " " + title["title"]})

    return lst

@app.route('/interfaces/coursepage/object_name', methods=['POST'])
def obj_name():

    otype = request.form["otype"]
    oid = request.form["oid"]
    db = client.netkent_lectures
    if otype == "ders":
        doc = db.courses.find_one({"ders_kodu": oid})
        if doc:
            return doc["ders_adi"]
    elif otype in ["oturum", "başlık"]:
        course = oid.split('*!*!')[0]
        if otype == "oturum":
            doc = db.lectures.find_one({"course": course,
                                        "session_no": oid.split('*!*!')[1]})
            if doc:
                return doc["description"]
        else: # otype == başlık
            return oid.split('*!*!')[1]



"""
def all_users():
    # returns in the form of {"id": id, "name": username}
    db = client.routeX_demo
    
    return [{"id": x["_id"], "name": x["username"], "email": x.get("email", "") } for x in db.users.find()]
"""
@app.route('/interfaces/coursepage/authorized_users', methods=['POST'])
def auth_users():

	otype = request.form["otype"]
	oid = request.form["oid"]

	db = client.netkent_lectures
	dbn = client.netkent

	auth_users = []
	# admins
	for admin in db.s4s4rights.find({"role": {"$in": ["master", "admin"]}}):
	    auth_users.append({"id": admin["userid"], "name": admin["username"], "email": admin.get("email")})

	if otype == "ders":
	    course = oid
	elif otype in ["oturum", "başlık"]:
	    course = oid.split('*!*!')[0]
	else:
	    course = ""

	# lecturers
	for lect in db.s4s4rights.find({"role": "lecturer",
	                            "courses": course }):
	    auth_users.append({"id": lect["userid"], "name": lect["username"], "email": lect.get("email")})

	# students
	for std in dbn.courselist.find({"ders_kodu": course}):
	    ogr = dbn.ogrencilist.find_one({"ogrenci_no": std["ogrenci_no"]})
	    if ogr:
	        auth_users.append({"id": ogr["ogrenci_no"], "name": ogr["ad"] + " " + ogr["soyad"], "email": ogr["eposta_adresi"]})

	return auth_users



if __name__ == '__main__':
    app.run(debug = True, host = "0.0.0.0", port=5020)
