from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

notifications = []
next_id = 1


@app.route("/notifications", methods=["POST"])
def create_notification():
    """
    Tạo một notification mới.
    Body JSON: { "user_id": 1, "message": "Hello" }
    """
    global next_id

    data = request.get_json() or {}
    user_id = data.get("user_id")
    message = data.get("message")

    if user_id is None or message is None:
        return jsonify({"error": "user_id và message là bắt buộc"}), 400

    notif = {
        "id": next_id,
        "user_id": user_id,
        "message": message,
        "read": False,
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    next_id += 1
    notifications.append(notif)

    return jsonify(notif), 201


@app.route("/notifications", methods=["GET"])
def list_notifications():
    
    user_id = request.args.get("user_id")     
    unread = request.args.get("unread")        
    page = int(request.args.get("page", 1))   
    page_size = int(request.args.get("page_size", 10))  

    result = notifications

    # ----- Filtering -----
    if user_id is not None:
        result = [n for n in result if str(n["user_id"]) == str(user_id)]

    if unread == "true":
        result = [n for n in result if not n["read"]]

    # ----- Pagination -----
    total = len(result)
    start = (page - 1) * page_size
    end = start + page_size
    data = result[start:end]

    return jsonify({
        "page": page,
        "page_size": page_size,
        "total": total,
        "data": data
    })



@app.route("/notifications/<int:notif_id>", methods=["GET"])
def get_notification(notif_id):
    """
    Đọc 1 notification theo id.
    """
    notif = next((n for n in notifications if n["id"] == notif_id), None)
    if notif is None:
        return jsonify({"error": "Không tìm thấy notification"}), 404
    return jsonify(notif)


@app.route("/notifications/<int:notif_id>", methods=["PATCH"])
def update_notification(notif_id):
    """
    Cập nhật 1 phần notification.
    Body JSON có thể chứa: { "message": "...", "read": true }
    """
    notif = next((n for n in notifications if n["id"] == notif_id), None)
    if notif is None:
        return jsonify({"error": "Không tìm thấy notification"}), 404

    data = request.get_json() or {}
    if "message" in data:
        notif["message"] = data["message"]
    if "read" in data:
        notif["read"] = bool(data["read"])

    return jsonify(notif)


@app.route("/notifications/<int:notif_id>", methods=["DELETE"])
def delete_notification(notif_id):
    """
    Xoá notification theo id.
    """
    index = next((i for i, n in enumerate(notifications) if n["id"] == notif_id), None)
    if index is None:
        return jsonify({"error": "Không tìm thấy notification"}), 404

    notifications.pop(index)
    return "", 204


if __name__ == "__main__":
    print("Starting Flask server on http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000, debug=True)
