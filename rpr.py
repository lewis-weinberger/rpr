"""
rpr: ranked preferences resolver

The user participates as follows:
1) Provides a (unique) username
2) Inputs their desired list of options
3) Ranks from the list of all options provided by users
4) Views final ranking based on aggregate of users' preferences
"""

import os
import json
import re
from flask import (
    Flask, flash, redirect, render_template, request, session, url_for
)
from flask_caching import Cache
from wtforms import Form, FieldList, StringField, validators

app = Flask(__name__)
cache = Cache(config={
    "CACHE_TYPE": "FileSystemCache",
    "CACHE_DIR": "rprcache",
    "CACHE_DEFAULT_TIMEOUT": 3600
})

class LoginForm(Form):
    """Form for users to provide their username"""
    user = StringField("User", [validators.InputRequired()])

    def __repr__(self):
        return self.__class__.__name__

    def user_exists(self, users):
        """Check if username is already in use"""
        return self.user.data in users

class InputForm(Form):
    """Form for users to input their options"""
    choices = FieldList(
        StringField("", [validators.InputRequired()]), min_entries=5
    )

    def __repr__(self):
        return self.__class__.__name__

    def normalise(self, thes):
        """Normalise inputs based on given thesaurus"""
        new_choices = set()
        for field in self.choices:
            choice = field.data
            for (regex, value) in thes:
                if regex.match(choice) is not None:
                    choice = value
            new_choices.add(choice)
        return list(new_choices)

@app.route("/", methods=["GET", "POST"])
def index():
    """Main landing page where users login"""
    if "user" in session:
        return redirect(url_for("options"))
    form = LoginForm(request.form)
    users = cache.get("users")
    if request.method == "POST" and form.validate():
        if not form.user_exists(users):
            session["user"] = request.form["user"]
            users[session["user"]] = []
            cache.set("users", users)
            return redirect(url_for("options"))
        flash("Username already in use!")
    return render_template("index.html", form=form, users=users)

@app.route("/options", methods=["GET", "POST"])
def options():
    """Page where users input their options"""
    if "user" not in session:
        return redirect(url_for("index"))
    form = InputForm(request.form)
    users = cache.get("users")
    if "options" not in session:
        if request.method == "POST" and form.validate():
            thes = cache.get("thesaurus")
            choices = form.normalise(thes)
            session["options"] = choices
            users[session["user"]] = choices
            cache.set("users", users)
            return redirect(url_for("options"))
    return render_template("options.html", form=form, users=users)

@app.route("/ready_users")
def ready_users():
    """List users that are ready, having entered their options"""
    users = cache.get("users")
    return render_template("ready_users.html", users=users)

def amalgamate():
    """Combine user options into single list"""
    all_options = cache.get("all_options")
    if all_options is None:
        all_options = set()
        for choices in cache.get("users").values():
            for option in choices:
                all_options.add(option)
        all_options = list(all_options)
        cache.set("all_options", all_options)
    return all_options

@app.route("/rank", methods=["GET", "POST"])
def rank():
    """Page where users specify their preferences"""
    if "user" not in session:
        return redirect(url_for("index"))
    if "options" not in session:
        return redirect(url_for("options"))
    if "all" not in session:
        session["all"] = amalgamate()
    if "rankings" not in session:
        session["rankings"] = list(range(len(session["all"])))
    if request.method == "POST":
        data = [int(x) for x in request.json.replace("item[]=", "").split("&")]
        session["rankings"] = data
    return render_template("rank.html", all_options=session["all"])

@app.route("/results")
def results():
    """Results page where aggregate rankings are shown"""
    if "user" not in session:
        return redirect(url_for("index"))
    if "rankings" not in session:
        return redirect(url_for("rank"))
    return render_template("results.html", finished=[], final=[])

def aggregate(finished, all_options):
    """Determine current rankings submitted by users so far"""
    inds = {k: 0 for k in range(len(all_options))}
    for vals in finished.values():
        for i, val in enumerate(vals):
            inds[val] += i
    return [all_options[i] for i in sorted(inds, key=inds.get)]

@app.route("/current_results")
def current_results():
    """Determine current rankings submitted by users so far"""
    finished = cache.get("finished")
    if finished is None:
        finished = {session["user"]: session["rankings"]}
    if session["user"] not in finished:
        finished[session["user"]] = session["rankings"]
    cache.set("finished", finished)
    final = aggregate(finished, session["all"])
    return render_template("current_results.html", finished=finished, final=final)

if __name__ == "__main__":
    thesaurus = []
    try:
        with open("thesaurus.json", encoding="utf-8") as f:
            for k, v in json.load(f).items():
                thesaurus.append((re.compile(k, re.IGNORECASE), v))
    except:
        print("Valid thesaurus.json not found")
    app.config["SECRET_KEY"] = os.urandom(12).hex()
    cache.init_app(app)
    cache.clear()
    cache.set("thesaurus", thesaurus)
    cache.set("users", {})
    app.run(port=5000)
