#!/usr/bin/env python3

import os
import time
import glob
import json
import signal
import requests
import threading
import tkinter as tk
from itertools import cycle
from PIL import ImageTk, Image
from flask import Flask, request, send_file, redirect

WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080

IMAGES_FOLDER = './img/'
DEFAULT_IMG = 'flair.png'

app = Flask(__name__)

class PictureStore():
	def __init__(self):
		self.mutex = threading.Lock()
		self.index = 0;
		self.images = []
		self.add_image(DEFAULT_IMG)

	def __len__(self):
		with self.mutex:
			return len(self.images)

	def add_image(self, image: str):
		with self.mutex:
			self.images.append(image)

	def get_image(self, index: int= -1):
		with self.mutex:
			if index == -1:
				if self.index >= len(self.images):
					self.index = 0;
				img = self.images[self.index]
				self.index += 1
				self.index %= len(self.images)
				return img
			else:
				return self.images[index]

	def get_images(self):
		with self.mutex:
			return self.images.copy();

	def remove_image(self, index: int):
		with self.mutex:
			self.images.pop(index)

	def reset_index(self):
		with self.mutex:
			self.index = 0;

class Window(tk.Tk):
	'''Tk window/label adjusts to size of image'''
	def __init__(self):
		tk.Tk.__init__(self)
		self.geometry('1920x1080+0+0')
		self.delay = 5000
		self.picture_display = tk.Label(self)
		self.picture_display.pack()
	def show_slides(self):
		'''cycle through the images and show them'''
		img = picture_store.get_image()
		self.image = ImageTk.PhotoImage(Image.open(IMAGES_FOLDER + img).resize((WINDOW_WIDTH, WINDOW_HEIGHT), Image.ANTIALIAS))
		self.picture_display.config(image=self.image)
		self.title(img)
		self.after(self.delay, self.show_slides)
	def run(self):
		self.mainloop()

window = None
picture_store = PictureStore()

@app.before_first_request
def activate_job():
	def run_job():
		global window
		window = Window()
		window.show_slides()
		window.run()
	thread = threading.Thread(target=run_job)
	thread.start()

@app.route("/")
def index():
	return send_file('index.html', mimetype='text/html')

@app.route("/bootstrap")
def bootstrap():
	return send_file('node_modules/bootstrap/dist/css/bootstrap.min.css', mimetype='text/css')

@app.route("/logo.png")
def logo():
	return send_file('logo.png', mimetype='image/png')

@app.route("/images", methods=['GET', 'POST', 'DELETE'])
def images():
	if request.method == 'GET':
		return json.dumps(sorted(os.listdir(IMAGES_FOLDER))), 200
	elif request.method == 'POST':
		f = request.files['file']
		f.save(IMAGES_FOLDER + f.filename)
		return "", 201
	elif request.method == 'DELETE':
		filename = request.form.get('filename', default='', type=str)
		if filename == '':
			return "", 400
		if filename == DEFAULT_IMG:
			return "", 403
		os.remove(IMAGES_FOLDER + filename)
		return "", 204
	else:
		return "", 405

@app.route("/frames", methods=['GET', 'POST', 'DELETE'])
def frames():
	if request.method == 'GET':
		return json.dumps(picture_store.get_images()), 200
	elif request.method == 'POST':
		filename = request.form.get('filename', default='', type=str)
		if filename == '':
			return "", 400
		picture_store.add_image(filename)
		return "", 201
	elif request.method == 'DELETE':
		index = request.form.get('index', default=-1, type=int)
		if index == -1:
			return "", 400
		if index == 0:
			return "", 403
		if index >= len(picture_store):
			return "", 409
		picture_store.remove_image(index)
		return "", 204
	else:
		return "", 405

@app.route("/frames/time", methods=['GET', 'POST'])
def frames_times():
	if request.method == 'GET':
		return str(window.delay), 200
	elif request.method == 'POST':
		delay = request.form.get('delay', default=-1, type=int)
		if delay == -1:
			return "", 400
		window.delay = delay
		return "", 204
	else:
		return "", 405

@app.route("/system/stop", methods=['GET'])
def system_stop():
	os.kill(os.getpid(), signal.SIGINT)
	return "", 200

@app.route("/system/restart", methods=['GET'])
def system_restart():
	subprocess.run('sudo reboot', shell=True)
	return "", 200

@app.route("/system/shutdown", methods=['GET'])
def system_shutdown():
	subprocess.run('sudo shutdown', shell=True)
	return "", 200

def window_runner():
	def start_loop():
		not_started = True
		while not_started:
			try:
				r = requests.get('http://127.0.0.1:5000/')
				if r.status_code == 200:
					print('Server started')
					not_started = False
			except:
				print('starting ...')
			time.sleep(2)
	thread = threading.Thread(target=start_loop)
	thread.start()

if __name__ == "__main__":
	window_runner()
	app.run(host='0.0.0.0')
