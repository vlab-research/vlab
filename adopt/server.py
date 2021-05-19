from environs import Env
from flask import Flask, jsonify, request
from flask_cors import CORS

from .campaign_queries import (create_campaign_confs, create_campaign_for_user,
                               get_campaign_configs, get_campaigns_for_user)

app = Flask(__name__)
CORS(app)

env = Env()

db_conf = {
    "db": env("CHATBASE_DATABASE"),
    "user": env("CHATBASE_USER"),
    "host": env("CHATBASE_HOST"),
    "port": env("CHATBASE_PORT"),
    "password": env("CHATBASE_PASSWORD", None),
}


@app.route("/campaigns", methods=["GET"])
def get_campaigns():
    email = request.args.get("email")
    if email:
        res = get_campaigns_for_user(email, db_conf)
        return jsonify(res), 200
    else:
        # get all active campaigns???
        pass


@app.route("/campaigns", methods=["POST"])
def create_campaign():
    email = request.args.get("email")
    name = request.args.get("name")
    res = create_campaign_for_user(email, name, db_conf)
    return res, 201


@app.route("/campaigns/:campaignid/confs/:conf_type", methods=["POST"])
def create_conf(campaignid, conf_type):
    dat = request.json
    create_campaign_confs(campaignid, conf_type, dat, db_conf)
    return "OK", 200


@app.route("/campaigns/:campaignid/confs", methods=["GET"])
def get_confs(campaignid):
    res = get_campaign_configs(campaignid, db_conf)
    return jsonify(res), 200


def create_image():
    fi = request.files.get("file")

    if fi and allowed_file(fi.filename):
        b = fi.read()
        s = base64.b64encode(b).decode()

        # make image in facebook api with those bytes
        # ...
        # store in database and do this elsewhere???

        # state.account.create_ad_image(params = {AdImage.Field.bytes: s, AdImage.Field.name: 'vlab-mnm-test'})
    else:
        return "poop", 400
