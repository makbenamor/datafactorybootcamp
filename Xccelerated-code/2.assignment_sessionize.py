# Databricks notebook source
# MAGIC %md 
# MAGIC #### Step 1: Setup
# MAGIC run the sutup notebook:

# COMMAND ----------

# MAGIC %md #### Step 2: Sessionize the Data using PySpark
# MAGIC 1.Load the data

# COMMAND ----------

df = spark.read.json("/mnt/xcc-de-assessment")
#display(df)


# COMMAND ----------

df.printSchema()

# COMMAND ----------

# MAGIC %md #### fixing the schema 

# COMMAND ----------

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window

spark = SparkSession.builder.appName("Sessionize").getOrCreate()

# Assuming you've already loaded your data into the DataFrame named `df`

# Threshold for session inactivity (e.g., 30 minutes)
SESSION_THRESHOLD = 30 * 60  # 30 minutes in seconds

# Step 1: Flatten the DataFrame

df_flattened = df.select(
    df["id"].alias("event_id"),
    df["type"].alias("event_type"),
    df["event"]["customer-id"].alias("customer_id"),
    df["event"]["ip"].alias("ip"),
    df["event"]["page"].alias("page"),
    df["event"]["position"].alias("position"),
    df["event"]["product"].alias("product"),
    df["event"]["query"].alias("query"),
    df["event"]["referrer"].alias("referrer"),
    df["event"]["timestamp"].alias("timestamp"),
    df["event"]["user-agent"].alias("user_agent")
)
#display(df_flattened)

# COMMAND ----------

# MAGIC %md #### filter the data 

# COMMAND ----------

# Step 2: Apply your filters
filtered_df = df_flattened.filter(df_flattened.customer_id.isNotNull())
#display(filtered_df)




# COMMAND ----------

# Step 3: Sessionize
# Create a window partitioned by customer and ordered by timestamp
window_spec = Window.partitionBy("customer_id").orderBy(F.unix_timestamp("timestamp"))

# Calculate the difference in seconds between the current and previous event timestamp for each user
time_diff = (F.unix_timestamp("timestamp") - F.lag(F.unix_timestamp("timestamp")).over(window_spec))

# If the time difference is greater than the threshold or if it's the first event (time_diff is null),
# start a new session; otherwise, continue the old session
filtered_df = filtered_df.withColumn("is_new_session", F.when(F.isnull(time_diff) | (time_diff > SESSION_THRESHOLD), 1).otherwise(0))

# Compute session ID for each event using a cumulative sum of the is_new_session column
filtered_df = filtered_df.withColumn("session_id", F.sum("is_new_session").over(window_spec))

#display(filtered_df)


# COMMAND ----------

# Local path on the Spark driver node
local_db_path = "/tmp/mydb.sqlite"
table_name = "eventstable"

# Write the DataFrame to SQLite on the local file system of the Spark driver
filtered_df.write.jdbc(
    url=f"jdbc:sqlite:{local_db_path}",
    table=table_name,
    mode="overwrite"
)

# Then, copy the SQLite file to DBFS if you want to persist it there
dbutils.fs.cp(f"file:{local_db_path}", "dbfs:/tmp/mydb.sqlite")


# COMMAND ----------

#preview the data in the SQLite table 
import sqlite3

# Connect to the SQLite database
conn = sqlite3.connect("/dbfs/tmp/mydb.sqlite")

# Fetch the data
query = "SELECT * FROM eventstable ;"
cursor = conn.cursor()
cursor.execute(query)
data = cursor.fetchall()

# Get column names and types from the cursor description
column_names = [desc[0] for desc in cursor.description]
column_types = [desc[1] for desc in cursor.description]  # This will give SQLite's type

# Close the connection
conn.close()



# COMMAND ----------

from pyspark.sql.types import StringType, IntegerType, DoubleType, StructType, StructField

type_mapping = {
    "TEXT": StringType(),
    "INTEGER": IntegerType(),
    "REAL": DoubleType(),
    # Add more if needed, based on the SQLite types you have in your dataset.
}

schema = StructType([StructField(name, type_mapping.get(typ, StringType())) for name, typ in zip(column_names, column_types)])

df_preview = spark.createDataFrame(data, schema)

#display(df_preview)

# COMMAND ----------

pip install Flask


# COMMAND ----------

from flask import Flask, jsonify
import sqlite3

app = Flask(__name__)

@app.route('/metrics/orders', methods=['GET'])
def get_metrics():
    conn = sqlite3.connect('/path_to_your_db.db')
    cursor = conn.cursor()
    
    cursor.execute("""WITH SessionWithOrder AS (
    SELECT customer_id,
           MIN(session_id) AS first_order_session_id
    FROM df_preview
    WHERE event_type = 'placed_order'
    GROUP BY customer_id
),
SessionsBeforeFirstOrder AS (
    SELECT d.customer_id,
           COUNT(DISTINCT d.session_id) AS sessions_before_order
    FROM df_preview d
    JOIN SessionWithOrder s ON d.customer_id = s.customer_id
    WHERE d.session_id < s.first_order_session_id
    GROUP BY d.customer_id
)
SELECT 
    PERCENTILE_CONT(0.5) WITHIN GROUP(ORDER BY sessions_before_order) AS median_sessions_before_order
FROM SessionsBeforeFirstOrder;
e""")
    median_sessions_before_order = cursor.fetchone()[0]
    
    cursor.execute("""WITH SessionDurations AS (
    SELECT customer_id,
           session_id,
           MAX(timestamp) - MIN(timestamp) AS session_duration_minutes
    FROM df_preview
    GROUP BY customer_id, session_id
),
SessionWithOrder AS (
    SELECT customer_id,
           MIN(session_id) AS first_order_session_id
    FROM df_preview
    WHERE event_type = 'placed_order'
    GROUP BY customer_id
),
DurationsBeforeFirstOrder AS (
    SELECT d.customer_id,
           d.session_duration_minutes
    FROM SessionDurations d
    JOIN SessionWithOrder s ON d.customer_id = s.customer_id
    WHERE d.session_id < s.first_order_session_id
)
SELECT 
    PERCENTILE_CONT(0.5) WITHIN GROUP(ORDER BY session_duration_minutes) AS median_duration_before_order
FROM DurationsBeforeFirstOrder;
""")
    median_duration_before_order = cursor.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        "median_visits_before_order": median_sessions_before_order,
        "median_session_duration_minutes_before_order": median_duration_before_order
    })

if __name__ == '__main__':
    app.run(debug=True)


# COMMAND ----------

dbutils.notebook.exit("Success")
