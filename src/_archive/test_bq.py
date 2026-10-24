from google.cloud import bigquery
print("Initializing BigQuery client...")
client = bigquery.Client(project="careflow-analytics-98234")
print("Client initialized successfully! Listing datasets...")
datasets = list(client.list_datasets())
print("Datasets found:", [d.dataset_id for d in datasets])
