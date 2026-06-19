import os
from flask import Flask, render_template, request, jsonify
from mssql_python import connect

app = Flask(__name__)

SQL_SERVER = os.getenv("AZURE_SQL_SERVER")
SQL_DATABASE = os.getenv("AZURE_SQL_DATABASE")
RESULTS_PER_PAGE = 10  # Define how many items to show per page

def get_db_connection():
    connection_string = (
        f"Server={SQL_SERVER},1433;"
        f"Database={SQL_DATABASE};"
        f"Authentication=ActiveDirectoryMSI;"
        f"Encrypt=yes;"
        f"TrustServerCertificate=no;"
    )
    return connect(connection_string)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    
    # Safely parse the page number from the query string (defaults to page 1)
    try:
        page = int(request.args.get('page', 1))
        if page < 1: page = 1
    except ValueError:
        page = 1

    if len(query) < 3:
        return jsonify({"results": [], "page": page, "has_more": False})

    # Calculate how many rows to skip
    offset = (page - 1) * RESULTS_PER_PAGE

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # We fetch RESULTS_PER_PAGE + 1 items to easily determine if a "Next" page exists
        sql_query = """
            SELECT ProductName 
            FROM Products 
            WHERE ProductName LIKE ?
            ORDER BY ProductName ASC
            OFFSET ? ROWS
            FETCH NEXT ? ROWS ONLY
        """
        
        like_parameter = f"%{query}%"
        # Fetching 1 extra row beyond RESULTS_PER_PAGE for lookahead lookups
        cursor.execute(sql_query, (like_parameter, offset, RESULTS_PER_PAGE + 1))
        
        rows = cursor.fetchall()
        raw_results = [row[0] for row in rows]
        
        # Check if we found more rows than the page limit
        has_more = len(raw_results) > RESULTS_PER_PAGE
        
        # Truncate the results array back to the expected page limit
        results = raw_results[:RESULTS_PER_PAGE]
        
        return jsonify({
            "results": results,
            "page": page,
            "has_more": has_more
        })
        
    except Exception as e:
        print(f"Database error: {e}")
        return jsonify({"error": "Internal server error"}), 500
        
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    app.run(debug=True)