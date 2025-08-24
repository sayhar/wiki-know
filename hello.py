from flask import Flask
from flask import url_for as local_url_for
from flask import render_template
import logging

# Make S3 optional for local development
try:
    from flask_s3 import FlaskS3

    S3_AVAILABLE = True
except ImportError:
    S3_AVAILABLE = False
    FlaskS3 = None

try:
    from flask_basicauth import BasicAuth

    BASIC_AUTH_AVAILABLE = True
except ImportError:
    BASIC_AUTH_AVAILABLE = False
    BasicAuth = None

import json
import app_functions
import app_helper

# NOTE!  We have a couple import statements lower down as well.


MODES = ["GUESS", "NOGUESS"]
logger = logging.getLogger(__name__)
logger.info("HELLO")


def setup(debug=False):
    app = Flask(__name__)
    app.jinja_env.globals.update(local_url_for=local_url_for)
    app.debug = debug
    return app


app = setup()

if not app.debug:
    import logging

    file_handler = logging.FileHandler("crash.log")
    file_handler.setLevel(logging.WARNING)
    app.logger.addHandler(file_handler)

    # Add console logging
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(formatter)
    app.logger.addHandler(console_handler)

    # Also configure the root logger for other modules
    logging.basicConfig(level=logging.INFO, handlers=[console_handler])

try:
    with open("config.json", "r") as config_file:
        config = json.load(config_file)
    app.config["FLASKS3_BUCKET_NAME"] = config.get("bucketname", "")
    app.config["BASIC_AUTH_USERNAME"] = config.get("basicauth_name", "")
    app.config["BASIC_AUTH_PASSWORD"] = config.get("basicauth_password", "")
    app.config["USE_S3_DEBUG"] = False
    app.config["INTERESTING_TESTS"] = config.get("interesting_tests", [])

    # Flask-S3 configuration
    if config.get("bucketname"):
        app.config["FLASKS3_ACTIVE"] = True
        app.config["FLASKS3_DEBUG"] = True
        app.config["FLASKS3_USE_HTTPS"] = True
        app.config["FLASKS3_BUCKET_DOMAIN"] = "s3.us-east-1.amazonaws.com"
    if "mode" in config:
        MODE = config["mode"]
    else:
        MODE = MODES[0]

    # Only set up auth if available
    if BASIC_AUTH_AVAILABLE:
        app.config["BASIC_AUTH_FORCE"] = True
        basic_auth = BasicAuth(app)
    else:
        logger.warning("Flask-BasicAuth not available, authentication disabled")

    # Only set up S3 if available
    if S3_AVAILABLE and config.get("bucketname"):
        s3 = FlaskS3(app)
    else:
        s3 = False
        logger.warning("Flask-S3 not available or no bucket configured, S3 disabled")

except Exception as e:
    logger.error(f"Config loading error: {e}")
    s3 = False
    MODE = MODES[0]


def is_s3():
    return s3


h = app_helper.AppHelper(app, s3)
f = app_functions.AppFunctions(app, h)


### The real stuff


@app.route("/")
def welcome():
    # print 'welcome'
    return render_template("welcome.html")


@app.route("/dir/", defaults={"batch": "reverse"})
@app.route("/dir/<batch>")
def go_dir(batch):
    if MODE in MODES:
        return f.show_dir(batch, MODE)
    else:
        return (
            render_template(
                "error.html",
                why="Sorry, but mode " + MODE + " doesn't exist.",
                title="404'd!",
            ),
            404,
        )


@app.errorhandler(404)
def page_not_found(e):
    return (
        render_template(
            "error.html",
            why="There's nothing here. Sorry! Your URL was probably mistyped etc.",
            title="404'd!",
        ),
        404,
    )


@app.route("/show/", defaults={"batch": "reverse", "testname": None})
@app.route("/show/<batch>/", defaults={"testname": None})
@app.route("/show/<batch>/<testname>")
def go_test(batch, testname):

    if testname == "error":
        return (
            render_template(
                "error.html",
                batch=batch,
                why="Ordering scheme: " + batch + " not found",
                title="Err...",
            ),
            404,
        )

    if testname is None:
        testname = h.first_test(batch)

    if testname.lower() == "random":
        testname = h.find_random_test(batch)

    if testname.lower() == "fin":
        return render_template("finished.html", batch=batch)

    if not h.test_in_batch(testname, batch):
        return (
            render_template(
                "error.html",
                why="Sorry, but this test doesn't exist in the "
                + batch
                + " ordering scheme",
                title="404'd!",
            ),
            404,
        )

    if MODE == "GUESS":
        return f.ask_guess(testname, batch)
    elif MODE == "NOGUESS":
        return f.show_noguess(testname, batch)
    else:
        return (
            render_template(
                "error.html",
                why="Sorry, but mode " + MODE + " doesn't exist.",
                title="404'd!",
            ),
            404,
        )


@app.route("/show/<batch>/<testname>/result/<path:guess>")
def go_result(batch, testname, guess):
    if not h.test_in_batch(testname, batch):
        return (
            render_template(
                "error.html",
                why="Sorry, but this test doesn't exist in the "
                + batch
                + " ordering scheme",
                title="404'd!",
            ),
            404,
        )

    if MODE == "GUESS":
        return f.result_guess(testname, batch, guess)
    elif MODE == "NOGUESS":
        return f.show_noguess(testname, batch)
    else:
        return (
            render_template(
                "error.html",
                why="Sorry, but mode " + MODE + " doesn't exist.",
                title="404'd!",
            ),
            404,
        )


if __name__ == "__main__":
    app.debug = True
    app.run(port=5001)
    # app.run()


# We call these functions:
# result_guess(testname, batch, guess)
# ask_guess(testname, batch)
# show_noguess(testname, batch)
# show_dir(batch, MODE)
