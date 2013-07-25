# -*- coding: utf-8 -*-
import os, datetime, re
from flask import Flask, request, render_template, redirect, abort, jsonify
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
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024 # 16 megabyte file upload

# --------- Database Connection ---------
# MongoDB connection to MongoLab's database
mongoengine.connect('mydata', host=os.environ.get('MONGOLAB_URI'))
app.logger.debug("Connecting to MongoLabs")

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif', 'mp4', 'h264'])


# --------- Routes ----------

# this is our main page
@app.route("/", methods=['GET'])
def index():

		# get existing images
	images = models.Image.objects.order_by('-timestamp')
	tweets = models.Tweet.objects.order_by('-timestamp')
	prompts = models.Question.objects()
		
		# render the template
	templateData = {
		'images' : images,
		'tweets' : tweets,
		'prompts' : prompts
	}

	return render_template("main.html", **templateData)




@app.route("/hashtags", methods=['GET','POST'])
def hash():

	# get Idea form from models.py
	photo_upload_form = models.photo_upload_form(request.form)
	
	# if form was submitted and it is valid...
	if request.method == "POST" and photo_upload_form.validate():
		
		new_post = models.Question.objects.order_by('-timestamp').first()
		new_post.guitar = request.form.get("guitar")
		new_post.typewriter = request.form.get("typewriter")
		new_post.still = request.form.get("still")
		new_post.video = request.form.get("video")
		new_post.prompt = request.form.get("prompt")
				
				
		if new_post.save():

			return redirect('/')

		else:
			return "uhoh there was an error " 



	else:
		# get existing images
		
		prompts = models.Question.objects.order_by('-timestamp')
		
		# render the template
		templateData = {
			
			'form' : photo_upload_form,
			'prompts' : prompts
		}

		return render_template("hashtags.html", **templateData)

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


@app.route('/delete2/<imageid>')
def delete_tweet(imageid):
	tweet = models.Tweet.objects.get(id=imageid)

	if tweet:

		tweet.delete()

		return redirect('/')

	else:
		return "Unable to find tweet"


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


@app.route('/data')
def data():

	# query for the ideas - return oldest first, limit 10
	question = models.Question.objects().order_by('timestamp')

	if question:

		# list to hold ideas
		public_loops = []

		#prep data for json
		for n in question:

			tmpLoop = {
				'prompt' : n.prompt,
				'guitar' : n.guitar,
				'typewriter' : n.typewriter,
				'still' : n.still,
				'video' : n.video
				
			}


			# insert idea dictionary into public_ideas list
			public_loops.append( tmpLoop )

		# prepare dictionary for JSON return
		data = {
			'status' : 'OK',
			'data' : public_loops
		}

		# jsonify (imported from Flask above)
		# will convert 'data' dictionary and set mime type to 'application/json'
		return jsonify(data)

	else:
		error = {
			'status' : 'error',
			'msg' : 'unable to retrieve ideas'
		}
		return jsonify(error)





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



	