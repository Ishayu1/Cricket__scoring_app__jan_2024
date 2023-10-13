from flask import Blueprint, render_template, redirect, url_for,request, flash, session, jsonify
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

auth = Blueprint("auth",__name__)

def check_session():
    if "username" not in session:
        return redirect(url_for("auth.login"))

@auth.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password, password):
                flash("Logged in", category="success")
                login_user(user, remember=True)
                session['username'] = email
                return redirect(url_for("views.home"))
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
    return redirect(url_for("views.home"))

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
                    "team": team

                }
        )

        db.session.commit()

        flash("Player created")

        # Redirect to the same page to display the player list as a pop-up
        return redirect(url_for("auth.create_player"))

    players = db.session.execute(text("SELECT * FROM players WHERE user_created = :username"), {"username": session["username"]}).fetchall()
    print(players)

    return render_template("create_player.html", players=players)


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
            csv_file = csv.reader(file.stream.read().decode('utf-8').splitlines())
            
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
        print(team_players)


    return render_template('create_team.html', team_players=team_players)



@auth.route("/match_setup", methods=["GET", "POST"])
@login_required
def match_setup():
    teams = db.session.execute(text("SELECT DISTINCT team FROM players WHERE user_created = :username"), {"username": session["username"]}).fetchall()
    current_date = datetime.now().date().strftime("%Y-%m-%d")
    if request.method == "POST":
        # Retrieve form data
        overs = int(request.form.get("overs"))
        wide_runs = int(request.form.get("wideRuns"))
        no_ball_runs = int(request.form.get("noBallRuns"))
        free_hits = request.form.get("freeHits") == "true"
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
    text("INSERT INTO match (match_id, team1, team2, match_date, wide_runs, no_ball_runs, wide_reball, free_hits, overs, user) "
         "VALUES (:match_id, :team1, :team2, :match_date, :wide_runs, :no_ball_runs, :wide_reball, :free_hits, :overs, :user)"),
    {
        "match_id": match_id,
        "team1": team1_name,
        "team2": team2_name,
        "match_date": match_date,
        "wide_runs": wide_runs,
        "no_ball_runs": no_ball_runs,
        "wide_reball": wide_reball,
        "free_hits": free_hits,
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
# only show recent matches change query
    return render_template("match_setup.html", matches = matches, current_date=current_date, teams = teams)


@auth.route("/ball_update/<int:id>", methods=["GET", "POST"])
@auth.route("/ball_update/<int:id>/<string:team_name>", methods=["GET", "POST"])
@login_required
def ball_update(id, team_name=None):
    # convert into function
    total_overs, wide_runs, no_ball_runs = db.session.execute(
        text("SELECT overs, wide_runs, no_ball_runs FROM match WHERE match_id = :id"), 
        {"id": id}).fetchone()
    # call only if matchlog doesn't have this match_id
    matchlog = db.session.execute(text("SELECT * FROM matchlog WHERE match_id=:id"), {"id":id}).fetchone()
    if matchlog:
        session["ball_counter"] = matchlog[1] + 1
        session["team1"] = matchlog[2]
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
            
            if session["ball_counter"] % 6 ==0:
                session["current_over"] +=1
            print(f'ball counter {session["ball_counter"]}')
            print(f'current over {session["current_over"]}')
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

            
            
            flash("Score updated")
            if session["ball_counter"] % 6==0:
                flash("End of over")
            # innings end check 
            if session["ball_counter"] == session["total_balls"]:
                if session["innings"] == 1:
                    flash("Innings 1 over")
                    team_name = session["team2"] if team_name == session["team1"] else session["team1"]
                    session["ball_counter"] = 0
                    session["innings"] += 1
                elif session["innings"] == 2:
                    
                    flash("Match over")
                    # Optionally reset the innings and ball_counter for a new match or to avoid any further updates for the current match
                    session["ball_counter"] = 0
                    session["innings"] = 1
            else:
                session["ball_counter"] += 1

           
        elif "update_id" in request.form:  # If any "Update" button in the log table was pressed
            update_id = request.form.get("update_id")
            
            batsman_name = request.form.get(f"batsman_{update_id}")
            bowler_name = request.form.get(f"bowler_{update_id}")
            runs = request.form.get(f"runs_{update_id}")
            extra = request.form.get(f"extra_{update_id}")
            extra_id = db.session.execute(text("SELECT extra_id FROM extras WHERE extra_type = :extra"),{"extra":extra}).fetchone()[0]
            dismissal = request.form.get(f"dismissal_{update_id}")
            dismissal_id = db.session.execute(text("SELECT Dismissal_ID FROM dismissals WHERE Dismissal_type = :dismissal"),{"dismissal":dismissal}).fetchone()[0]
            batsman_firstname, batsman_lastname = batsman_name.split()
            bowler_firstname, bowler_lastname = bowler_name.split()

            batsman_id = db.session.execute(text("SELECT player_id FROM players WHERE firstname = :firstname AND lastname = :lastname"), {"firstname": batsman_firstname, "lastname": batsman_lastname}).fetchone()[0]
            bowler_id = db.session.execute(text("SELECT player_id FROM players WHERE firstname = :firstname AND lastname = :lastname"), {"firstname": bowler_firstname, "lastname": bowler_lastname}).fetchone()[0]

            db.session.execute(text("UPDATE outcome SET Batter_ID=:batsman_id, Bowler_ID=:bowler_id, Runs=:runs, Extras_ID=:extra, Dismissal_ID=:dismissal WHERE ball_ID = :update_id"), 
                               {
                                   "batsman_id": batsman_id,
                                   "bowler_id": bowler_id,
                                   "runs": runs,
                                   "extra": extra_id,
                                   "dismissal": dismissal_id,
                                   "update_id": update_id
                               })
            db.session.commit()
            print(f"{batsman_name},{bowler_name},{runs},{extra},{dismissal}")
            flash("Log updated")

        return redirect(url_for("auth.ball_update", id=id, team_name=team_name))

    else:
        
        match = db.session.execute(text("SELECT * FROM match WHERE match_id = :id"), {"id": id}).fetchone()

        players = db.session.execute(
            text("SELECT * FROM players WHERE user_created = :user"),
            {"user": session["username"]}
        ).fetchall()

        dropdown_options = [(player.player_id, f"{player.firstname} {player.lastname}") for player in players]
        dropdown_options.append((-1, "Choose a New Player"))

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

        return render_template("ball_update.html", id=id, match=match, dropdown_options=dropdown_options, updates=updates,team1=session["team1"],team2=session["team2"])

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
    # Fetch batsman scores
    batsman_scores = db.session.execute(text("""
        SELECT 
        firstname || " " || lastname as batsman,
        sum(Runs) as runs_scored,
        count(ball_ID) as balls_faced,
        COUNT(CASE WHEN Runs = 4 THEN 1 ELSE NULL END) as fours,
        COUNT(CASE WHEN Runs = 6 THEN 1 ELSE NULL END) as sixes,     
        ((sum(Runs)*1.0)/count(ball_ID)) * 100 as strike_rate
        FROM outcome
        JOIN players 
        ON outcome.Batter_ID = players.player_id
        WHERE match_id = :match_id 
        AND Team_name = "Test_1"
        group by batsman
    """), {"match_id": match_id}).fetchall()


    # Fetch bowler scores
    bowler_scores = db.session.execute(text("""
        SELECT 
        firstname || " " || lastname as bowler,
        ((count(ball_ID)/6)+((count(ball_ID)%6)/10.0)) as overs,
        sum(runs) as runs_given,
        COUNT(CASE WHEN Dismissal_ID > 1 THEN 1 ELSE NULL END) as wickets,                          
        ((sum(Runs)*1.0)/((count(ball_ID) * 1.0)/6)) as economy
        FROM outcome
        JOIN players 
        ON outcome.Bowler_ID = players.player_id
        WHERE match_id = :match_id 
        AND Team_name = "Test_1"
        GROUP BY bowler
    """), {"match_id": match_id}).fetchall()

    getcwd = os.getcwd()

    # Fetch data from the database
    over_runs = db.session.execute(text("""
        SELECT over,
        sum(Runs) as runs,
        COUNT(CASE WHEN Runs = 4 THEN 1 ELSE NULL END) as fours_per_over,
        COUNT(CASE WHEN Runs = 6 THEN 1 ELSE NULL END) as sixes_per_over
        FROM outcome
        WHERE match_id = :match_id
        GROUP BY over
        ORDER BY over
    """), {"match_id": match_id}).fetchall()

    print(over_runs, file=sys.stdout)


    # Create DataFrame
    overs, runs, fours, sixes = zip(*over_runs)
    match = {"over": overs, "runs": runs, "fours": fours, "sixes": sixes}
    
    df = pd.DataFrame(match)

    plt.switch_backend("agg")

    # Plotting runs per over
    plt.figure(figsize=(10, 6))
    plt.plot(df['over'], df['runs'], color='green', marker='o', label='Runs')
    plt.xlabel('Overs')
    plt.ylabel('Runs')
    plt.title('Runs per Over')
    plt.xticks(df['over'])
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)
    image_path_runs = getcwd + f"/website/static/images/runs_per_over_{match_id}.png"
    if os.path.exists(image_path_runs):
        os.remove(image_path_runs)
    plt.savefig(image_path_runs)

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
    plt.title('4s and 6s per Over')
    plt.xticks([r + bar_width for r in range(len(df['over']))], df['over'])
    plt.legend()
    plt.grid(True, which='both', linestyle='--', linewidth=0.5, axis='y')  # Only horizontal grid lines

    plt.tight_layout()
    image_path_boundaries = getcwd + f"/website/static/images/fours_sixes_per_over_{match_id}.png"
    if os.path.exists(image_path_boundaries):
        os.remove(image_path_boundaries)
    plt.savefig(image_path_boundaries)


    return render_template('scorecard.html', batsman_scores=batsman_scores, bowler_scores=bowler_scores, match_id=match_id)



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

