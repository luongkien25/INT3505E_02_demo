from flask import Flask, request, jsonify, url_for
from datetime import datetime

app = Flask(__name__)

notifications = []
next_id = 1


def make_notification_links(notif):
    """Tạo HATEOAS links cho notification"""
    notif_id = notif["id"]
    return {
        "self": {
            "href": url_for("get_notification", notif_id=notif_id, _external=True),
            "method": "GET"
        },
        "update": {
            "href": url_for("update_notification", notif_id=notif_id, _external=True), 
            "method": "PATCH"
        },
        "delete": {
            "href": url_for("delete_notification", notif_id=notif_id, _external=True),
            "method": "DELETE"
        },
        "mark_read": {
            "href": url_for("update_notification", notif_id=notif_id, _external=True),
            "method": "PATCH",
            "body": {"read": True}
        }
    }


def notification_with_links(notif):
    """Thêm _links vào notification"""
    result = dict(notif)
    result["_links"] = make_notification_links(notif)
    return result


# ------------------------------
# HÀM TIỆN ÍCH TẠO HYPERMEDIA
# ------------------------------

def make_notification_links(notif):
    """
    Tạo danh sách các link (HATEOAS) cho một notification cụ thể.
    """
    notif_id = notif["id"]
    return {
        "self": {
            "href": url_for("get_notification", notif_id=notif_id, _external=True),
            "method": "GET"
        },
        "update": {
            "href": url_for("update_notification", notif_id=notif_id, _external=True),
            "method": "PATCH"
        },
        "delete": {
            "href": url_for("delete_notification", notif_id=notif_id, _external=True),
            "method": "DELETE"
        },
        "mark_read": {
            "href": url_for("update_notification", notif_id=notif_id, _external=True),
            "method": "PATCH",
            # Gợi ý body cho client (không bắt buộc nhưng giúp API tự mô tả hơn)
            "body": {"read": True}
        }
    }


def notification_with_links(notif):
    """
    Gắn thêm trường _links vào một notification.
    """
    result = dict(notif)  # copy để tránh sửa trực tiếp object gốc
    result["_links"] = make_notification_links(notif)
    return result


def make_collection_links(page, page_size, total):
    """
    Tạo các link phân trang cho danh sách notifications.
    """
    links = {
        "self": {
            "href": url_for("list_notifications", page=page, page_size=page_size, _external=True),
            "method": "GET"
        }
    }

    # Tính toán trang trước / sau
    if page > 1:
        links["prev"] = {
            "href": url_for("list_notifications", page=page - 1, page_size=page_size, _external=True),
            "method": "GET"
        }

    max_page = (total + page_size - 1) // page_size if page_size > 0 else 1
    if page < max_page:
        links["next"] = {
            "href": url_for("list_notifications", page=page + 1, page_size=page_size, _external=True),
            "method": "GET"
        }

    # Link tạo mới notification
    links["create"] = {
        "href": url_for("create_notification", _external=True),
        "method": "POST",
        "body": {
            "user_id": 1,
            "message": "Nội dung thông báo"
        }
    }

    return links


# ------------------------------
# API ROOT – ĐIỂM KHỞI ĐẦU
# ------------------------------

@app.route("/", methods=["GET"])
def api_root():
    """
    Endpoint gốc giúp client khám phá API thông qua hypermedia.
    """
    return jsonify({
        "message": "Notification API with HATEOAS demo",
        "_links": {
            "self": {
                "href": url_for("api_root", _external=True),
                "method": "GET"
            },
            "notifications": {
                "href": url_for("list_notifications", _external=True),
                "method": "GET"
            },
            "create_notification": {
                "href": url_for("create_notification", _external=True),
                "method": "POST"
            }
        }
    })


# ------------------------------
# CRUD + QUERY VỚI HATEOAS
# ------------------------------

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

    # HATEOAS: trả về resource kèm các link hành động
    return jsonify(notification_with_links(notif)), 201


@app.route("/notifications", methods=["GET"])
def list_notifications():
    """
    Liệt kê danh sách notifications với filter + phân trang.
    Có kèm hypermedia (HATEOAS) cho collection và từng item.
    """
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
        "_links": make_collection_links(page, page_size, total),
        "data": [notification_with_links(n) for n in data]
    })


@app.route("/notifications/<int:notif_id>", methods=["GET"])
def get_notification(notif_id):
    """
    Đọc 1 notification theo id.
    Trả về resource kèm link (HATEOAS).
    """
    notif = next((n for n in notifications if n["id"] == notif_id), None)
    if notif is None:
        return jsonify({"error": "Không tìm thấy notification"}), 404
    return jsonify(notification_with_links(notif))


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

    return jsonify(notification_with_links(notif))


@app.route("/notifications/<int:notif_id>", methods=["DELETE"])
def delete_notification(notif_id):
    """
    Xoá notification theo id.
    Không trả body, nhưng trong slide bạn có thể lưu ý:
    - Trước khi xoá, client có thể gọi GET để lấy link 'delete' từ HATEOAS.
    """
    index = next((i for i, n in enumerate(notifications) if n["id"] == notif_id), None)
    if index is None:
        return jsonify({"error": "Không tìm thấy notification"}), 404

    notifications.pop(index)
    return "", 204


if __name__ == "__main__":
    print("Starting Flask server on http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000, debug=True)
