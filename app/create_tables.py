from google.cloud import bigquery
import pandas as pd 
import time


BQ_CLIENT = bigquery.Client(project='bdccproject01')

dataset_id = "{}.openimages".format(BQ_CLIENT.project)

dataset = bigquery.Dataset(dataset_id)
dataset.location = "US"

dataset = BQ_CLIENT.create_dataset(dataset, timeout=30)  # Makes an API request.
#print("Created dataset {}.{}".format(BQ_CLIENT.project, dataset.dataset_id))




# Creating image_labels table:

table_image_labels = 'bdccproject01.openimages.image_labels'
print('Creating table ' + table_image_labels)

# Delete the table in case you're running this for the second time
#BQ_CLIENT.delete_table(table_image_labels, not_found_ok=True)

# Create the table
# - we use the same field names as in the original data set

table1 = bigquery.Table(table_image_labels)
table1.schema = (
        bigquery.SchemaField('ImageId',      'STRING'),
        bigquery.SchemaField('Label',      'STRING')
)
BQ_CLIENT.create_table(table1)


# Creating classes table:

table_classes = 'bdccproject01.openimages.classes'
print('Creating table ' + table_classes)

# Delete the table in case you're running this for the second time
#BQ_CLIENT.delete_table(table_classes, not_found_ok=True)

# Create the table
# - we use the same field names as in the original data set

table2 = bigquery.Table(table_classes)
table2.schema = (
        bigquery.SchemaField('Label',      'STRING'),
        bigquery.SchemaField('Description',      'STRING')

)
BQ_CLIENT.create_table(table2)



# Creating relations table:

table_relations = 'bdccproject01.openimages.relations'
print('Creating table ' + table_relations)

# Delete the table in case you're running this for the second time
#BQ_CLIENT.delete_table(table_relations, not_found_ok=True)

# Create the table
# - we use the same field names as in the original data set

table3 = bigquery.Table(table_relations)
table3.schema = (
        bigquery.SchemaField('ImageId',      'STRING'),
        bigquery.SchemaField('Label1',      'STRING'),
        bigquery.SchemaField('Relation',      'STRING'),
        bigquery.SchemaField('Label2',      'STRING')
)
BQ_CLIENT.create_table(table3)




# Populate table image_labels

image_labels = pd.read_csv("image-labels.csv")

print('Loading data into ' + table_image_labels)
load_job = BQ_CLIENT.load_table_from_dataframe(image_labels, table1)

while load_job.running():
  print('waiting for the load job to complete')
  time.sleep(1)

if load_job.errors == None:
  print('Load complete!')
else:
  print(load_job.errors)



# Populate table classes

classes = pd.read_csv("classes.csv")

print('Loading data into ' + table_classes)
load_job = BQ_CLIENT.load_table_from_dataframe(classes, table2)

while load_job.running():
  print('waiting for the load job to complete')
  time.sleep(1)

if load_job.errors == None:
  print('Load complete!')
else:
  print(load_job.errors)


# Populate table relations

relations = pd.read_csv("relations.csv")

print('Loading data into ' + table_relations)
load_job = BQ_CLIENT.load_table_from_dataframe(relations, table3)

while load_job.running():
  print('waiting for the load job to complete')
  time.sleep(1)

if load_job.errors == None:
  print('Load complete!')
else:
  print(load_job.errors)
