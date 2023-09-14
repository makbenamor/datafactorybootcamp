# Databricks notebook source
#set up the cluster to be able to access the json file

# Configuration values
storage_account_name = "dlmamorbootcamp2023"
container_name = "dl-raw"
relative_path = "xcc-de-assessment/events.json"  
sas_token = "?sp=racwdlmeop&st=2023-09-14T10:07:10Z&se=2023-09-14T18:07:10Z&spr=https&sv=2022-11-02&sr=c&sig=ZQYjmc2gqqAhCfbo0F1Szn3jvcBkbmmfAANPduh5elE%3D" # I created a public endpoint to the ADLS container

# Full source path
source_path = f"wasbs://{container_name}@{storage_account_name}.blob.core.windows.net/{relative_path}{sas_token}"


# Mount point in Databricks' file system
mount_point = "/mnt/xcc-de-assessment"

# Mount the blob storage to Databricks
configs = {
    f"fs.azure.sas.{container_name}.{storage_account_name}.blob.core.windows.net": sas_token.lstrip("?")
}

dbutils.fs.mount(
    source=source_path,
    mount_point=mount_point,
    extra_configs=configs
)


# COMMAND ----------

dbutils.fs.ls("/mnt/xcc-de-assessment/")


# COMMAND ----------

dbutils.notebook.exit("Success")
