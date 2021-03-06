# mongo.py
import os

from flask import Flask
from flask import jsonify
from flask import request
from flask_cors import CORS, cross_origin
from flask import render_template

# from flask_pymongo import PyMongo
import pymongo
from pymongo import MongoClient

app = Flask(__name__)
CORS(app)
# tutorial
client = pymongo.MongoClient('dbh44.mlab.com', 27447)
db = client['attempts']
db.authenticate(os.environ["DB_USERNAME"], os.environ["DB_PASSWORD"])
db.games.ensure_index('gameId', unique=True)

app.config['MONGO_DBNAME'] = 'attempts'
app.config['DB_USERNAME'] = os.environ["DB_USERNAME"]
app.config['DB_PASSWORD'] = os.environ["DB_PASSWORD"]
# app.config['MONGO_URI'] = ''

# mongo = PyMongo(app)
# mongo = client
# mongo.api.authenticate('ImASmarty', '12345')


@app.route('/games', methods=['GET'])
@cross_origin()
def get_all_games():
    games = db.games
    output = []
    for s in games.find({}):
        s.pop('_id')
        # output.append({'name' : s['name'], 'distance' : s['distance']})
        output.append(s)
    return jsonify({'result' : output})

@app.route('/games/<gameId>', methods=['GET'])
def get_one_game(gameId):
    print 'get it'
    game = db.games
    g = game.find_one({'gameId' : gameId})
    if g:
        g.pop('_id')
        output = g
    else:
        output = "No such name"
    return jsonify({'result' : output})

@app.route('/games', methods=['POST'])
def add_game():
    games = db.games
    print 'in post games'
    print request.json
    gameId = request.json['gameId']
    general_game_attributes = ["userId","level"]
    # ensures unique attributes
    specific_game_attributes = list(set(request.json['specificGameAttributes']))#request.json['specificGameAttributes']
    game_id = games.insert({'gameId': gameId, \
                            'generalGameAttributes': general_game_attributes, \
                            'specificGameAttributes':specific_game_attributes, \
                            'attempts':[]
                            })
    new_game = games.find_one({'_id': game_id })
    new_game.pop('_id')
    new_game.pop('attempts')
    return jsonify({'result' : new_game})
    
@app.route('/games/<game_id>/', methods=['POST'])
def add_attempt(game_id):
    print 'in add attempt'
    games = db.games
    attempt = request.json["attempt"]
    for key in attempt:
        attempt[key] = int(attempt[key])
    print attempt
    if len(attempt.keys()) >0:
        games.update({"gameId":game_id}, \
                    { "$push": {"attempts": attempt }
        })
        
        new_game = games.find_one({'gameId': game_id })
        if new_game['_id']:
            new_game.pop('_id')
    else:
        new_game = "you must have params when submitting attempt"
    return jsonify({'result' : new_game})  
 
 
###### aggregate code ##################
def specific_keys_for_attempts():
    games = db.games
    all_games = games.find({})
    get_skeys = db.games.aggregate([
           { "$unwind": "$specificGameAttributes" },
             { "$group": {
                 "_id":"$specificGameAttributes",
                 },
              }
          ])
    return get_skeys
   
# @app.route('/games/aggregate_per_level/', methods=['GET'])
def statistics_for_game_per_level(gameId):
    get_skeys = specific_keys_for_attempts()
    group_options  = {
                        "$group": {
                            "_id":{"gameId":"$gameId","level":"$attempts.level"}
                        }
                    }
    
    aggregate_by_level =   { "$group": { 
                                "_id" :  "$_id.gameId",
                                  "levels": { 
                                      "$push": { 
                                         "level":"$_id.level"
                                         }
                                    }
                                }    
                            }
                  
    for key_obj in get_skeys:
        #### build group_options dict
        key_string = key_obj['_id']
        value_string = "$attempts.%s" %(key_string)
        value_obj = { "$avg":value_string }
        group_options["$group"][key_string] = value_obj
        
        ###build aggregate_by_level dict ####
        aggregate_by_level["$group"]["levels"]["$push"][key_string] = "$%s"%(key_string)
    
    game_instance_stats = db.games.aggregate([
         { "$unwind": "$attempts" },
         {"$match":{"gameId":gameId}},
         group_options,
         aggregate_by_level,
         {"$sort":{ "_id": 1 } },
     ])

    output = list(game_instance_stats)
    return output
    # return jsonify({'result' : output})  
@app.route('/games/aggregate/<game_id>/', methods=['GET'])
def statistics_for_one_games(game_id):
    get_skeys = specific_keys_for_attempts()
          
    group_options  = {
                        "$group": {
                            "_id":"$gameId" 
                        }
                    }
                    
    for key_obj in get_skeys:
        key_string = key_obj['_id']
        value_string = "$attempts.%s" %(key_string)
        value_obj = { "$avg":value_string }
        group_options["$group"][key_string] = value_obj
    # print group_options
    game_instance_stats = db.games.aggregate([
         {"$match":{"gameId":game_id}},
         { "$unwind": "$attempts" },
         group_options,
         {"$sort":{ "_id": 1 } },
         
     ])

    output = list(game_instance_stats)
    output_per_level= statistics_for_game_per_level(game_id)
    if len(output_per_level) >0:
        sorted_output_per_level =  sorted(output_per_level[0]["levels"], key=lambda k: k['level'])
    
        # output_per_level["levels"].sort(key=lambda x: x["level"], reverse=False)
        return render_template('hello.html',output=output,output_per_level=sorted_output_per_level,game_id=game_id)
    else:
        return render_template('need_more.html')
    # return jsonify({'result' : output})  
    
@app.route('/games/aggregate/', methods=['GET'])
def statistics_for_all_games():
    get_skeys = specific_keys_for_attempts()
          
    group_options  = {
                        "$group": {
                            "_id":"$gameId" 
                        }
                    }
                    
    for key_obj in get_skeys:
        key_string = key_obj['_id']
        value_string = "$attempts.%s" %(key_string)
        value_obj = { "$avg":value_string }
        group_options["$group"][key_string] = value_obj
    print group_options
    game_instance_stats = db.games.aggregate([
         { "$unwind": "$attempts" },
         group_options,
         {"$sort":{ "_id": 1 } },
         
     ])

    output = list(game_instance_stats)
    return jsonify({'result' : output})  



###### TEMPLATES ####################
@app.route('/')
def forms():
    return render_template('forms.html')
@app.route('/aggregate/view')
def table():
    return render_template('hello.html',test="hello")


if __name__ == '__main__':
    app.debug = True
    app.run(host=os.getenv('IP', '0.0.0.0'),port=int(os.getenv('PORT', 8080)))

'''
create a new game

curl -i -H "Content-Type: application/json" -X POST \
 'localhost:8080/games' -d '{"gameId":"game3", "generalGameAttributes":["userId","level"],\
 "specificGameAttributes":["timeDeltaInSeconds","points","errors"]}'
 
add attempts to existing game
curl -i -H "Content-Type: application/json" -X POST  \
 'localhost:8080/games/game4/' -d '{"attempt":{"timeDeltaInSeconds":34,"points":3,"errors":1,"userId":3,"level":2}}'
'''