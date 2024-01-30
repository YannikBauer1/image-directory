# Imports
from __future__ import print_function
from google.cloud import storage
from google.cloud import bigquery
from google.cloud import vision
from google.oauth2 import service_account
import tfmodel
import os
import logging
import flask
import warnings


warnings.filterwarnings("ignore", category=FutureWarning)


# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

PROJECT = os.environ.get('GOOGLE_CLOUD_PROJECT')
logging.info('Google Cloud project is {}'.format(PROJECT))

# Initialisation
logging.info('Initialising app')
app = flask.Flask(__name__)

logging.info('Initialising BigQuery client')
BQ_CLIENT = bigquery.Client()


BUCKET_NAME = PROJECT + '.appspot.com'
logging.info('Initialising access to storage bucket {}'.format(BUCKET_NAME))
APP_BUCKET = storage.Client().bucket(BUCKET_NAME)


logging.info('Initialising TensorFlow classifier')
TF_CLASSIFIER = tfmodel.Model(
    app.root_path + "/static/tflite/model.tflite",
    app.root_path + "/static/tflite/dict.txt"
)
logging.info('Initialisation complete')



# End-point implementation.

@app.route('/')
def index():
    return flask.render_template('index.html')


@app.route('/classes')
def classes():
    results = BQ_CLIENT.query(
        '''
        Select Description, COUNT(*) AS NumImages
        FROM `bdccproject01.openimages.image_labels`
        JOIN `bdccproject01.openimages.classes` USING(Label)
        GROUP BY Description
        ORDER BY Description
    ''').result()
    logging.info('classes: results={}'.format(results.total_rows))
    data = dict(results=results)
    return flask.render_template('classes.html', data=data)


@app.route('/relations')
def relations():
    results = BQ_CLIENT.query(
        '''
        Select Relation, COUNT(*) AS NumRelations
        FROM `bdccproject01.openimages.relations`
        GROUP BY Relation
        ORDER BY Relation
    ''').result()
    logging.info('relations: results={}'.format(results.total_rows))
    data = dict(results=results)
    return flask.render_template('relations.html', data=data)


@app.route('/image_info')
def image_info():
    image_id = flask.request.args.get('image_id')
    imageLabelsResults = BQ_CLIENT.query(
        '''
        SELECT ARRAY_AGG(Description ORDER BY Description) AS ImageDescriptions
        FROM bdccproject01.openimages.image_labels 
        JOIN bdccproject01.openimages.classes USING(Label)
        WHERE ImageId = '{0}'
    '''.format(image_id)
    ).result()
    logging.info('image_info: image_id={}, imageLabelsResults={}'.format(
        image_id, imageLabelsResults.total_rows))
    relationsResults = BQ_CLIENT.query(
        '''
        SELECT ARRAY_AGG(Description1) AS fisrtLabel,ARRAY_AGG(Relation) AS possibleRelations,
        ARRAY_AGG(Description) AS Description2
        FROM(
            SELECT ImageId, Description AS Description1, Label1, Relation, Label2
            FROM bdccproject01.openimages.relations 
            JOIN bdccproject01.openimages.classes  ON Label = Label1
            )
        JOIN bdccproject01.openimages.classes ON Label = Label2
        WHERE ImageId = '{0}'
    '''.format(image_id)
    ).result()
    logging.info('image_info: image_id={}, relationsResults={}'.format(
        image_id, relationsResults.total_rows))

    data = dict(
        image_id=image_id,
        imageLabelsResults=imageLabelsResults,
        relationsResults=relationsResults
    )

    return flask.render_template('image_info.html', data=data)


@app.route('/image_search')
def image_search():
    description = flask.request.args.get('description')
    image_limit = flask.request.args.get('image_limit', default=10, type=int)
    results = BQ_CLIENT.query(
        '''
        SELECT ImageId
        FROM `bdccproject01.openimages.image_labels`
        JOIN `bdccproject01.openimages.classes` USING(Label)
        WHERE Description = '{0}' 
        ORDER BY ImageId
        LIMIT {1}  
    '''.format(description, image_limit)
    ).result()
    logging.info('image_search: description={} limit={}, results={}'
                 .format(description, image_limit, results.total_rows))
    data = dict(description=description,
                image_limit=image_limit,
                results=results)
    return flask.render_template('image_search.html', data=data)


@app.route('/image_search_multiple')
def image_search_multiple():
    descriptions = flask.request.args.get('descriptions').split(',')
    image_limit = flask.request.args.get('image_limit', default=10, type=int)
    results = BQ_CLIENT.query(
        '''
        SELECT ImageId, ARRAY_AGG(Description) as GroupedDescriptions
        FROM `bdccproject01.openimages.image_labels`
        JOIN `bdccproject01.openimages.classes` USING(Label)
        WHERE Description IN UNNEST({0})
        GROUP BY ImageId
        HAVING COUNT(Description) >= 1
        ORDER BY COUNT(Description) DESC, ImageId
        LIMIT {1}  
    '''.format(descriptions, image_limit)
    ).result()

    logging.info('image_search: descriptions={} limit={}, results={}'
                 .format(descriptions, image_limit, results.total_rows))
    data = dict(descriptions=descriptions,
                image_limit=image_limit,
                results=results)
    return flask.render_template('image_search_multiple.html', data=data)


@app.route('/relation_search')
def relation_search():
    class1 = flask.request.args.get('class1', default='%')
    relation = flask.request.args.get('relation', default='%')
    class2 = flask.request.args.get('class2', default='%')
    image_limit = flask.request.args.get('image_limit', default=10, type=int)
    results = BQ_CLIENT.query(
        '''
        SELECT ImageId
        FROM(
            SELECT ImageId, Description, Relation, Label2
            FROM `bdccproject01.openimages.relations`
            JOIN `bdccproject01.openimages.classes` ON Label = Label1
            WHERE Description LIKE '{0}' AND Relation LIKE '{2}'
            )
        JOIN bdccproject01.openimages.classes ON Label = Label2
        WHERE classes.Description LIKE '{1}'
        ORDER BY ImageId
        LIMIT {3}  
    '''.format(class1, class2, relation, image_limit)
    ).result()
    logging.info('relation_search: class1={}, relation={}, class2={}, limit={}, results={}'
                 .format(class1, relation, class2, image_limit, results.total_rows))
    data = dict(class1=class1,
                relation=relation,
                class2=class2,
                image_limit=image_limit,
                results=results)
    return flask.render_template('relations_search.html', data=data)


@app.route('/image_classify_classes')
def image_classify_classes():
    with open(app.root_path + "/static/tflite/dict.txt", 'r') as f:
        data = dict(results=sorted(list(f)))
        return flask.render_template('image_classify_classes.html', data=data)


@app.route('/image_classify', methods=['POST'])
def image_classify():
    files = flask.request.files.getlist('files')
    min_confidence = flask.request.form.get(
        'min_confidence', default=0.25, type=float)
    results = []
    if len(files) > 1 or files[0].filename != '':
        for file in files:
            classifications = TF_CLASSIFIER.classify(file, min_confidence)
            blob = storage.Blob(file.filename, APP_BUCKET)
            blob.upload_from_file(file, blob, content_type=file.mimetype)
            blob.make_public()
            logging.info('image_classify: filename={} blob={} classifications={}'
                         .format(file.filename, blob.name, classifications))
            results.append(dict(bucket=APP_BUCKET,
                                filename=file.filename,
                                classifications=classifications))

    data = dict(bucket_name=APP_BUCKET.name,
                min_confidence=min_confidence,
                results=results)
    return flask.render_template('image_classify.html', data=data)


@app.route('/image_multiple_labels', methods=['POST'])
def image_multiple_labels():
    files = flask.request.files.getlist('files')
    credentials = service_account.Credentials.from_service_account_file('app/key.json')
    
    to_show = []

    if len(files) > 1 or files[0].filename != '':
        for file in files:
            blob = storage.Blob(file.filename, APP_BUCKET)
            blob.upload_from_file(file, blob, content_type=file.mimetype)
            blob.make_public()
            logging.info('image_multiple_labels: filename={} blob={}'
                         .format(file.filename, blob.name))
            
            image_uri = 'gs://bdccproject01.appspot.com/' + file.filename

            client = vision.ImageAnnotatorClient(credentials=credentials)
            image = vision.Image()
            image.source.image_uri = image_uri

            response = client.label_detection(image=image)  # pylint: disable=no-member
            results = []
            results.append(dict(bucket=APP_BUCKET,
                                    filename=file.filename))
            
            for label in response.label_annotations:
                results.append((label.description,label.score*100)) 
                
            to_show.append(results)
        
    data = dict(bucket_name=APP_BUCKET.name,
                results=to_show)
    
    return flask.render_template('image_multiple_labels.html', data = data)


if __name__ == '__main__':
    # When invoked as a program.
    logging.info('Starting app')
    app.run(host='0.0.0.0', port=8080, debug=True)


