# coding=utf8
import mysql.connector
import xml.etree.ElementTree as ET
from datetime import date
from functools import wraps

import module as m
import requests
import updateModules
from flask import Flask, jsonify, request, abort
from flask_cors import CORS, cross_origin

app = Flask(__name__, static_url_path='/static')
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
app.config['SECRET_KEY'] = '<secret_key>'
db_config = {
    'user': '<db_user>',
    'password': '<db_password>',
    'host': '127.0.0.1',
    'database': '<db_name>',
}


# decorator for checking the api-key
def require_appkey(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        if request.args.get('key') and request.args.get('key') == app.config['SECRET_KEY']:
            return view_function(*args, **kwargs)
        else:
            abort(401)

    return decorated_function


# Hello World
@app.route('/hello')
@cross_origin()
@require_appkey
def hello_world():
    return jsonify(hell0='world'), 200


# Information about the API
@app.route('/')
@cross_origin()
def info():
    return 'This is a small scale API to access and manipulate data about Sustainability-related Modules at the University of Zurich'


# serve public js-file
@app.route('/js/public')
@cross_origin()
def get_public_js():
    return app.send_static_file('public.js')


# serve admin js-file
@app.route('/js/admin', methods=['GET'])
@cross_origin()
def get_admin_js():
    return app.send_static_file('admin.js')


# serve jquery-ui css-file
@app.route('/css/jqueryui', methods=['GET'])
@cross_origin()
def get_jquery_css():
    return app.send_static_file('jquery-ui.min.css')


# serve jquery-ui js-file
@app.route('/js/jqueryui', methods=['GET'])
@cross_origin()
def get_jquery_js():
    return app.send_static_file('jquery-ui.min.js')


# update all modules
@app.route('/update')
@cross_origin()
def update():
    if updateModules.update_db():
        return 'modules updated', 200
    else:
        return 'error', 400


# get whitelist
@app.route('/whitelist', methods=['GET'])
@cross_origin()
def get_whitelist():
    modules = []
    cnx = mysql.connector.connect(**db_config)
    cursor = cnx.cursor(dictionary=True)
    qry = (
        "SELECT SmObjId, PiqYear, PiqSession, title, held_in FROM whitelist WHERE SmObjId NOT IN(SELECT SmObjId FROM blacklist) AND PiqYear != 0 ORDER BY title ASC")
    cursor.execute(qry)
    for module in cursor:
        for column, value in module.iteritems():
            if type(value) is bytearray:
                module[column] = value.decode('utf-8')
        modules.append(module)
    cnx.close()
    return jsonify(modules)


# add module to whitelist and remove it from blacklist
@app.route('/whitelist/<int:module_id>', methods=['POST'])
@cross_origin()
@require_appkey
def add_whitelist(module_id):
    cnx = mysql.connector.connect(**db_config)
    qry = "INSERT IGNORE INTO whitelist (SmObjId, PiqYear, PiqSession, title, held_in) VALUES (%(SmObjId)s, %(PiqYear)s, %(PiqSession)s, %(title)s, %(held_in)s)"
    qry2 = "DELETE FROM blacklist WHERE SmObjId = %(SmObjId)s"
    module = m.Module(module_id)
    module.update()
    val = module.get_module()
    if val:
        try:
            cursor = cnx.cursor()
            cursor.execute(qry2, val)
            cnx.commit()
            cursor.close()
        except mysql.connector.Error as err:
            pass
        try:
            cursor = cnx.cursor()
            cursor.execute(qry, val)
            cnx.commit()
            cursor.close()
            cnx.close()
            return jsonify(val), 200
        except mysql.connector.Error as err:
            return "Error: {}".format(err), 409
    else:
        return 'No module found', 404


# remove module from whitelist and add to blacklist
@app.route('/whitelist/<int:module_id>', methods=['DELETE'])
@cross_origin()
@require_appkey
def remove_whitelist(module_id):
    cnx = mysql.connector.connect(**db_config)

    # read module from whitelist
    try:
        val = {'SmObjId': module_id}
        sel = "SELECT * FROM whitelist WHERE SmObjId = %(SmObjId)s"
        cursor = cnx.cursor(dictionary=True, buffered=True)
        cursor.execute(sel, val)
        if cursor.rowcount > 0:
            val = cursor.fetchone()
            for column, value in val.iteritems():
                if type(value) is bytearray:
                    val[column] = value.decode('utf-8')
        else:
            return 'There is no module to delete', 404
    except mysql.connector.Error as err:
        return "Error: {}".format(err), 500

    # remove module from whitelist
    try:
        qry = "DELETE FROM whitelist WHERE SmObjId = %(SmObjId)s"
        cursor.execute(qry, val)
    except mysql.connector.Error as err:
        return "Error: {}".format(err), 500

    # add module to blacklist
    try:
        qry = "INSERT IGNORE INTO blacklist (SmObjId, PiqYear, PiqSession, title, held_in) VALUES (%(SmObjId)s, %(PiqYear)s, %(PiqSession)s, %(title)s, %(held_in)s)"
        cursor.execute(qry, val)
    except mysql.connector.Error as err:
        return "Error: {}".format(err), 500

    cnx.commit()
    cursor.close()
    cnx.close()
    return 'Deleted and moved module to blacklist', 200


# get blacklist
@app.route('/blacklist', methods=['GET'])
@cross_origin()
def get_blacklist():
    modules = []
    cnx = mysql.connector.connect(**db_config)
    cursor = cnx.cursor(dictionary=True)
    qry = (
        "SELECT SmObjId, PiqYear, PiqSession, title, held_in FROM blacklist WHERE PiqYear != 0 ORDER BY title ASC")
    cursor.execute(qry)
    for module in cursor:
        for column, value in module.iteritems():
            if type(value) is bytearray:
                module[column] = value.decode('utf-8')
        modules.append(module)
    return jsonify(modules)


# add module to blacklist and remove it from whitelist
@app.route('/blacklist/<int:module_id>', methods=['POST'])
@cross_origin()
@require_appkey
def add_blacklist(module_id):
    cnx = mysql.connector.connect(**db_config)
    qry = "INSERT IGNORE INTO blacklist (SmObjId, PiqYear, PiqSession, title, held_in) VALUES (%(SmObjId)s, %(PiqYear)s, %(PiqSession)s, %(title)s, %(held_in)s)"
    qry2 = "DELETE FROM whitelist WHERE SmObjId = %(SmObjId)s"
    module = m.Module(module_id)
    module.update()
    val = module.get_module()
    if val:
        try:
            cursor = cnx.cursor()
            cursor.execute(qry2, val)
            cnx.commit()
            cursor.close()
        except mysql.connector.Error as err:
            pass

        try:
            cursor = cnx.cursor()
            cursor.execute(qry, val)
            cnx.commit()
            cursor.close()
            cnx.close()
            return jsonify(val), 200
        except mysql.connector.Error as err:
            return "Error: {}".format(err), 409
    else:
        return 'No Module found', 404


# remove module from blacklist
@app.route('/blacklist/<int:module_id>', methods=['DELETE'])
@cross_origin()
@require_appkey
def remove_blacklist(module_id):
    cnx = mysql.connector.connect(**db_config)

    # read module from blacklist
    try:
        val = {'SmObjId': module_id}
        sel = "SELECT * FROM blacklist WHERE SmObjId = %(SmObjId)s"
        cursor = cnx.cursor(dictionary=True, buffered=True)
        cursor.execute(sel, val)
        if cursor.rowcount > 0:
            val = cursor.fetchone()
            for column, value in val.iteritems():
                if type(value) is bytearray:
                    val[column] = value.decode('utf-8')
        else:
            return 'There is no module to delete', 404
    except mysql.connector.Error as err:
        return "Error: {}".format(err), 500

    # remove module from whitelist
    try:
        qry = "DELETE FROM blacklist WHERE SmObjId = %(SmObjId)s"
        cursor.execute(qry, val)
    except mysql.connector.Error as err:
        return "Error: {}".format(err), 500

    cnx.commit()
    cursor.close()
    cnx.close()
    return 'Deleted module from blacklist', 200


# get all search terms
@app.route('/searchterm', methods=['GET'])
@cross_origin()
def get_searchterms():
    terms = []
    cnx = mysql.connector.connect(**db_config)
    cursor = cnx.cursor(dictionary=True)
    qry = (
        "SELECT id, term FROM searchterm ORDER BY term ASC")
    cursor.execute(qry)
    for row in cursor.fetchall():
        for column, value in row.iteritems():
            if type(value) is bytearray:
                row[column] = value.decode('utf-8')
        terms.append(row)
    return jsonify(terms)


# add search term
@app.route('/searchterm', methods=['POST'])
@cross_origin()
@require_appkey
def add_searchterm():
    cnx = mysql.connector.connect(**db_config)
    cursor = cnx.cursor()
    data = request.form
    term = data['term']
    # term  =  'test'
    qry = "INSERT INTO searchterm (term) VALUES (%(term)s)"
    try:
        cursor.execute(qry, data)
        id = cursor.lastrowid
        cnx.commit()
        cnx.close()
        return jsonify({'id': id, 'term': term}), 200
    except mysql.connector.Error as err:
        cnx.close()
        return "Error: {}".format(err), 400


# remove search term
@app.route('/searchterm/<int:id>', methods=['DELETE'])
@cross_origin()
@require_appkey
def remove_searchterm(id):
    cnx = mysql.connector.connect(**db_config)
    cursor = cnx.cursor()
    qry = "DELETE FROM searchterm WHERE id= %(id)s"
    try:
        cursor.execute(qry, {'id': id})
        cnx.commit()
        cnx.close()
        return 'deleted', 200
    except mysql.connector.Error as err:
        cnx.close()
        return "Error: {}".format(err), 404


# get modules based on search terms, excluding those on white- and blacklist
@app.route('/search', methods=['GET'])
@cross_origin()
def search():
    # get searchterms
    terms = []
    cnx = mysql.connector.connect(**db_config)
    cursor = cnx.cursor(dictionary=True)
    qry = (
        "SELECT term FROM searchterm")
    cursor.execute(qry)
    for row in cursor:
        terms.append(row['term'])

    # get results for all searchterms
    modules = []
    for session in [next_session(), current_session(), previous_session()]:
        for searchterm in terms:
            rURI = "https://studentservices.uzh.ch/sap/opu/odata/uzh/vvz_data_srv/SmSearchSet?$skip=0&$top=20&$orderby=SmStext%20asc&$filter=substringof('{0}',Seark)%20and%20PiqYear%20eq%20'{1}'%20and%20PiqSession%20eq%20'{2}'&$inlinecount=allpages".format(
                searchterm, session['year'], session['session'])
            r = requests.get(rURI)
            root = ET.fromstring(r.content)
            for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
                for a in entry.findall('{http://www.w3.org/2005/Atom}content'):
                    modules.append({
                        'SmObjId': a[0].find('{http://schemas.microsoft.com/ado/2007/08/dataservices}Objid').text,
                        'PiqYear': a[0].find('{http://schemas.microsoft.com/ado/2007/08/dataservices}PiqYear').text,
                        'PiqSession': a[0].find(
                            '{http://schemas.microsoft.com/ado/2007/08/dataservices}PiqSession').text,
                        'title': a[0].find('{http://schemas.microsoft.com/ado/2007/08/dataservices}SmStext').text
                    })

    # remove duplicates
    modules = [dict(t) for t in set([tuple(d.items()) for d in modules])]

    # remove elements that are on blacklist
    blacklist = []
    cursor = cnx.cursor()
    qry = (
        "SELECT SmObjId FROM blacklist")
    cursor.execute(qry)
    for row in cursor:
        blacklist.append(row[0])

    for mod in modules:
        if mod['SmObjId'] in blacklist:
            modules.pop(mod)
    cursor.close()

    # remove elements that are already on whitelist
    whitelist = []
    cursor = cnx.cursor()
    qry = (
        "SELECT SmObjId FROM whitelist WHERE SmObjId NOT IN(SELECT SmObjId FROM blacklist) AND PiqYear != 0 ORDER BY title ASC")
    cursor.execute(qry)
    for row in cursor:
        whitelist.append(row[0])

    for mod in modules:
        if mod['SmObjId'] in whitelist:
            modules.pop(mod)
    cursor.close()

    return jsonify(modules)


def current_session():
    if date.today() < date(date.today().year, 2, 1):
        return {'year': current_year() - 1, 'session': '003'}
    elif date.today() < date(date.today().year, 8, 1):
        return {'year': current_year() - 1, 'session': '004'}
    else:
        return {'year': current_year(), 'session': '003'}


def next_session():
    if date.today() < date(date.today().year, 2, 1):
        return {'year': current_year() - 1, 'session': '004'}
    elif date.today() < date(date.today().year, 8, 1):
        return {'year': current_year(), 'session': '003'}
    else:
        return {'year': current_year(), 'session': '004'}


def previous_session():
    if date.today() < date(date.today().year, 2, 1):
        return {'year': current_year() - 2, 'session': '004'}
    elif date.today() < date(date.today().year, 8, 1):
        return {'year': current_year() - 1, 'session': '003'}
    else:
        return {'year': current_year() - 1, 'session': '004'}


def current_year():
    return date.today().year


if __name__ == "__main__":
    app.run()
