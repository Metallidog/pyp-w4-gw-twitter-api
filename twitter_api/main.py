import sqlite3
from datetime import datetime
from flask import Flask
from flask import g, request, Response, url_for, abort
import json
from hashlib import md5
from random import randint

app = Flask(__name__)
JSON_MIME_TYPE = "application/json"

def connect_db(db_name):
    return sqlite3.connect(db_name)

def _hash_password(password):
    hexd =  md5(password.encode("utf-8"))
    return hexd.hexdigest()
    
def _generate_token():
    #TODO: IMPROVE GE
    token = _hash_password(str(randint(1000, 5000)))
    return (token)
    
@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])

@app.route("/login", methods = ["POST"])
def login():
    token = _generate_token()
    content = request.json
    #checking keys because we don't want bad guys messing around
    #if list(content.keys()) == ['username', 'password']:
    username = content['username']
    password = content['password']
    
    #TODO: CHECK FOR NONE
    hashedPassword = _hash_password(password)

    query = "SELECT id, username, password FROM user WHERE username = ? AND password = ?"
    cursor = g.db.execute(query, (username, hashedPassword))
    results = cursor.fetchone()
    user_id = results[0]
    if results:
        query = "INSERT INTO auth ('user_id', 'access_token') VALUES(?, ?)"
        try:
            cursor = g.db.execute(query, (user_id, token))
            g.db.commit()
        except sqlite3.IntegrityError:
            abort(500)
        else:
            response = Response(
            response = json.dumps({"access_token": token}),
            status = 200,
            mimetype = JSON_MIME_TYPE
            )
        return response
    else:
        print ("aborting")
        abort(404)

@app.route("/logout", methods = ["POST"])
def logout():
    content = request.json
    access_token_to_delete = content["access_token"]
    query = "DELETE FROM auth WHERE access_token = ?"
    g.db.execute(query, (access_token_to_delete,))
    g.db.commit()
    return Response(status=204)

@app.route("/profile/<username>", methods = ['GET'])
def display_profile(username):
    query = "SELECT * from user WHERE username = ?"
    user_data = g.db.execute(query,(username,)).fetchall()[0]
    user_id = user_data[0] #user info missing first name and last name
    query = "SELECT * from tweet WHERE user_id = ?"
    user_tweets = g.db.execute(query,(user_id,)).fetchall()
    tweets = [{"id": t[0], "text": t[3] , "date": t[2], "uri": "uri" } for t in user_tweets] #list of all the tweets

    response = Response(response = json.dumps({"user_id": user_data[0],
                                              "username": username,
                                              "first_name": user_data[3],
                                              "last_name": user_data[4],
                                              "birth_date": user_data[5],
                                              "tweets": tweets,
                                              "tweet_count": len(tweets)
                                            }),
    
                        status = 200,
                        mimetype = JSON_MIME_TYPE
                        )
    return response

@app.route("/profile", methods = ["POST"])
def update_profile():
    content = request.json
    user_id = _get_user_id_with_token(content['access_token'])
    update_list = [key for key in content if key != 'access_token']
    for key in update_list:
        query =  'UPDATE user SET {} = "{}" WHERE id = {}'.format(key, content[key], user_id)
        g.db.execute(query)
    g.db.commit()
    return Response(status=204)

@app.route("/tweet/<tweet_id>", methods = ['GET', 'DELETE'])
def get_tweet(tweet_id):
    if request.method == 'GET':
        query = 'SELECT * FROM tweet WHERE id = {}'.format(tweet_id)
        tweet_info = g.db.execute(query).fetchone()
        print (tweet_info)
        return Response(response = json.dumps( {"id": tweet_id,
                                                "text": tweet_info[3],
                                                "date": tweet_info[2],
                                                "profile": "/profile/<USERNAME>",
                                                "uri": "/tweet/{}".format(tweet_id)}),
                                                status = 200,
                                                mimetype = JSON_MIME_TYPE
                                                )
    elif request.method == 'DELETE':
        content = request.json
        query = "SELECT user_id FROM tweet WHERE id = {}".format(tweet_id)
        try:
            g.db.execute(query).fetchone()[0] ==  _get_user_id_with_token(content['access_token'])
            g.db.execute("DELETE FROM tweet WHERE id = {}".format(tweet_id))
            g.db.commit()
            return Response(status=204)
        except:
            return Response(status=401)
    pass

@app.route("/tweet", methods = ['POST'])
def post_tweet():
    content = request.json
    user_id = _get_user_id_with_token(content['access_token'])
    tweet = content['text']
    query = 'INSERT INTO tweet ("user_id", "content") VALUES ({}, "{}")'.format(user_id, tweet)
    g.db.execute(query)
    g.db.commit()
    return Response(status=204)
    
def _get_user_id_with_token(token):
    query = 'SELECT user_id FROM auth WHERE access_token = ?'
    return g.db.execute(query, (token,)).fetchone()[0]
    
@app.errorhandler(404)
def not_found(e):
    return '', 404

@app.errorhandler(401)
def not_found(e):
    return 'Tweet Not Found', 401
