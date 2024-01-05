from flask import Blueprint, render_template, redirect, url_for,request, flash, session, jsonify,current_app
from . import db, mail
from .models import User
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Message
from random import randint
from datetime import datetime
from sqlalchemy import text
import requests
import json
import pandas as pd
import matplotlib.pyplot as plt
import os
import sys
import numpy as np
import csv
from werkzeug.utils import secure_filename
import base64
auth = Blueprint("auth",__name__)

def check_session():
    if "username" not in session:
        logout_user()
        return redirect(url_for("auth.login"))
    

@auth.route("/", methods=["GET","POST"])
@auth.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()
        print(f"users: {user}")
        if user:
            if check_password_hash(user.password, password):
                flash("Logged in", category="success")
                login_user(user, remember=True)
                session['username'] = email
                return redirect(url_for("auth.create_team"))
            else:
                flash("Password is incorrect", category="error")
        else:
            flash("Email does not exist", category="error")
    return render_template("login.html")

@auth.route("/sign_up", methods=["GET","POST"])
def sign_up():
    if request.method == "POST": 
        #email = request.form.get("email")
        email = request.form["email"]
        password = request.form.get("password")
        password1 = request.form.get("password1")

        email_exists = User.query.filter_by(email=email).first()
        activate = []
        if email_exists:
            flash("Email is already in use", category="error")
            activate.append(0)
        if password != password1:
            flash("Passwords do not match", category="error")
            activate.append(0)
        if len(password) <8:
            flash("Password must be at least 8 characters", category="error")
            activate.append(0)
           
        if len(activate)==0:
            msg = Message("Registration", sender = "ishayu.ghosh@gmail.com", recipients=[email])
            msg.body = f'''
            <h3>Hello {email},welcome to the website</h3>
            '''
            try:
                mail.send(msg)
            except:
                flash("Email not sent, please check your settings", category="error")
            else:
                new_user = User(email=email, password= generate_password_hash(password, method="sha256"))
                db.session.add(new_user)
                db.session.commit()
                flash("User created")
                login_user(new_user, remember=True)
               
        
        return redirect(url_for("auth.sign_up"))
        
        
    return render_template("sign_up.html")

@auth.route("/change_password", methods=["GET","POST"])
def change_password():
    if request.method == "POST":
        email = request.form["email"]
        email_exists = User.query.filter_by(email=email).first()
        if email_exists:
            # add reset code for the user
            # the link will contain the reset code
            reset_code = randint(100000,1000000)
            email_exists.reset_code = reset_code
            db.session.commit()
            msg = Message("Change password", sender = "ishayu.ghosh@gmail.com", recipients=[email])
            msg.html = f'''
                <h3>Hello {email}, click the link to change password</h3>
                <a href="http://127.0.0.1:5000/reset_password/{reset_code}">Click here</a>
                ''' 
            
            try:
                mail.send(msg)
                flash("Email has been sent with a reset code", category="success")
            except:
                flash("Email not sent, please check your settings", category="error")
        else:
            flash("Email doesn't exist", category="error")

    return render_template("change_password.html")
    



@auth.route("/reset_password/<int:reset_id>",  methods=["GET","POST"])
def reset_password(reset_id):
    reset_code_exists = User.query.filter_by(reset_code=reset_id).first()
    return render_template("reset_password.html",user=reset_code_exists)

@auth.route("/reset_password_confirm", methods = ["GET","POST"])
def reset_password_confirm():
    if request.method=="POST":
        password = request.form["password"]
        email = request.form["email"]
        password1 = request.form["password1"]
        activate = []
        if password != password1:
            flash("Passwords do not match", category="error")
            activate.append(0)
        if len(password) <8:
            flash("Password must be at least 8 characters", category="error")
            activate.append(0)
        if len(activate)==0:
            #update password in database and remove reset code
            update_user = User.query.filter_by(email=email).first()
            update_user.password = generate_password_hash(password, method="sha256")
            update_user.reset_code = None
            db.session.commit()
            flash("Password has been reset",category="success")
            return render_template("login.html")
        else:
            return render_template("reset_password_confirm")
        
    else:
        return render_template("login.html")
            

@auth.route("/sign_out")
@login_required 
def sign_out():
    logout_user()
    return redirect(url_for("auth.login"))

@auth.route("/create_player", methods=["GET", "POST"])
@login_required
def create_player():
    if request.method == "POST":
        firstName = request.form['firstName']
        lastName = request.form['lastName']
        battingStyle = request.form['battingStyle']
        bowlingStyle = request.form['bowlingStyle']
        team = request.form["teamName"]
        while True:
            player_id = randint(100000, 1000000)
            id_exists = db.session.execute(text("SELECT 1 FROM players WHERE player_id = :player_id"), {"player_id": player_id}).fetchone()
            if not id_exists:
                break

        date = datetime.now().date()

        cursor = db.session.execute(
                text("INSERT INTO players (player_id, firstname, lastname, batting_style, bowling_style, date_created, user_created, team) VALUES (:player_id, :firstname, :lastname, :batting_style, :bowling_style, :date_created, :user_created, :team)"),
                {
                    "player_id": player_id,
                    "firstname": firstName,
                    "lastname": lastName,
                    "batting_style": battingStyle,
                    "bowling_style": bowlingStyle,
                    "date_created": date,
                    "user_created": session["username"],
                    "team": get_team_id(team)

                }
        )

        db.session.commit()

        flash("Player created")

        # Redirect to the same page to display the player list as a pop-up
        return redirect(url_for("auth.create_player"))

    players = db.session.execute(text("SELECT * FROM players WHERE user_created = :username"), {"username": session["username"]}).fetchall()
    # print(players)
    teams = db.session.execute(text("SELECT team_name FROM teams WHERE created_by = :username"), {"username": session["username"]}).fetchall()
    # print(teams)
    return render_template("create_player.html", players=players, teams=teams)


ALLOWED_EXTENSIONS = {'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@auth.route('/create_team', methods=['GET', 'POST'])
@login_required
def create_team():
    date = datetime.now().date()
    team_players = {}
    team_name_file = ""
    team_players_dict = {}
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            file_content = file.stream.read().decode('utf-8-sig')  
            csv_file = csv.reader(file_content.splitlines())
            
            for x,row in enumerate(csv_file,start=1):
                firstName, lastName, battingStyle, bowlingStyle, team = row
                if x == 1:
                    team_name_file += team
                    # print(f"THIS IS THE TEAM NAME {team_name_file}")
                    cursor = db.session.execute(text("SELECT team_name, team_id FROM teams WHERE team_name = :team"),{"team": team}).fetchone()
                    
                    # print(cursor)
                    if cursor:
                        # fetching team id for existing team
                        team_id = cursor[1]

                    else:
                        # generating team id for new team
                        team_id = randint(100000,1000000)
                        cursor = db.session.execute(text("INSERT INTO teams (team_id,team_name,date_created,date_modified,created_by) VALUES (:team_id,:team_name,:date_created,:date_modified,:created_by)"),{"team_id":team_id,"team_name":team,"date_created":date,"date_modified":date,"created_by":session["username"]})
                
                while True:
                    player_id = randint(100000, 1000000)
                    id_exists = db.session.execute(text("SELECT 1 FROM players WHERE player_id = :player_id"), {"player_id": player_id}).fetchone()
                    if not id_exists:
                        break

                    

                cursor = db.session.execute(
                    text("INSERT INTO players (player_id, firstname, lastname, batting_style, bowling_style, date_created, user_created, team) VALUES (:player_id, :firstname, :lastname, :batting_style, :bowling_style, :date_created, :user_created, :team)"),
                    {
                        "player_id": player_id,
                        "firstname": firstName,
                        "lastname": lastName,
                        "batting_style": battingStyle,
                        "bowling_style": bowlingStyle,
                        "date_created": date,
                        "user_created": session["username"],
                        "team": team_id
                    }
                )


            db.session.commit()
            flash('Team added successfully')
            return redirect(url_for('auth.create_team'))
    teams = db.session.execute(text("SELECT DISTINCT team,team_name FROM players, teams WHERE team=team_id AND user_created = :username"), {"username": session["username"]}).fetchall()
    print(teams)
    if teams:  # Check if there are teams
        for team in teams:
            # print(team)
            players_in_team = db.session.execute(text("SELECT * FROM players WHERE user_created = :username AND team = :team"), {"username": session["username"], "team": team[0]}).fetchall()
            team_players[team[1]] = players_in_team
        # print(team_players)


    return render_template('create_team.html', team_players=team_players)



@auth.route("/match_setup", methods=["GET", "POST"])
@login_required
def match_setup():
    teams = db.session.execute(text("SELECT team_name FROM teams WHERE created_by = :username"), {"username": session["username"]}).fetchall()
    current_date = datetime.now().date().strftime("%Y-%m-%d")
    
    if request.method == "POST":
        # Retrieve form data
        overs = int(request.form.get("overs"))
        wide_runs = int(request.form.get("wideRuns"))
        no_ball_runs = int(request.form.get("noBallRuns"))
        no_ball_reball = request.form.get("no_ball_reball") == "true"
        team1_name = request.form.get("team1Name")
        team2_name = request.form.get("team2Name")
        wide_reball = request.form.get("wide_reball") == "true"

        # Generate a unique match ID
        while True:
            match_id = randint(100000, 1000000)
            id_exists = db.session.execute(text("SELECT 1 FROM match WHERE match_id = :match_id"), {"match_id": match_id}).fetchone()
            if not id_exists:
                break

        # Get the current date
        match_date = request.form.get("matchDate")
        

        cursor = db.session.execute(
    text("INSERT INTO match (match_id, team1, team2, match_date, wide_runs, no_ball_runs, wide_reball, no_ball_reball, overs, user) "
         "VALUES (:match_id, :team1, :team2, :match_date, :wide_runs, :no_ball_runs, :wide_reball, :no_ball_reball, :overs, :user)"),
    {
        "match_id": match_id,
        "team1": team1_name,
        "team2": team2_name,
        "match_date": match_date,
        "wide_runs": wide_runs,
        "no_ball_runs": no_ball_runs,
        "wide_reball": wide_reball,
        "no_ball_reball": no_ball_reball,
        "overs": overs,
        "user": session["username"]
    }
)

        db.session.commit()


        flash("Match created")

        return redirect(url_for("auth.match_setup"))
    matches = db.session.execute(
    text("SELECT * FROM match WHERE user = :username ORDER BY match_date DESC"),
    {"username": session["username"]}).fetchall()
        
        # Execute the query with parameters
    print(matches)
# only show recent matches change query
    return render_template("match_setup.html", matches = matches, current_date=current_date, teams = teams)


@auth.route("/ball_update/<int:id>", methods=["GET", "POST"])
@auth.route("/ball_update/<int:id>/<string:team_name>", methods=["GET", "POST"])
@login_required
def ball_update(id, team_name=None):

    # convert into function
    total_overs, wide_runs, no_ball_runs,wide_reball,no_ball_reball = db.session.execute(
        text("SELECT overs, wide_runs, no_ball_runs, wide_reball, no_ball_reball FROM match WHERE match_id = :id"), 
        {"id": id}).fetchone()
    # call only if matchlog doesn't have this match_id
    matchlog = db.session.execute(text("SELECT * FROM matchlog WHERE match_id=:id"), {"id":id}).fetchone()
    if matchlog:
        session["ball_counter"] = matchlog[1] + 1
        teams = db.session.execute(text("SELECT team1,team2 FROM match WHERE match_id = :id"), {"id": id}).fetchone()
        session["team1"] = matchlog[2]
        session["team2"] = teams[0] if matchlog[2] != teams[0] else teams[1]
        session["innings"] = matchlog[3]
        #check 
        session["current_over"] = (session["ball_counter"] + 5) // 6
    else:
        session["total_balls"] = int(total_overs) * 6 
        session["ball_counter"] = 1
        session["current_over"] = 1
        teams = db.session.execute(text("SELECT team1,team2 FROM match WHERE match_id = :id"), {"id": id}).fetchone()
        session["team1"], session["team2"] = teams

        session["innings"] = 1

    #fetching team name
    # if not team_name:
    #     teams = db.session.execute(text("SELECT team1,team2 FROM match WHERE match_id = :id"), {"id": id}).fetchone()
    #     session["team1"], session["team2"] = teams
    # if "ball_counter" not in session:
    #     session["ball_counter"] = 1
    # if "innings" not in session:
    #     session["innings"] = 1
    # if "current_over" not in session:
    #     session["current_over"] = 1
    # print(session["team1"])
    # print(session["team2"])
    score = db.session.execute(text("""
    SELECT 
        SUM(Runs) AS total_runs,
        COUNT(CASE WHEN Dismissal_ID != 1 THEN 1 END) AS total_dismissals
    FROM outcome
    WHERE match_id = :match_id 
        AND Team_name = :team1;
    """), {"match_id": id,"team1":session["team1"]}).fetchone()
    

    if request.method == "POST":
        if "add_ball" in request.form:  # If the "Update Ball" button was pressed
            
            batsman_id = int(request.form.get("batsman"))
            bowler_id = int(request.form.get("bowler"))
            runs = int(request.form.get("runs"))
            team_name = request.form.get("team")
            extra = int(request.form.get("extras"))
            dismissal = int(request.form.get("dismissals"))
            if batsman_id == -1:
                return redirect(url_for("auth.create_player"))

            if bowler_id == -1:
                return redirect(url_for("auth.create_player"))
            
            # if session["ball_counter"] % 6 ==0:
                # session["current_over"] +=1
            # print(f'ball counter {session["ball_counter"]}')
            # print(f'current over {session["current_over"]}')
            reball_needed = False
            if extra == 2:
                runs += wide_runs
                if wide_reball:
                    reball_needed = True
            elif extra == 3:
                runs += no_ball_runs
                if no_ball_reball:
                    reball_needed = True
            cursor = db.session.execute(
                text("INSERT INTO outcome (match_id, Scorer_ID, Runs, Batter_ID, Bowler_ID, Extras_ID, over, Dismissal_ID, Team_name) "
                    "VALUES (:match_id, :Scorer_ID, :Runs, :Batter_ID, :Bowler_ID, :Extras_ID, :over, :Dismissal_ID, :Team_name)"),
                {
                    "match_id": id,
                    "Scorer_ID": 1,  # add query
                    "Runs": runs,
                    "Batter_ID": batsman_id,
                    "Bowler_ID": bowler_id,
                    "Extras_ID": extra,
                    "over": session["current_over"],  # map extra type to id
                    "Dismissal_ID": dismissal,
                    "Team_name": team_name,  # query from match table
                }
            )
            # updating matchlog table
            # saving current status of match (everything complete already)
            if reball_needed:
                session["ball_counter"] -= 1

            print(reball_needed)
            flash("Score updated")
            if not reball_needed:
                if session["ball_counter"] % 6==0:
                    flash("End of over")
                    session["current_over"] +=1
                # innings end check 
                if session["ball_counter"] == session["total_balls"] or session["ball_counter"] == (session["total_balls"]*2):
                    if session["innings"] == 1:
                        flash("Innings 1 over")
                        team_name = session["team2"] if team_name == session["team1"] else session["team1"]
                        session["ball_counter"] = 0
                        session["innings"] += 1
                    elif session["innings"] == 2:   
                        
                        flash("Match over")
                        db.session.execute(text("UPDATE match SET match_end = 'True' WHERE match_id = :match_id AND match_end = 'False'"), {'match_id': id})
                        db.session.commit()
                        # Optionally reset the innings and ball_counter for a new match or to avoid any further updates for the current match
                        session["ball_counter"] = 0
                        session["innings"] = 1
                # else:
                    
                #     session["ball_counter"] += 1

            if not matchlog:
                cursor2 = db.session.execute(text("""INSERT INTO matchlog (match_id, current_ball, batting_team, innings) 
                                                VALUES (:match_id, :current_ball, :batting_team, :innings)"""),
                                                
                                                {
                                                    "match_id": id,
                                                    "current_ball":session["ball_counter"],
                                                    "batting_team":team_name,
                                                    "innings": session["innings"],
                                                })
            else:
                cursor2 = db.session.execute(text("UPDATE matchlog SET current_ball = :current_ball, batting_team = :batting_team, innings= :innings WHERE match_id = :match_id"), 
                                             {
                                                    "current_ball":session["ball_counter"],
                                                    "batting_team":team_name,
                                                    "innings": session["innings"],
                                                    "match_id": id, 
                                                  })
            db.session.commit()
            print(f"""ball_counter: {session["ball_counter"]},
batting_team: {team_name},
innings:{session["innings"]},
total_balls:{session["total_balls"]}
current_over:{session["current_over"]}
""")
           
        elif "update_id" in request.form:
            # If any "Update" button in the log table was pressed
            update_id = request.form.get("update_id")

            batsman_name = request.form.get(f"batsman_{update_id}")
            bowler_name = request.form.get(f"bowler_{update_id}")
            runs = request.form.get(f"runs_{update_id}")
            extra = request.form.get(f"extra_{update_id}")
            dismissal = request.form.get(f"dismissal_{update_id}")

            # Check for None values
            if None not in (update_id, batsman_name, bowler_name, runs, extra, dismissal):
                extra_id = db.session.execute(text("SELECT extra_id FROM extras WHERE extra_type = :extra"), {"extra": extra}).fetchone()[0]
                dismissal_id = db.session.execute(text("SELECT Dismissal_ID FROM dismissals WHERE Dismissal_type = :dismissal"), {"dismissal": dismissal}).fetchone()[0]

                # Split names only if they are not None
                batsman_firstname, batsman_lastname = batsman_name.split() if batsman_name else ("", "")
                bowler_firstname, bowler_lastname = bowler_name.split() if bowler_name else ("", "")
                # Fetch player IDs only if names are not empty
                batsman_id = db.session.execute(text("SELECT player_id FROM players WHERE firstname = :firstname AND lastname = :lastname"), {"firstname": batsman_firstname, "lastname": batsman_lastname}).fetchone()
                bowler_id = db.session.execute(text("SELECT player_id FROM players WHERE firstname = :firstname AND lastname = :lastname"), {"firstname": bowler_firstname, "lastname": bowler_lastname}).fetchone()
                # Check if player IDs are not None
                if None not in (batsman_id, bowler_id):
                    db.session.execute(text("UPDATE outcome SET Batter_ID=:batsman_id, Bowler_ID=:bowler_id, Runs=:runs, Extras_ID=:extra, Dismissal_ID=:dismissal WHERE ball_ID = :update_id"),
                                    {
                                        "batsman_id": batsman_id[0],
                                        "bowler_id": bowler_id[0],
                                        "runs": runs,
                                        "extra": extra_id,
                                        "dismissal": dismissal_id,
                                        "update_id": update_id
                                    })
                    db.session.commit()
                    flash("Log updated")
                else:
                    flash("Error: Unable to fetch player IDs.")
            else:
                flash("Error: One or more form fields are missing.")


        return redirect(url_for("auth.ball_update", id=id, team_name=team_name))


    else:

        match = db.session.execute(text("SELECT * FROM match WHERE match_id = :id"), {"id": id}).fetchone()

        players = db.session.execute(
            text("SELECT * FROM players WHERE user_created = :user"),
            {"user": session["username"]}
        ).fetchall()
        # Assuming you have team1 and team2 variables set in your Flask route
        team1_players = [(player.player_id, f"{player.firstname} {player.lastname}",session["team1"]) for player in players if player.team == get_team_id(session["team1"])]
        team2_players = [(player.player_id, f"{player.firstname} {player.lastname}",session["team2"]) for player in players if player.team == get_team_id(session["team2"])]
        
        # Combine the filtered players for team1 and team2
        dropdown_options = team1_players + team2_players

        # dropdown_options = [(player.player_id, f"{player.firstname} {player.lastname} {get_team_name(player.team)}") for player in players]
        # dropdown_options.append((-1, "Choose a New Player"))
        out_players_query = """
        SELECT players.player_id
        FROM outcome
        JOIN players ON outcome.Batter_ID = players.player_id
        WHERE outcome.match_id = :id AND outcome.Dismissal_ID != 1
        """
        out_players = [row[0] for row in db.session.execute(text(out_players_query), {"id": id})]

        updates = db.session.execute(
            text("SELECT outcome.*, players_batsman.firstname AS batsman_firstname, players_batsman.lastname AS batsman_lastname, players_bowler.firstname AS bowler_firstname, players_bowler.lastname AS bowler_lastname,Dismissal_type, extra_type "
                "FROM outcome "
                "JOIN players AS players_batsman ON outcome.Batter_ID = players_batsman.player_id "
                "JOIN players AS players_bowler ON outcome.Bowler_ID = players_bowler.player_id "
                "JOIN extras AS extra ON outcome.Extras_ID = extra.extra_id "
                "JOIN dismissals AS dismissal ON outcome.Dismissal_ID = dismissal.Dismissal_ID "
                "WHERE outcome.match_id = :id"),
            {"id": id}
        ).fetchall()
        # print(dropdown_options)
        # print(team_name)
        # print(session["team1"])
        # print(session["team2"])
        # print(session["ball_counter"])
        # print(session["total_balls"])
        return render_template("ball_update.html", id=id, match=match, dropdown_options=dropdown_options, updates=updates,team1=session["team1"],team2=session["team2"],out_players=out_players, total_runs=score)

def get_team_name(team_id):
    # Replace this with your actual code to fetch the team name from the database
    team_name = db.session.execute(text("SELECT team_name FROM teams WHERE team_id = :team_id"), {"team_id": team_id}).scalar()
    return team_name
def get_team_id(team_name):
    # Replace this with your actual code to fetch the team name from the database
    team_id = db.session.execute(text("SELECT team_id FROM teams WHERE team_name = :team_name"), {"team_name": team_name}).scalar()
    return team_id

@auth.route("/test_api")
@login_required
def test_api():
    list_players = []
    query = None
    player = request.args.get("player")
    
    if  not player:
        query = db.session.execute(text("SELECT * FROM players WHERE user_created=:user"), {"player": player,"user": session["username"]})
    else: 
        pass
    
    for q in query:
        list_players.append({"player_id": q[0], "firstname": q[1], "lastname": q[2], "batting style": q[3], "bowling style": q[4]})

    return jsonify(list_players)

@auth.route("/fetch_api")
@login_required
def fetch_api():
    url = "https://cricbuzz-cricket.p.rapidapi.com/matches/v1/recent"

    headers = {
        "X-RapidAPI-Key": "8bb790bcc8msh9d55e0f52cc3b26p1b1655jsn34be60245c09",
        "X-RapidAPI-Host": "cricbuzz-cricket.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers)

    with open("match_list.json","w") as f:
        json.dump(response.json(),f,indent=4)
    return redirect(url_for("auth.fetch_data"))


@auth.route("/fetch_data")
@login_required
def fetch_data():
    with open("match_list.json","r") as f:
        values = json.load(f)
        base = values["typeMatches"]
        base3 = []
        for i in base:
            base2 = i["seriesMatches"]
            for j in base2:
                for x in j:
                    if x == "seriesAdWrapper":
                        base3.append(j[x]["matches"])
                            
    return render_template("api_data.html",match_data = base3)


@auth.route("/get_scoreboard/<int:matchId>")
@login_required
def get_scoreboard(matchId):
    with open("match_scoreboard.json","r") as f:
        scoreboards = json.load(f)
    for i in scoreboards:
        exists = False
        if i["scoreCard"][0]["matchId"] == matchId:
            exists = True
            break
        
    if not exists:

        url = f"https://cricbuzz-cricket.p.rapidapi.com/mcenter/v1/{matchId}/hscard"

        headers = {
        "X-RapidAPI-Key": "8bb790bcc8msh9d55e0f52cc3b26p1b1655jsn34be60245c09",
        "X-RapidAPI-Host": "cricbuzz-cricket.p.rapidapi.com"
        }
        response = requests.get(url, headers=headers)
        scoreboards.append(response.json())
        with open("match_scoreboard.json","w") as f:
            json.dump(scoreboards,f,indent=4)

    
    
    
    return redirect(url_for('auth.api_scoreboard', match_id=matchId))


                     
@auth.route("/scoreboard_test/<int:match_id>", methods=["GET", "POST"])
@login_required
def scoreboard(match_id):
    # Fetch team names
    team_names = db.session.execute(text("""
        SELECT team1, team2 FROM match WHERE match_id = :match_id
    """), {"match_id": match_id}).fetchone()
    team1, team2 = team_names

    # Fetch batsman scores - Innings 1
    batsman_scores_innings1 = db.session.execute(text("""
        SELECT 
        firstname || " " || lastname as batsman,
        sum(Runs) as runs_scored,
        COUNT(CASE WHEN Extras_ID = 1 THEN 1 END) as balls_faced,
        COUNT(CASE WHEN (Runs = 4 OR Runs = 5) THEN 1 ELSE NULL END) as fours,
        COUNT(CASE WHEN (Runs = 6 OR Runs = 7) THEN 1 ELSE NULL END) as sixes,
        ((SUM(CASE WHEN Extras_ID = 1 THEN Runs ELSE 0 END)*1.0) / 
        COUNT(CASE WHEN Extras_ID = 1 THEN 1 ELSE NULL END)) * 100 as strike_rate
        FROM outcome
        JOIN players 
        ON outcome.Batter_ID = players.player_id
        WHERE match_id = :match_id 
        AND Team_name = :team1
        group by batsman
    """), {"match_id": match_id, "team1": team1}).fetchall()

    # Fetch bowler scores - Innings 1
    bowler_scores_innings1 = db.session.execute(text("""
        SELECT 
        firstname || " " || lastname as bowler,
        ((COUNT(CASE WHEN Extras_ID = 1 THEN ball_ID ELSE NULL END)/6) + 
        ((COUNT(CASE WHEN Extras_ID = 1 THEN ball_ID ELSE NULL END) % 6)/10.0)) as overs,
        sum(runs) as runs_given,
        COUNT(CASE WHEN Dismissal_ID > 1 THEN 1 ELSE NULL END) as wickets,                          
        ((sum(Runs)*1.0)/((count(ball_ID) * 1.0)/6)) as economy
        FROM outcome
        JOIN players 
        ON outcome.Bowler_ID = players.player_id
        WHERE match_id = :match_id 
        AND Team_name = :team1
        GROUP BY bowler
    """), {"match_id": match_id, "team1": team1}).fetchall()

    # Fetch data from the database - Innings 1
    over_runs_innings1 = db.session.execute(text("""
        SELECT over,
        sum(Runs) as runs,
        COUNT(CASE WHEN (Runs = 4 OR Runs = 5) THEN 1 ELSE NULL END) as fours_per_over,
        COUNT(CASE WHEN (Runs = 6 OR Runs = 7) THEN 1 ELSE NULL END) as sixes_per_over
        FROM outcome
        WHERE match_id = :match_id
        AND Team_name = :team1
        GROUP BY over
        ORDER BY over
    """), {"match_id": match_id, "team1": team1}).fetchall()

    # Generate and save graphs - Innings 1
    generate_and_save_graphs(match_id, over_runs_innings1, "innings1")

    # Fetch batsman scores - Innings 2
    batsman_scores_innings2 = db.session.execute(text("""
        SELECT 
        firstname || " " || lastname as batsman,
        sum(Runs) as runs_scored,
        COUNT(CASE WHEN Extras_ID = 1 THEN 1 END) as balls_faced,
        COUNT(CASE WHEN (Runs = 4 OR Runs = 5) THEN 1 ELSE NULL END) as fours,
        COUNT(CASE WHEN (Runs = 6 OR Runs = 7) THEN 1 ELSE NULL END) as sixes,  
        (SUM(Runs*1.0) / COUNT(CASE WHEN Extras_ID = 1 THEN ball_ID END)) * 100 as strike_rate
        FROM outcome
        JOIN players 
        ON outcome.Batter_ID = players.player_id
        WHERE match_id = :match_id 
        AND Team_name = :team2
        group by batsman
    """), {"match_id": match_id, "team2": team2}).fetchall()

    # Fetch bowler scores - Innings 2
    bowler_scores_innings2 = db.session.execute(text("""
        SELECT 
        firstname || " " || lastname as bowler,
        ((COUNT(CASE WHEN Extras_ID = 1 THEN ball_ID ELSE NULL END)/6) + 
        ((COUNT(CASE WHEN Extras_ID = 1 THEN ball_ID ELSE NULL END) % 6)/10.0)) as overs,
        sum(runs) as runs_given,
        COUNT(CASE WHEN Dismissal_ID > 1 THEN 1 ELSE NULL END) as wickets,                          
        ((sum(Runs)*1.0)/((count(ball_ID) * 1.0)/6)) as economy
        FROM outcome
        JOIN players 
        ON outcome.Bowler_ID = players.player_id
        WHERE match_id = :match_id 
        AND Team_name = :team2
        GROUP BY bowler
    """), {"match_id": match_id, "team2": team2}).fetchall()

    # Fetch data from the database - Innings 2
    over_runs_innings2 = db.session.execute(text("""
        SELECT over,
        sum(Runs) as runs,
        COUNT(CASE WHEN (Runs = 4 OR Runs = 5) THEN 1 ELSE NULL END) as fours_per_over,
        COUNT(CASE WHEN (Runs = 6 OR Runs = 7) THEN 1 ELSE NULL END) as sixes_per_over
        FROM outcome
        WHERE match_id = :match_id
        AND Team_name = :team2
        GROUP BY over
        ORDER BY over
    """), {"match_id": match_id, "team2": team2}).fetchall()

    # Generate and save graphs - Innings 2
    generate_and_save_graphs(match_id, over_runs_innings2, "innings2")

    github_username = "Ishayu1"
    github_repo = "graphs"
    github_token = "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"

    return render_template('scorecard.html',
                           batsman_scores_innings1=batsman_scores_innings1,
                           bowler_scores_innings1=bowler_scores_innings1,
                           batsman_scores_innings2=batsman_scores_innings2,
                           bowler_scores_innings2=bowler_scores_innings2,
                           match_id=match_id, team1=team1, team2=team2,
                           github_username=github_username, github_repo=github_repo, github_token=github_token)


def generate_and_save_graphs(match_id, over_runs, innings):
    # Create DataFrame
    overs, runs, fours, sixes = zip(*over_runs)
    match = {"over": overs, "runs": runs, "fours": fours, "sixes": sixes}
    df = pd.DataFrame(match)
    print(over_runs)
    plt.switch_backend("agg")

    # Plotting runs per over
    plt.figure(figsize=(10, 6))
    plt.plot(df['over'], df['runs'], color='green', marker='o', label='Runs')
    plt.xlabel('Overs')
    plt.ylabel('Runs')
    plt.title(f'Runs per Over - {innings}')
    plt.xticks(df['over'])
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)

    # Save the image locally
    image_path_runs = os.path.join(current_app.root_path, 'static', 'images', f'runs_per_over_{match_id}_{innings}.png')
    plt.savefig(image_path_runs)

    # Upload the image to GitHub repository
    upload_to_github(image_path_runs, f'runs_per_over_{match_id}_{innings}.png')

    # Plotting 4s and 6s per over
    plt.figure(figsize=(10, 6))

    # Calculate bar width and positions
    bar_width = 0.35
    r1 = np.arange(len(df['over']))
    r2 = [x + bar_width for x in r1]

    # Plotting 4s per over as bars
    plt.bar(r1, df['fours'], color='blue', width=bar_width, edgecolor='grey', label='4s')

    # Plotting 6s per over as bars
    plt.bar(r2, df['sixes'], color='red', width=bar_width, edgecolor='grey', label='6s')

    plt.xlabel('Overs', fontweight='bold')
    plt.ylabel('Counts')
    plt.title(f'4s and 6s per Over - {innings}')
    plt.xticks([r + bar_width for r in range(len(df['over']))], df['over'])
    plt.legend()
    plt.grid(True, which='both', linestyle='--', linewidth=0.5, axis='y')  # Only horizontal grid lines

    plt.tight_layout()

    # Save the image locally
    image_path_boundaries = os.path.join(current_app.root_path, 'static', 'images', f'fours_sixes_per_over_{match_id}_{innings}.png')
    plt.savefig(image_path_boundaries)

    # Upload the image to GitHub repository
    upload_to_github(image_path_boundaries, f'fours_sixes_per_over_{match_id}_{innings}.png')

def upload_to_github(file_path, file_name):
    # GitHub repository details
    github_username = "Ishayu1"
    github_repo = "graphs"
    github_token = "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"

    # GitHub API endpoint for uploading
    upload_url = f'https://uploads.github.com/repos/{github_username}/{github_repo}/contents/website/static/images/{file_name}'

    # Open the file and read its content
    with open(file_path, 'rb') as file:
        content = file.read()

    # Base64 encode the content
    content_base64 = base64.b64encode(content).decode('utf-8')

    # Prepare headers for the GitHub API request
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'token {github_token}'
    }

    # Prepare data for the GitHub API request
    data = {
        'message': f'Upload {file_name}',
        'content': content_base64,
    }

    # Make the GitHub API request to upload the file
    response = requests.put(upload_url, headers=headers, json=data)

    # Check if the upload was successful
    if response.status_code == 200:
        print(f'Successfully uploaded {file_name} to GitHub.')
    else:
        print(f'Error uploading {file_name} to GitHub. Status Code: {response.status_code}, Response: {response.text}')

    return response




@auth.route("/api_scorecard/<int:match_id>", methods=["GET", "POST"])
def api_scoreboard(match_id):
    try:
        with open('match_scoreboard.json', 'r') as file:
            data = json.load(file)
            
            # Find the scorecard with the matching matchId
            for item in data:
                for score in item['scoreCard']:
                    if score['matchId'] == match_id:
                        for item in data:
                            innings_data = []
                            for score in item['scoreCard']:
                                if score['matchId'] == match_id:
                                    wickets_data = score['wicketsData']
                                    # sorted_wickets_data = sorted(wickets_data, key=lambda x: x['over'])
                                    innings = {
                                        "bat_team_data": score['batTeamDetails']['batsmenData'],
                                        "bat_team_name": score['batTeamDetails']['batTeamName'],
                                        "bowl_team_data": score['bowlTeamDetails']['bowlersData'],
                                        "bowl_team_name": score['bowlTeamDetails']['bowlTeamName'],
                                        "extras_data": score['extrasData'],
                                        "wickets_data": score['wicketsData']
                                    }   
                                    innings_data.append(innings)

                                # # Extracting batsman names and their respective runs
                                # batsmen = [batsman['batName'] for batsman in innings_data[0]['bat_team_data'].values()]
                                # runs = [batsman['runs'] for batsman in innings_data[0]['bat_team_data'].values()]

                                # # Generating the bar chart
                                # plt.figure(figsize=(10, 6))
                                # plt.bar(batsmen, runs, color='blue')
                                # plt.xlabel('Batsmen')
                                # plt.ylabel('Runs')
                                # plt.title('Runs Scored by Each Batsman')
                                # plt.xticks(rotation=45)
                                # plt.tight_layout()

                                # # Save the plot to a file with match_id in the filename
                                # plot_filename = os.path.join('static', 'images', f'api_batsman_runs_{match_id}.png')
                                # plt.savefig(plot_filename)
                                # plt.close()
                                                        
                            if innings_data:
                                return render_template('api_scorecard.html',innings_data=innings_data)
                        
                        # If no matching matchId is found, return an error message
                        return jsonify({"error": "Match ID not found"}), 404
    except:
        return jsonify({"error": "Match ID not found"}), 404

