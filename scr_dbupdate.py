from pymongo import MongoClient

client = MongoClient()

db = client.coursepage
dbn = client.netkent
dbnl = client.netkent_lectures

import re

def insert_students(std_list):

	hobbits = list(db.hobbit_names.find())
	
	for i in range(0,100):
		db.students.insert_one({"std_no": std_list[i],
								"name": hobbits[i]["GivenName"],
								"surname": hobbits[i]["Surname"],
								"email": hobbits[i]["EmailAddress"],
								"username": hobbits[i]["Username"] })

def insert_std_courses(std_no):
	for rec in dbn.courselist.find({"ogrenci_no": std_no,
									"ders_kodu": re.compile("MUH")}):
		res = db.courses.find_one({"code": rec["ders_kodu"].replace("MUH", "SMP")})
		if res:
			db.courses.update_one({"_id": res["_id"]},
									{"$push": {"students": std_no}})
		else:
			lectures = list(dbnl.lectures.find({"course": rec["ders_kodu"]},
												projection={"_id": 0,
															"session_no": 1,
															"description": 1,
															"lecture_date": 1}))
			for lecture in lectures:
				lecture["description"] = lecture["description"].replace("muh", "sample")
			db.courses.insert_one({"code": rec["ders_kodu"].replace("MUH", "SMP"),
									"course_name": "Sample Faculty Course " + rec["ders_kodu"].split("MUH")[1],
									"lectures": lectures,
									"students": [std_no]})

def convert_db():

	db.courses.delete_many({})
	db.students.delete_many({})

	std_list = dbn.courselist.distinct("ogrenci_no", {"ders_kodu": re.compile("MUH")})[:100]
	insert_students(std_list)

	for std_no in std_list:
		print(std_no)
		insert_std_courses(std_no)



"""
courses = lst(dbnl.courses.find({"ders_kodu": re.compile("MUH")}))

# insert sample courses
for course in courses:
	db.courses.insert_one({"course_code": course["ders_kodu"].replace("MUH", "ENG"),
							"course_name": "Sample Engineering Course " + course["ders_kodu"].split("MUH")[1]})
	if not insert_students

"""