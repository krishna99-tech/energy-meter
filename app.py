
from flask import Flask, render_template, jsonify, request, send_file, Response, stream_with_context
import sqlite3
from datetime import datetime
import csv
import io
from openpyxl import Workbook
import json
import time
import threading
import socket


# ================= APP CONFIG =================
app = Flask(__name__)
DB_PATH = "energy.db"
UDP_PORT = 8501
webport = 8502
UDP_DEBUG = True

# ================= SAFE FLOAT CONVERTER =================
def to_float(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def get_any(data, *keys):
    for k in keys:
        if k in data:
            return data.get(k)
    return None


def as_dashboard_row_upper(row):
    raw = dict(row) if row else {}
    return {
        "ENERGY": raw.get("energy"),
        "POWER": raw.get("power"),
        "POWER_FACTOR": raw.get("power_factor"),
        "FREQUENCY": raw.get("frequency"),
        "VR": raw.get("vr"),
        "VY": raw.get("vy"),
        "VB": raw.get("vb"),
        "RY": raw.get("ry"),
        "YB": raw.get("yb"),
        "BR": raw.get("br"),
        "IR": raw.get("ir"),
        "IY": raw.get("iy"),
        "IB": raw.get("ib"),
        "SHIFT": raw.get("shift"),
        "TIMESTAMP": raw.get("timestamp"),
    }


CSV_EXPORT_COLUMNS = [
    "ENERGY", "POWER_FACTOR", "FREQUENCY",
    "VR", "VY", "VB", "RY", "YB", "BR",
    "IR", "IY", "IB", "SHIFT", "TIMESTAMP"
]


def as_csv_row_upper(row):
    raw = dict(row) if row else {}
    return {
        "ENERGY": get_any(raw, "ENERGY", "energy"),
        "POWER_FACTOR": get_any(raw, "POWER_FACTOR", "power_factor"),
        "FREQUENCY": get_any(raw, "FREQUENCY", "frequency"),
        "VR": get_any(raw, "VR", "vr"),
        "VY": get_any(raw, "VY", "vy"),
        "VB": get_any(raw, "VB", "vb"),
        "RY": get_any(raw, "RY", "ry"),
        "YB": get_any(raw, "YB", "yb", "BY", "by"),
        "BR": get_any(raw, "BR", "br", "RB", "rb"),
        "IR": get_any(raw, "IR", "ir"),
        "IY": get_any(raw, "IY", "iy"),
        "IB": get_any(raw, "IB", "ib"),
        "SHIFT": get_any(raw, "SHIFT", "shift"),
        "TIMESTAMP": get_any(raw, "TIMESTAMP", "timestamp"),
    }

# ================= DB MANAGEMENT =================
def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def insert_energy_row(data):
    now = datetime.now()
    shift = get_shift_from_time(now)
    with get_db_connection() as conn:
        conn.execute("""
            INSERT INTO energy_data (
                energy,
                power,
                power_factor,
                frequency,
                vr, vy, vb,
                ry, yb, br,
                ir, iy, ib,
                shift,
                timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            to_float(data.get("energy")),        # kWh (from meter)
            to_float(data.get("power")),         # kW (from meter)
            to_float(data.get("power_factor")),
            to_float(data.get("frequency")),

            to_float(data.get("vr")),
            to_float(data.get("vy")),
            to_float(data.get("vb")),

            to_float(get_any(data, "ry", "vry", "v_ry")),
            to_float(get_any(data, "yb", "vyb", "v_yb")),
            to_float(get_any(data, "br", "vbr", "v_br")),

            to_float(data.get("ir")),
            to_float(data.get("iy")),
            to_float(data.get("ib")),

            shift,
            now.strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
    return shift


def start_udp_listener():
    def _run():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0", UDP_PORT))
        if UDP_DEBUG:
            print(f"[UDP] Listening on 0.0.0.0:{UDP_PORT}")
        while True:
            try:
                data, addr = sock.recvfrom(4096)
                raw_text = data.decode("utf-8", errors="replace").strip()
                if UDP_DEBUG:
                    print(f"[UDP] Packet from {addr[0]}:{addr[1]} | bytes={len(data)}")
                    print(f"[UDP] Raw: {raw_text}")

                payload = json.loads(raw_text)
                if UDP_DEBUG:
                    print(f"[UDP] Parsed: {payload}")

                shift = insert_energy_row(payload)
                if UDP_DEBUG:
                    print(f"[UDP] Inserted row successfully (shift={shift})")
            except Exception as e:
                if UDP_DEBUG:
                    print(f"[UDP] Error: {e}")
                # Ignore malformed packets to keep listener alive
                continue
    t = threading.Thread(target=_run, daemon=True)
    t.start()


def ensure_columns(conn, columns):
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(energy_data)")}
    for name, col_def in columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE energy_data ADD COLUMN {name} {col_def}")


def init_db():
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS energy_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                -- Meter values (direct from MFM384)
                energy REAL,          -- cumulative kWh
                power REAL,           -- total active power kW
                power_factor REAL,
                frequency REAL,

                -- Phase voltages (Line-Neutral)
                vr REAL, vy REAL, vb REAL,

                -- Line-Line voltages
                ry REAL, yb REAL, br REAL,

                -- Phase currents
                ir REAL, iy REAL, ib REAL,

                -- Metadata
                shift TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        ensure_columns(conn, {
            "ry": "REAL",
            "yb": "REAL",
            "br": "REAL",
        })
        conn.commit()


init_db()

# ================= SHIFT UTILITY =================
def get_shift_from_time(dt):
    hour = dt.hour
    if 6 <= hour < 14:
        return "A"
    elif 14 <= hour < 22:
        return "B"
    else:
        return "C"

# ================= ROUTES =================
@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/gauges")
def gauges():
    return render_template("gauges.html")

@app.route("/trends")
def trends():
    return render_template("trends.html")


@app.route("/api/data")
def api_data():
    """Latest record for dashboard"""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM energy_data ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
    return jsonify(as_dashboard_row_upper(row)) if row else jsonify({})


@app.route("/api/raw")
def api_raw():
    shift = request.args.get("shift", "ALL")
    start = request.args.get("start_date")
    end = request.args.get("end_date")
    try:
        limit = int(request.args.get("limit", 500))
    except (TypeError, ValueError):
        limit = 500
    limit = max(1, min(limit, 10000))

    columns = [
        "energy",
        "power",
        "power_factor",
        "frequency",
        "vr", "vy", "vb",
        "ry", "yb", "br",
        "ir", "iy", "ib",
        "shift",
        "timestamp",
    ]

    query = f"SELECT {', '.join(columns)} FROM energy_data"
    params = []
    where = []

    if start and end:
        where.append("DATE(timestamp) BETWEEN ? AND ?")
        params.extend([start, end])

    if shift != "ALL":
        where.append("shift = ?")
        params.append(shift)

    if where:
        query += " WHERE " + " AND ".join(where)

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    with get_db_connection() as conn:
        rows = conn.execute(query, params).fetchall()

    return jsonify([as_dashboard_row_upper(r) for r in rows])


@app.route("/api/latest")
def api_latest():
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM energy_data ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
    return jsonify(as_dashboard_row_upper(row)) if row else jsonify({})


@app.route("/api/stream")
def api_stream():
    shift_filter = request.args.get("shift", "ALL")
    start = request.args.get("start_date")
    end = request.args.get("end_date")

    start_dt = None
    end_dt = None
    try:
        if start:
            start_dt = datetime.strptime(start, "%Y-%m-%d")
        if end:
            end_dt = datetime.strptime(end, "%Y-%m-%d")
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
    except ValueError:
        start_dt = None
        end_dt = None

    def event_stream():
        last_ts = None
        while True:
            with get_db_connection() as conn:
                row = conn.execute(
                    "SELECT * FROM energy_data ORDER BY timestamp DESC LIMIT 1"
                ).fetchone()
            if row:
                data = dict(row)
                ts = data.get("timestamp")
                if ts and ts != last_ts:
                    last_ts = ts
                    if shift_filter != "ALL" and data.get("shift") != shift_filter:
                        time.sleep(1)
                        continue
                    if start_dt or end_dt:
                        try:
                            row_dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                            if start_dt and row_dt < start_dt:
                                time.sleep(1)
                                continue
                            if end_dt and row_dt > end_dt:
                                time.sleep(1)
                                continue
                        except ValueError:
                            pass
                    dashboard_row = as_dashboard_row_upper(data)
                    yield f"data: {json.dumps(dashboard_row)}\n\n"
            time.sleep(1)
    return Response(stream_with_context(event_stream()), mimetype="text/event-stream")


# ================= INGEST FROM ESP32 =================
# UDP-only ingest; HTTP endpoint removed by design.


# ================= TREND CHART API =================
@app.route("/api/raw/export")
def api_raw_export():
    shift = request.args.get("shift", "ALL")
    start = request.args.get("start_date")
    end = request.args.get("end_date")
    try:
        limit = int(request.args.get("limit", 10000))
    except (TypeError, ValueError):
        limit = 10000
    limit = max(1, min(limit, 10000))

    columns = [
        "energy", "power_factor", "frequency",
        "vr", "vy", "vb", "ry", "yb", "br",
        "ir", "iy", "ib", "shift", "timestamp"
    ]
    query = f"SELECT {', '.join(columns)} FROM energy_data"
    params = []
    where = []
    if start and end:
        where.append("DATE(timestamp) BETWEEN ? AND ?")
        params.extend([start, end])
    if shift != "ALL":
        where.append("shift = ?")
        params.append(shift)
    if where:
        query += " WHERE " + " AND ".join(where)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    with get_db_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    if not rows:
        return jsonify({"error": "No data"}), 404
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_EXPORT_COLUMNS)
    writer.writeheader()
    writer.writerows([as_csv_row_upper(r) for r in rows])
    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name="energy_data.csv"
    )


@app.route("/api/trend/<string:trend_type>", methods=["POST"])
def api_trend(trend_type):
    req = request.get_json(silent=True) or {}
    shift = req.get("shift", "ALL")
    start = req.get("start_date")
    end = req.get("end_date")

    if not start or not end:
        return jsonify({"ok": False, "error": "Missing date range"}), 400

    trend_type = trend_type.lower().strip()

    if trend_type == "voltage":
        columns = ["timestamp", "vr", "vy", "vb"]
    elif trend_type == "current":
        columns = ["timestamp", "ir", "iy", "ib"]
    elif trend_type == "power":
        columns = ["timestamp", "power"]
    else:
        return jsonify({"ok": False, "error": "Invalid trend type"}), 400

    query = f"""
        SELECT {', '.join(columns)}
        FROM energy_data
        WHERE DATE(timestamp) BETWEEN ? AND ?
    """
    params = [start, end]

    if shift != "ALL":
        query += " AND shift = ?"
        params.append(shift)

    query += " ORDER BY timestamp ASC"

    with get_db_connection() as conn:
        rows = conn.execute(query, params).fetchall()

    return jsonify({
        "ok": True,
        "data": [dict(r) for r in rows]
    })


# ================= EXPORT HELPERS =================
def fetch_filtered(req_data):
    req_data = req_data or {}
    shift = req_data.get("shift", "ALL")
    start = req_data.get("start_date")
    end = req_data.get("end_date")

    # Export order: voltage/current in R, Y, B order and no internal id
    columns = [
        "energy",
        "power_factor",
        "frequency",
        "vr", "vy", "vb",
        "ry", "yb", "br",
        "ir", "iy", "ib",
        "shift",
        "timestamp",
    ]

    if not start or not end:
        return []

    query = f"SELECT {', '.join(columns)} FROM energy_data WHERE DATE(timestamp) BETWEEN ? AND ?"
    params = [start, end]

    if shift != "ALL":
        query += " AND shift = ?"
        params.append(shift)

    query += " ORDER BY timestamp DESC"

    with get_db_connection() as conn:
        rows = conn.execute(query, params).fetchall()

    # Preserve column order in output
    return [{col: row[col] for col in columns} for row in rows]


@app.route("/api/export/preview", methods=["POST"])
def export_preview():
    data = fetch_filtered(request.get_json(silent=True))
    return jsonify({
        "data": data[:50],
        "total_records": len(data)
    })


@app.route("/api/export/csv", methods=["POST"])
def export_csv():
    req = request.get_json(silent=True) or {}
    # If 'data' is present and is a list, export that directly
    if isinstance(req.get("data"), list) and req["data"]:
        data = req["data"]
    else:
        data = fetch_filtered(req)
    if not data:
        return jsonify({"error": "No data"}), 404

    csv_rows = [as_csv_row_upper(r) for r in data]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_EXPORT_COLUMNS)
    writer.writeheader()
    writer.writerows(csv_rows)

    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name="energy_report.csv"
    )


@app.route("/api/export/excel", methods=["POST"])
def export_excel():
    data = fetch_filtered(request.get_json(silent=True))
    if not data:
        return jsonify({"error": "No data"}), 404

    wb = Workbook()
    ws = wb.active
    ws.append([k.upper() for k in data[0].keys()])

    for row in data:
        ws.append(list(row.values()))

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="energy_report.xlsx"
    )


# ================= MAIN =================
if __name__ == "__main__":
    start_udp_listener()
    
    app.run(
        host="0.0.0.0",
        port=webport,
        debug=True,
        use_reloader=False
    )



