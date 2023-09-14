# Databricks notebook source
# MAGIC %run /Users/makramamor2026@gmail.com/Xccelerated/2.assignment_sessionize

# COMMAND ----------

# MAGIC %md #### 1. SQL Queries for Metrics
# MAGIC
# MAGIC ** Median number of sessions before purchase: **
# MAGIC
# MAGIC * We'd be counting the number of sessions before the session with a purchase.

# COMMAND ----------

# MAGIC %sql 
# MAGIC
# MAGIC WITH SessionWithOrder AS (
# MAGIC     SELECT customer_id,
# MAGIC            MIN(session_id) AS first_order_session_id
# MAGIC     FROM df_preview
# MAGIC     WHERE event_type = 'placed_order'
# MAGIC     GROUP BY customer_id
# MAGIC ),
# MAGIC SessionsBeforeFirstOrder AS (
# MAGIC     SELECT d.customer_id,
# MAGIC            COUNT(DISTINCT d.session_id) AS sessions_before_order
# MAGIC     FROM df_preview d
# MAGIC     JOIN SessionWithOrder s ON d.customer_id = s.customer_id
# MAGIC     WHERE d.session_id < s.first_order_session_id
# MAGIC     GROUP BY d.customer_id
# MAGIC )
# MAGIC SELECT 
# MAGIC     PERCENTILE_CONT(0.5) WITHIN GROUP(ORDER BY sessions_before_order) AS median_sessions_before_order
# MAGIC FROM SessionsBeforeFirstOrder;
# MAGIC

# COMMAND ----------

# MAGIC %md #### Median session duration before a purchase:
# MAGIC We will compute the duration of each session and then find the median duration of sessions before the first purchase.

# COMMAND ----------

# MAGIC %sql 
# MAGIC
# MAGIC WITH SessionDurations AS (
# MAGIC     SELECT customer_id,
# MAGIC            session_id,
# MAGIC            MAX(timestamp) - MIN(timestamp) AS session_duration_minutes
# MAGIC     FROM df_preview
# MAGIC     GROUP BY customer_id, session_id
# MAGIC ),
# MAGIC SessionWithOrder AS (
# MAGIC     SELECT customer_id,
# MAGIC            MIN(session_id) AS first_order_session_id
# MAGIC     FROM df_preview
# MAGIC     WHERE event_type = 'placed_order'
# MAGIC     GROUP BY customer_id
# MAGIC ),
# MAGIC DurationsBeforeFirstOrder AS (
# MAGIC     SELECT d.customer_id,
# MAGIC            d.session_duration_minutes
# MAGIC     FROM SessionDurations d
# MAGIC     JOIN SessionWithOrder s ON d.customer_id = s.customer_id
# MAGIC     WHERE d.session_id < s.first_order_session_id
# MAGIC )
# MAGIC SELECT 
# MAGIC     PERCENTILE_CONT(0.5) WITHIN GROUP(ORDER BY session_duration_minutes) AS median_duration_before_order
# MAGIC FROM DurationsBeforeFirstOrder;
# MAGIC

# COMMAND ----------

# MAGIC %md #### 2. Setting up the API Endpoint with Flask:

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
