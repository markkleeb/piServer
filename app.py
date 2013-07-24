# -*- coding: utf-8 -*-
import os, datetime, re
from flask import Flask, request, render_template, redirect, abort
from werkzeug import secure_filename

# import all of mongoengine
from flask.ext.mongoengine import mongoengine

# import data models
import models

# Amazon AWS library
import boto

# Python Image Library
import StringIO


app = Flask(__name__)   # create our flask app
app.secret_key = os.environ.get('SECRET_KEY') # put SECRET_KEY variable inside .env file with a random string of alphanumeric characters
app.config['CSRF_ENABLED'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16 megabyte file upload

# --------- Database Connection ---------
# MongoDB connection to MongoLab's database
mongoengine.connect('mydata', host=os.environ.get('MONGOLAB_URI'))
app.logger.debug("Connecting to MongoLabs")

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])


# --------- Routes ----------

# this is our main page
@app.route("/", methods=['GET','POST'])
def index():

	# get Idea form from models.py
	photo_upload_form = models.photo_upload_form(request.form)
	
	# if form was submitted and it is valid...
	if request.method == "POST" and photo_upload_form.validate():
		
		uploaded_file = request.files['fileupload']
		# app.logger.info(file)
		# app.logger.info(file.mimetype)
		# app.logger.info(dir(file))
		
		# Uploading is fun
		# 1 - Generate a file name with the datetime prefixing filename
		# 2 - Connect to s3
		# 3 - Get the s3 bucket, put the file
		# 4 - After saving to s3, save data to database

		if uploaded_file and allowed_file(uploaded_file.filename):
			# create filename, prefixed with datetime
			now = datetime.datetime.now()
			filename = now.strftime('%Y%m%d%H%M%s') + "-" + secure_filename(uploaded_file.filename)
			# thumb_filename = now.strftime('%Y%m%d%H%M%s') + "-" + secure_filename(uploaded_file.filename)

			# connect to s3
			s3conn = boto.connect_s3(os.environ.get('AWS_ACCESS_KEY_ID'),os.environ.get('AWS_SECRET_ACCESS_KEY'))

			# open s3 bucket, create new Key/file
			# set the mimetype, content and access control
			b = s3conn.get_bucket(os.environ.get('AWS_BUCKET')) # bucket name defined in .env
			k = b.new_key(b)
			k.key = filename
			k.set_metadata("Content-Type", uploaded_file.mimetype)
			k.set_contents_from_string(uploaded_file.stream.read())
			k.make_public()

			# save information to MONGO database
			# did something actually save to S3
			if k and k.size > 0:
				
				submitted_image = models.Image()
				submitted_image.filename = filename # same filename of s3 bucket file
				submitted_image.save()


			return redirect('/')

		else:
			return "uhoh there was an error " + uploaded_file.filename



	else:
		# get existing images
		images = models.Image.objects.order_by('-timestamp')
		tweets = models.Tweet.objects.order_by('-timestamp')
		
		# render the template
		templateData = {
			'images' : images,
			'tweets' : tweets,
			'form' : photo_upload_form
		}

		return render_template("main.html", **templateData)



@app.route("/add", methods=["POST"])
def newloop():

	#app.logger.debug("JSON received...")
	#app.logger.debug(request.form)

	
	if request.form:
		data = request.form

		now = datetime.datetime.now()
		filename = now.strftime('%Y%m%d%H%M%s') + "-" + secure_filename(request.files["img"].filename)

		img = models.Image()
		img.filename = filename
		

		#app.logger.debug(loop.title)

		if request.files["img"]:# and allowed_file(request.files["loop"].filename):

			app.logger.debug(request.files["img"].mimetype)

			s3conn = boto.connect_s3(os.environ.get('AWS_ACCESS_KEY_ID'),os.environ.get('AWS_SECRET_ACCESS_KEY'))

			b = s3conn.get_bucket(os.environ.get('AWS_BUCKET')) #bucket name defined in .env
			k = b.new_key(b)
			k.key =  filename
			k.set_metadata("Content-Type" , request.files["img"].mimetype)
			k.set_contents_from_string(request.files["img"].stream.read())
			k.make_public()


			if k and k.size > 0:

				img.save() 
				return "Received!" 


	else:

		return "FAIL : %s" %request.form
	# get form data - create new idea


@app.route("/tweet", methods=["POST"])
def newtweet():

	#app.logger.debug("JSON received...")
	#app.logger.debug(request.form)

	
	if request.form:
		data = request.form

		now = datetime.datetime.now()
		

		newtweet = models.Tweet()
		newtweet.text = data.get("text")
		newtweet.save()		
		return "Received!" 


	else:

		return "FAIL : %s" %request.form
	# get form data - create new idea



@app.route('/delete/<imageid>')
def delete_image(imageid):
	
	image = models.Image.objects.get(id=imageid)
	if image:

		# delete from s3
	
		# connect to s3
		s3conn = boto.connect_s3(os.environ.get('AWS_ACCESS_KEY_ID'),os.environ.get('AWS_SECRET_ACCESS_KEY'))

		# open s3 bucket, create new Key/file
		# set the mimetype, content and access control
		bucket = s3conn.get_bucket(os.environ.get('AWS_BUCKET')) # bucket name defined in .env
		k = bucket.new_key(bucket)
		k.key = image.filename
		bucket.delete_key(k)

		# delete from Mongo	
		image.delete()

		return redirect('/')

	else:
		return "Unable to find requested image in database."

@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404

def allowed_file(filename):
    return '.' in filename and \
           filename.lower().rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

# --------- Server On ----------
# start the webserver
if __name__ == "__main__":
	app.debug = True
	
	port = int(os.environ.get('PORT', 5000)) # locally PORT 5000, Heroku will assign its own port
	app.run(host='0.0.0.0', port=port)



	