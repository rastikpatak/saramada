#!/usr/bin/env python3

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.parse import urlparse, parse_qs
from urllib.error import HTTPError, URLError

from datetime import datetime
import json
import sqlite3

HOST = "0.0.0.0"
PORT = 8000

DB_NAME = "sensors.db"


# ------------------------
# DATABASE
# ------------------------

def init_db():

    conn = sqlite3.connect(DB_NAME)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS saved_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sensor_type TEXT,
            data TEXT,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()


def save_to_db(sensor_type, data):

    conn = sqlite3.connect(DB_NAME)

    conn.execute(
        "INSERT INTO saved_data (sensor_type, data, created_at) VALUES (?, ?, ?)",
        (
            sensor_type,
            json.dumps(data),
            datetime.now().isoformat()
        )
    )

    conn.commit()
    conn.close()


def get_saved_data():

    conn = sqlite3.connect(DB_NAME)

    cursor = conn.execute("""
        SELECT *
        FROM saved_data
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()

    conn.close()

    return rows


# ------------------------
# API FETCH
# ------------------------

def fetch_api(source):

    url = (
        f"https://projekttb.sksnr.sk/data/api.php"
        f"?source={source}&sort=timestamp&dir=desc&limit=1"
    )

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    req = Request(url, headers=headers)

    with urlopen(req) as response:

        data = response.read().decode("utf-8")

        return json.loads(data)


# ------------------------
# SERVER
# ------------------------

class MyServer(BaseHTTPRequestHandler):

    def send_json(self, data, status=200):

        body = json.dumps(data).encode()

        self.send_response(status)

        self.send_header(
            "Content-Type",
            "application/json"
        )

        self.send_header(
            "Access-Control-Allow-Origin",
            "*"
        )

        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, OPTIONS"
        )

        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type"
        )

        self.end_headers()

        self.wfile.write(body)

    # ------------------------

    def do_OPTIONS(self):

        self.send_response(204)

        self.send_header(
            "Access-Control-Allow-Origin",
            "*"
        )

        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, OPTIONS"
        )

        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type"
        )

        self.end_headers()

    # ------------------------

    def do_GET(self):

        parsed = urlparse(self.path)

        path = parsed.path

        query = parse_qs(parsed.query)

        # ------------------------
        # LOAD SENSOR
        # ------------------------

        if path == "/api/latest":

            try:

                source = query.get("source", ["0"])[0]

                data = fetch_api(source)

                self.send_json({
                    "ok": True,
                    "source": source,
                    "data": data
                })

            except HTTPError as e:

                self.send_json({
                    "error": str(e)
                }, 500)

            except URLError as e:

                self.send_json({
                    "error": str(e)
                }, 500)

            except Exception as e:

                self.send_json({
                    "error": str(e)
                }, 500)

            return

        # ------------------------
        # GET SAVED DATA
        # ------------------------

        if path == "/api/saved":

            rows = get_saved_data()

            data = []

            for row in rows:

                data.append({
                    "id": row[0],
                    "sensor_type": row[1],
                    "data": json.loads(row[2]),
                    "created_at": row[3]
                })

            self.send_json(data)

            return

        # ------------------------

        self.send_json({
            "error": "Not found"
        }, 404)

    # ------------------------

    def do_POST(self):

        parsed = urlparse(self.path)

        if parsed.path != "/api/save":

            self.send_json({
                "error": "Not found"
            }, 404)

            return

        try:

            content_length = int(
                self.headers["Content-Length"]
            )

            body = self.rfile.read(
                content_length
            )

            data = json.loads(body)

            sensor_type = data.get("type")

            sensor_data = data.get("data")

            save_to_db(
                sensor_type,
                sensor_data
            )

            self.send_json({
                "saved": True
            })

        except Exception as e:

            self.send_json({
                "error": str(e)
            }, 500)


# ------------------------
# START SERVER
# ------------------------

init_db()

server = ThreadingHTTPServer(
    (HOST, PORT),
    MyServer
)

print(f"SERVER RUNNING:")
print(f"http://localhost:{PORT}")

server.serve_forever()