import os
import uuid
from datetime import datetime
from flask import Flask, jsonify, render_template_string, request
from supabase import Client, create_client

app = Flask(__name__)

# Supabase URL 및 키 직접 설정 (에러 원천 차단)
# 환경 변수에서 가져오기 (GitHub에 키가 노출되지 않음)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Render 외부 URL 자동 인식
RENDER_EXTERNAL_URL = os.environ.get(
    "RENDER_EXTERNAL_URL", "http://localhost:5000"
)


@app.route("/")
def index():
    return "포인트 송금 및 링크 시스템 서버가 정상 작동 중입니다."


# 1. 사용자 등록 API
@app.route("/api/register", methods=["POST"])
def register_user():
    data = request.json
    username = data.get("username")
    initial_points = data.get("points", 1000)

    if not username:
        return jsonify({"error": "사용자 이름을 입력해주세요."}), 400

    try:
        res = (
            supabase.table("users")
            .insert({"username": username, "points": initial_points})
            .execute()
        )
        return jsonify({"success": True, "data": res.data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 2. 포인트 송금 요청 및 링크 생성 API
@app.route("/api/send", methods=["POST"])
def send_points():
    data = request.json
    sender_uid = data.get("sender_uid")
    receiver_uid = data.get("receiver_uid")
    amount = int(data.get("amount", 0))

    if not sender_uid or not receiver_uid or amount <= 0:
        return jsonify({"error": "잘못된 요청 데이터입니다."}), 400

    try:
        # 송금자 잔액 확인
        sender_res = (
            supabase.table("users")
            .select("points")
            .eq("id", sender_uid)
            .execute()
        )
        if not sender_res.data:
            return jsonify({"error": "송금자 정보를 찾을 수 없습니다."}), 404

        current_points = sender_res.data[0]["points"]
        if current_points < amount:
            return jsonify({"error": "잔액이 부족합니다."}), 400

        # 송금자 잔액 차감
        supabase.table("users").update({"points": current_points - amount}).eq(
            "id", sender_uid
        ).execute()

        # 고유 결제번호 생성
        payment_code = f"TX-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        # 거래 내역 저장
        supabase.table("transactions").insert(
            {
                "payment_code": payment_code,
                "sender_uid": sender_uid,
                "receiver_uid": receiver_uid,
                "amount": amount,
                "status": "PENDING",
            }
        ).execute()

        # 송금 수령 링크 생성
        claim_link = f"{RENDER_EXTERNAL_URL}/claim?code={payment_code}"

        return jsonify(
            {
                "success": True,
                "payment_code": payment_code,
                "claim_link": claim_link,
                "message": "송금 링크가 생성되었습니다.",
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 3. 링크 접속 시 포인트 수령 및 송금 확인증 출력
@app.route("/claim", methods=["GET"])
def claim_points():
    payment_code = request.args.get("code")
    if not payment_code:
        return "잘못된 접근입니다.", 400

    try:
        tx_res = (
            supabase.table("transactions")
            .select("*")
            .eq("payment_code", payment_code)
            .execute()
        )
        if not tx_res.data:
            return "존재하지 않거나 만료된 송금 링크입니다.", 404

        tx = tx_res.data[0]
        if tx["status"] == "COMPLETED":
            return render_template_string(
                """
                <div style="font-family: Arial; padding: 40px; text-align: center;">
                    <h2 style="color: #d32f2f;">이미 수령 완료된 송금 링크입니다.</h2>
                    <p>결제번호: <b>{{ code }}</b></p>
                </div>
            """,
                code=payment_code,
            )

        receiver_uid = tx["receiver_uid"]
        amount = tx["amount"]

        # 수신자 포인트 조회 및 증가
        user_res = (
            supabase.table("users")
            .select("points")
            .eq("id", receiver_uid)
            .execute()
        )
        if not user_res.data:
            return "수신자 계정을 찾을 수 없습니다.", 404

        new_points = user_res.data[0]["points"] + amount
        supabase.table("users").update({"points": new_points}).eq(
            "id", receiver_uid
        ).execute()

        # 거래 상태 완료로 변경
        supabase.table("transactions").update({"status": "COMPLETED"}).eq(
            "payment_code", payment_code
        ).execute()

        # 송금 확인증 렌더링 (금액, 결제번호, 결제일 포함)
        return render_template_string(
            """
            <div style="font-family: Arial; padding: 30px; max-width: 450px; margin: 40px auto; border: 2px solid #4CAF50; border-radius: 12px; background: #f9f9f9;">
                <h2 style="color: #2e7d32; text-align: center;">🎉 포인트 송금 완료 확인증</h2>
                <hr style="border: 0; border-top: 1px solid #ddd;">
                <p><b>결제번호:</b> {{ code }}</p>
                <p><b>송금 금액:</b> {{ amount }} 원</p>
                <p><b>결제일시:</b> {{ date }}</p>
                <hr style="border: 0; border-top: 1px solid #ddd;">
                <p style="color: #555; font-size: 13px; text-align: center;">포인트가 성공적으로 지급되었습니다.</p>
            </div>
        """,
            code=payment_code,
            amount=amount,
            date=tx["created_at"],
        )

    except Exception as e:
        return f"처리 중 오류가 발생했습니다: {str(e)}", 500


# 4. 사용자별 거래 내역 조회 API
@app.route("/api/history/<uid>", methods=["GET"])
def get_history(uid):
    try:
        sent = (
            supabase.table("transactions")
            .select("*")
            .eq("sender_uid", uid)
            .execute()
        )
        received = (
            supabase.table("transactions")
            .select("*")
            .eq("receiver_uid", uid)
            .execute()
        )
        return jsonify(
            {"success": True, "sent": sent.data, "received": received.data}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
