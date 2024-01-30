from google.cloud import bigquery
import flask

app = flask.Flask(__name__)
BQ_CLIENT = bigquery.Client()

with open(app.root_path + "/static/tflite/dict.txt", 'r') as f:
        classesList = list(f)
        print(classesList)
        curatedClassesList = []
        for item in classesList:
            curatedClassesList.append(item.replace('\n',''))
        data = dict(results=sorted(classesList))

def generateQuery(categoria):
    return '''
        SELECT ImageId, ARRAY_AGG(Description) AS ImageDescriptions
        FROM bdccproject01.openimages.image_labels 
        JOIN bdccproject01.openimages.classes USING(Label)
        WHERE Description in UNNEST (['{0}'])
        GROUP BY ImageId
        HAVING COUNT(Description) = 1
        LIMIT 100
    '''.format(categoria)

string = ''
string2 = ''

for item in curatedClassesList:
    results = BQ_CLIENT.query(
        generateQuery(item)
    ).result() 

    for count,result in enumerate(results):
        if count < 80:
            string2 += 'TRAIN,'+'gs://image_bucket_bdcc_1/'+result[0]+'.jpg,' + item+'\n'
            string += 'gs://bdcc_open_images_dataset/images/'+result[0]+'.jpg\n'
            
        if count >= 80 and count < 90:
            string2 += 'VALIDATION,'+'gs://image_bucket_bdcc_1/'+result[0]+'.jpg,' + item+'\n'
            string += 'gs://bdcc_open_images_dataset/images/'+result[0]+'.jpg\n'
            
        if count >= 90:
            string2 += 'TEST,'+'gs://image_bucket_bdcc_1/'+result[0]+'.jpg,' + item+'\n'
            string += 'gs://bdcc_open_images_dataset/images/'+result[0]+'.jpg\n'
            

with open(app.root_path + "/static/tflite/ImagesURIs.txt", 'w') as f:
    f.write(string)

with open(app.root_path + "/static/tflite/autoMLvision.csv", 'w') as f2:
    f2.write(string2)

