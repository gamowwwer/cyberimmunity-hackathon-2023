#!/usr/bin/env python

import os
from flask import Flask, make_response, send_file, abort
import zipfile
from hashlib import sha256

port = 6001
app = Flask(__name__)

@app.route('/download-update/<path:filename>')
def get_update(filename):
    
    try:
        print("[FILE-SERVER] got request")

        key = open('data/key.txt', 'r')
        key = key.readline()

        response = make_response(
            send_file(
                path_or_file=f'data/{filename}', 
                mimetype = 'txt', 
                as_attachment=True, 
                download_name=filename
                )
            )
        response.headers['key'] = key

        #print(response)

        return response        
    except FileNotFoundError as e:
        print("[error]", e, os.getcwd())
        abort(404)

if __name__ == "__main__":        # on running python app.py
    app.run(port=port, host="0.0.0.0")