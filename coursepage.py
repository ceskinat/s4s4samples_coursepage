from flask import Flask, render_template, request, session, redirect, url_for, send_file, make_response, Response, jsonify

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SECRET_KEY'] = 'KeB/9349q58vkdfjgkjc'

app.jinja_loader.searchpath.append('shared/combobox/templates')


""" configure your application here """
S4S4_ADDRESS = 'http://localhost:5015/routing_form'
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
	db = client.coursepage
	# return [{"code": x["code"], "name": x["course_name"]} for x in db.courses.find()] 
	return [{"code": x["code"], "name": x["course_name"]} for x in db.courses.find({"students": user["userid"]})] 

def get_course_lectures(code):
	db = client.coursepage
	res = db.courses.find_one({"code": code})
	if res:
		return res.get("lectures", [])
	else:
		return []

def get_course_titles(code):
	db = client.coursepage
	res = db.courses.find_one({"code": code})
	if res:
		return res.get("titles", [])
	else:
		return []

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
	db = client.coursepage
	course = request.form["inp-course"]
	baslik = request.form["newtitle"]
	if db.courses.find_one({"code": course, 
							"titles.title": re.compile(baslik, re.I)}):
		return "This topic is already present for this course"
	db.courses.update_one({"code": course},
						{"$push": {"titles": {"title": baslik,
									"description": request.form.get("description", "")
									}}
						})
	courses = get_courses(session["user"])
	crs_code = request.form["inp-course"]
	params = {"lectures": get_course_lectures(crs_code)}
	params["titles"] = get_course_titles(crs_code)

	return render_template("coursepage.html",
						courselist=courses,
						lectures=params.get("lectures", []),
						titles=params.get("titles", []),
						s4s4_address=S4S4_ADDRESS
							)

@app.route('/usr_list', methods=["POST"])
def usr_list():
	db = client.coursepage
	inp = request.form.get("name", "")
	lst = []
	for ogr in db.students.find({"$or": [{"name": re.compile(inp, re.I)},
										{"surname": re.compile(inp, re.I)}]}):
		name = ogr["name"] + " " + ogr["surname"]
		oid = str(ogr["std_no"]) + "|*|*" + name + "|*|*" + ogr["email"]
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

    db = client.coursepage
    doc = db.s4s4rights.find_one({"userid": userid})
    if not doc or doc["role"] == "student":
        courselist = [x["code"] for x in db.courses.find({"students": userid})]
    elif doc.get("role") == "master":
        courselist = [x["code"] for x in db.courses.find()]

    elif doc.get("role") == "lecturer":
        courselist = doc["courses"]



    lst = []

    #courses
    for crs in db.courses.find({"code": {"$in": courselist},
                                "$or": [{"code": re.compile(inp, re.I)},
                                        {"course_name": re.compile(inp, re.I)}]}):
        lst.append({"id": {"id": ["course", str(crs["code"])], "name": crs["course_name"]},
                    "name": "course" + ":" + crs["course_name"]})

    #lectures
    for course in db.courses.find({"code": {"$in": courselist},
                                    "$or": [{"code": re.compile(inp, re.I)},
                                    		{"course_name": re.compile(inp, re.I)},
                                        {"lectures.description": re.compile(inp, re.I)}]}):
    	for lect in course.get("lectures", []):
    		if re.search(re.compile(inp, re.I), course["code"]) or re.search(re.compile(inp, re.I), course["course_name"]) or re.search(re.compile(inp, re.I), lect["description"]):
	 	       lst.append({"id": {"id": ["session", course["code"] + "*!*!" + lect["session_no"]], "name": lect["description"]},
    		                "name": "session" + ":" + lect["description"]})

    #titles
    for course in db.courses.find({"code": {"$in": courselist},
                                    "$or": [{"code": re.compile(inp, re.I)},
                                    		{"course_name": re.compile(inp, re.I)},
                                            {"titles.title": re.compile(inp, re.I)},
                                            {"titles.description": re.compile(inp, re.I)}]}):
    	for title in course.get("titles", []):
    		reg = re.compile(inp, re.I)
    		if re.search(reg, course["code"]) or re.search(reg, course["course_name"]) or re.search(reg, title["title"]) or re.search(reg, title["description"]):
		        lst.append({"id": {"id": ["title", course["code"] + "*!*!" + title["title"]], "name": title["title"]}, "name": "title" + ":" + course["code"] + " " + title["title"]})

    return lst

@app.route('/interfaces/coursepage/object_name', methods=['POST'])
def obj_name():

	otype = request.form["otype"]
	oid = request.form["oid"]
	db = client.coursepage
	if otype == "course":
		doc = db.courses.find_one({"code": oid})
		if doc:
			return doc["course_name"]
	elif otype in ["session", "title"]:
		course = oid.split('*!*!')[0]
		if otype == "session":
			doc = db.courses.find_one({"code": course})
			for lect in doc.get("lectures", []):
				if lect["session_no"] == oid.split('*!*!')[1]:
					return lect["description"]
			return ""

		else: # otype == title
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

	db = client.coursepage

	auth_users = []
	# admins
	for admin in db.s4s4rights.find({"role": {"$in": ["master", "admin"]}}):
	    auth_users.append({"id": admin["userid"], "name": admin["username"], "email": admin.get("email")})

	if otype == "course":
	    course = oid
	elif otype in ["session", "title"]:
	    course = oid.split('*!*!')[0]
	else:
	    course = ""

	# lecturers
	for lect in db.s4s4rights.find({"role": "lecturer",
	                            "courses": course }):
	    auth_users.append({"id": lect["userid"], "name": lect["username"], "email": lect.get("email")})

	# students
	doc = db.courses.find_one({"code": course})
	if doc: 
		stdlist = doc.get("students", [])
		for std in db.students.find({"std_no": {"$in": stdlist}}):
			auth_users.append({"id": std["std_no"], "name": std["name"] + " " + std["surname"], "email": std["email"]})

	print(auth_users)

	return auth_users



if __name__ == '__main__':
    app.run(debug = True, host = "0.0.0.0", port=5020)
