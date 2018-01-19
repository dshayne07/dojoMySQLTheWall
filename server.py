from flask import Flask, render_template, redirect, request, session, flash
import re
from mysqlconnection import MySQLConnector
import md5
import bcrypt

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')
app = Flask(__name__)
mysql = MySQLConnector(app,'walldb')
app.secret_key="oiwajefoaiwnegwboughuao"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["POST"])
def register():
    error = False
    query = "SELECT * FROM users WHERE email = :email"
    emailExists = mysql.query_db(query, request.form)
    if len(request.form['fname']) < 2:
        flash("First Name must be at least 2 characters!", "error") # just pass a string to the flash function
        error = True
    elif not request.form['fname'].isalpha():
        flash("First Name cannot contain numbers!", "error")
        error = True
    if len(request.form['lname']) < 2:
        flash("Last Name must be at least 2 characters!", "error")
        error = True
    elif not request.form['lname'].isalpha():
        flash("Last Name cannot contain numbers!", "error")
        error = True
    if len(request.form['email']) < 1:
        flash("Email cannot be empty!", "error")
        error = True
    elif not EMAIL_REGEX.match(request.form['email']):
        flash("Invalid Email Address!", "error")
        error = True
    if len(emailExists) > 0:
        flash("That email is already taken!", "error")
        error = True
    if len(request.form['password']) < 1:
        flash("Password cannot be empty!", "error")
        error = True
    elif len(request.form['password']) < 8:
        flash("Password must be longer than 8 characters", "error")
        error = True
    if request.form['password'] != request.form['confirmPassword']:
        flash("Passwords don't match!", "error")
        error = True
    if not error:
        fname = request.form['fname']
        lname = request.form['lname']
        email = request.form['email']
        password = bcrypt.hashpw(request.form['password'].encode(), bcrypt.gensalt())
        insert_query = "INSERT INTO users (first_name, last_name, email, password, created_at, updated_at) VALUES (:fname, :lname, :email, :password, NOW(), NOW())"
        query_data = { 'fname': fname, 'lname': lname, 'email': email, 'password': password }
        mysql.query_db(insert_query, query_data)
        session.clear()
        flash("Successfully registered!", "success")
        return redirect('/')
    flash(True, "login")
    flash(request.form, "data")

    return redirect('/') # either way the application should return to the index and display the message

@app.route("/login", methods=["POST"])
def login():
    error = False
    if len(request.form['email']) < 1:
        flash("Email cannot be empty!", "error")
        error = True
    elif not EMAIL_REGEX.match(request.form['email']):
        flash("Invalid Email Address!", "error")
        error = True
    if not error:
        email = request.form['email']
        query = "SELECT * FROM users WHERE email = :email"
        user = mysql.query_db(query, request.form)
        if len(user) > 0 and (bcrypt.checkpw(request.form['password'].encode(), user[0]['password'].encode())):
            flash(request.form, "data")
            session["name"] = user[0]['first_name']+" "+user[0]['last_name']
            session['uid'] = user[0]['id']
            return redirect('/wall')
        else:
            flash("Invalid username/password", "error")
    flash(request.form, "data")
    return redirect('/')

@app.route("/wall")
def wall():
    if "uid" in session:
        query = "SELECT first_name, last_name, message, DATE_FORMAT(messages.created_at,'%M %d %Y (%r)') AS created_at, messages.id FROM messages JOIN users on users.id=messages.user_id"
        messages = mysql.query_db(query)
        print messages
        query = "SELECT first_name, last_name, comment, DATE_FORMAT(comments.created_at,'%M %d %Y (%r)') AS created_at, message_id, comments.id FROM comments JOIN users on users.id=comments.user_id"
        comments = mysql.query_db(query)
        return render_template("wall.html", messages=messages, comments=comments)
    else:
        flash("You must login first!", "error")
        return redirect('/')

@app.route("/wall/post_message", methods=["POST"])
def post_message():
    if len(request.form['message']) > 0:
        query = "INSERT INTO messages(message, created_at, updated_at, user_id) VALUES(:message, NOW(), NOW(), "+str(session['uid'])+")"
        mysql.query_db(query, request.form)
        return redirect('/wall')
    else:
        flash("Message cannot be empty!", "error")
        return redirect('/wall')

@app.route("/wall/post_message")
def wall_post_message_redirect():
    return redirect('/wall') 

@app.route("/wall/post_comment", methods=["POST"])
def post_comment():
    if len(request.form['comment']) > 0:
        query = "INSERT INTO comments(comment, created_at, updated_at, message_id, user_id) VALUES(:comment, NOW(), NOW(), :message_id, "+str(session['uid'])+")"
        mysql.query_db(query, request.form)
        return redirect('/wall')
    else:
        flash("Comment cannot be empty!", "error")
        return redirect('/wall')

@app.route("/wall/post_comment")
def wall_comment_redirect():
    return redirect('/wall') 

@app.route("/wall/delete_message", methods=["POST"])
def wall_delete_message():
    query = "DELETE FROM comments WHERE message_id="+request.form['id']
    mysql.query_db(query)
    query = "DELETE FROM messages WHERE id="+request.form['id']
    mysql.query_db(query)
    return redirect('/wall')   

@app.route("/wall/delete_message")
def wall_delete_message_redirect():
    return redirect('/wall')

@app.route("/wall/delete_comment", methods=["POST"])
def wall_delete_comment():
    query = "DELETE FROM comments WHERE id="+request.form['id']
    mysql.query_db(query)
    return redirect('/wall')   

@app.route("/wall/delete_comment")
def wall_delete_comment_redirect():
    return redirect('/wall')    

@app.route("/logout")
def logout():
    session.clear()
    return redirect('/')

@app.route("/email/<email>")
def email(email):
    query = "SELECT password FROM users WHERE email = '"+email+"'"
    user = mysql.query_db(query)
    password = "That email didn't exist!"
    if len(user) > 0:
        password = user[0]['password']
    return render_template('email.html', email=email, password=password)

@app.route("/change_password", methods=["POST"])
def change_password():
    error = False
    if len(request.form['password']) < 1:
        flash("Password cannot be empty!", "error")
        error = True
    elif len(request.form['password']) < 8:
        flash("Password must be longer than 8 characters", "error")
        error = True
    if request.form['password'] != request.form['confirm_password']:
        flash("Passwords don't match!", "error")
        error = True
    if not error:
        myIDquery = "SELECT id from users WHERE email='"+request.form['email']+"'"
        myID = mysql.query_db(myIDquery)
        password = bcrypt.hashpw(request.form['password'].encode(), bcrypt.gensalt())
        query = "UPDATE users SET password=:password WHERE id=:id"
        data = {'password':password, 'id':myID[0]['id']}
        mysql.query_db(query, data)
        flash("Updated your password", "success")
        return redirect('/')
    return redirect('/email/'+request.form['email'])

app.run(debug=True)