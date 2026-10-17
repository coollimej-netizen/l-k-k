import os
import uuid
from datetime import datetime
from flask import Flask, jsonify, render_template_string, request
from supabase import Client, create_client

app = Flask(__name__)

# Supabase URL 및 키 설정
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Render 외부 URL 자동 인식
RENDER_EXTERNAL_URL = os.environ.get(
    "RENDER_EXTERNAL_URL", "http://localhost:5000"
)


# 메인 화면: 로그인/회원가입 및 판매자 링크 생성 대시보드
@app.route("/", methods=["GET"])
def index():
    return render_template_string(
        """
        <!DOCTYPE html>
        <html lang="ko">
        <head>
            <meta charset="UTF-8">
            <title>포인트 송금 및 링크 시스템</title>
            <style>
                body { font-family: 'Malgun Gothic', sans-serif; background: #f4f7f6; margin: 0; padding: 40px; display: flex; justify-content: center; }
                .container { width: 100%; max-width: 500px; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
                h2 { color: #333; text-align: center; margin-bottom: 20px; }
                .section { margin-bottom: 25px; padding: 20px; background: #fafafa; border-radius: 8px; border: 1px solid #eee; }
                label { display: block; margin-bottom: 8px; font-weight: bold; color: #555; }
                input { width: 100%; padding: 10px; margin-bottom: 12px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; }
                button { width: 100%; padding: 12px; background: #4CAF50; color: white; border: none; border-radius: 6px; font-size: 16px; font-weight: bold; cursor: pointer; }
                button:hover { background: #45a049; }
                .result { margin-top: 15px; padding: 12px; background: #e8f5e9; border: 1px solid #c8e6c9; border-radius: 6px; word-break: break-all; font-size: 14px; display: none; }
            </style>
        </head>
        <body>
            <div class="container">
                <h2>💳 포인트 송금 시스템</h2>
                
                <!-- 1. 로그인 / 계정 등록 -->
                <div class="section">
                    <h3>1. 계정 등록 (로그인/가입)</h3>
                    <label>사용자 이름 (Username)</label>
                    <input type="text" id="username" placeholder="사용할 이름을 입력하세요">
                    <button onclick="registerUser()">계정 생성 및 UID 받기</button>
                    <div id="regResult" class="result"></div>
                </div>

                <!-- 2. 판매자 링크 생성 -->
                <div class="section">
                    <h3>2. 판매자 송금 링크 생성</h3>
                    <label>내(송금자) UID</label>
                    <input type="text" id="senderUid" placeholder="내 UUID 입력">
                    <label>상대방(수신자) UID</label>
                    <input type="text" id="receiverUid" placeholder="상대방 UUID 입력">
                    <label>송금 금액 (원)</label>
                    <input type="number" id="amount" placeholder="금액 입력">
                    <button onclick="createLink()" style="background: #2196F3;">링크 생성하기</button>
                    <div id="linkResult" class="result"></div>
                </div>
            </div>

            <script>
                async function registerUser() {
                    const username = document.getElementById('username').value;
                    if(!username) { alert('이름을 입력하세요.'); return; }
                    
                    const res = await fetch('/api/register', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({username: username, points: 5000})
                    });
                    const data = await res.json();
                    const resDiv = document.getElementById('regResult');
                    resDiv.style.display = 'block';
                    if(data.success) {
                        const uid = data.data[0].id;
                        resDiv.innerHTML = `<b>생성 완료!</b><br>내 UID: <span style="color:red;">${uid}</span><br>(이 UID를 복사해서 아래에 사용하세요)`;
                        document.getElementById('senderUid').value = uid;
                    } else {
                        resDiv.innerHTML = `오류: ${data.error}`;
                    }
                }

                async function createLink() {
                    const sender_uid = document.getElementById('senderUid').value;
                    const receiver_uid = document.getElementById('receiverUid').value;
                    const amount = document.getElementById('amount').value;

                    if(!sender_uid || !receiver_uid || !amount) { alert('모든 정보를 입력하세요.'); return; }

                    const res = await fetch('/api/send', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({sender_uid, receiver_uid, amount})
                    });
                    const data = await res.json();
                    const linkDiv = document.getElementById('linkResult');
                    linkDiv.style.display = 'block';
                    if(data.success) {
                        linkDiv.innerHTML = `<b>링크 생성 성공!</b><br>결제번호: ${data.payment_code}<br><a href="${data.claim_link}" target="_blank">${data.claim_link}</a>`;
                    } else {
                        linkDiv.innerHTML = `오류: ${data.error}`;
                    }
                }
            </script>
        </body>
        </html>
    ''', external_url=RENDER_EXTERNAL_URL)


# 1. 사용자 등록 API
@app.route("/api/register", methods=["POST"])
def register_user():
    data = request.json
    username = data.get("username")
    initial_points = data.get("points", 5000)

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

        # 잔액 차감
        supabase.table("users").update({"points": current_points - amount}).eq(
            "id", sender_uid
        ).execute()

        # 결제번호 생성
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

        # 송금 링크 생성
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


# 3. 링크 접속 시 포인트 수령 및 확인증 출력
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

        # 수신자 포인트 증가
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

        # 상태 변경
        supabase.table("transactions").update({"status": "COMPLETED"}).eq(
            "payment_code", payment_code
        ).execute()

        # 송금 확인증 렌더링
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
