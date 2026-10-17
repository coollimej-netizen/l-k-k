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


# 1. 메인 화면 (로그인 화면 및 링크 생성 대시보드 통합)
@app.route("/", methods=["GET"])
def index():
    html_content = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>전단지 코드 포인트 결제 및 링크 생성기</title>
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
            .error { background: #ffebee; border-color: #ffcdd2; color: #c62828; }
            #dashboard { display: none; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>전단지 포인트 결제 시스템</h2>
            
            <!-- 로그인 화면 -->
            <div id="loginSection" class="section">
                <h3>관리자 로그인</h3>
                <label>아이디 (ID)</label>
                <input type="text" id="adminId" placeholder="admin 입력">
                <label>비밀번호 (Password)</label>
                <input type="password" id="adminPw" placeholder="admin 입력">
                <button onclick="loginAdmin()">로그인</button>
                <div id="loginError" class="result error" style="display:none;">아이디 또는 비밀번호가 틀렸습니다.</div>
            </div>

            <!-- 링크 생성 대시보드 (로그인 후 표시) -->
            <div id="dashboard">
                <div class="section" style="background: #e8f5e9; text-align: center; font-weight: bold; color: #2e7d32;">
                    관리자 접속 성공 <span style="font-size:12px; color:#666; display:block; margin-top:5px;">(링크 생성기 모드)</span>
                </div>
                
                <div class="section">
                    <h3>전단지 송금 링크 생성</h3>
                    <label>판매자 UID</label>
                    <input type="text" id="sellerUid" placeholder="판매자 UID 입력">
                    
                    <label>전단지 코드 (Code)</label>
                    <input type="text" id="flyerCode" placeholder="예: FLYER-2026-01">
                    
                    <label>결제 금액 (원)</label>
                    <input type="number" id="amount" placeholder="금액 입력">
                    
                    <button onclick="createLink()" style="background: #2196F3;">링크 생성하기</button>
                    <div id="linkResult" class="result"></div>
                </div>
            </div>
        </div>

        <script>
            function loginAdmin() {
                const id = document.getElementById('adminId').value;
                const pw = document.getElementById('adminPw').value;
                
                if(id === 'admin' && pw === 'admin') {
                    document.getElementById('loginSection').style.display = 'none';
                    document.getElementById('dashboard').style.display = 'block';
                } else {
                    document.getElementById('loginError').style.display = 'block';
                }
            }

            async function createLink() {
                const seller_uid = document.getElementById('sellerUid').value;
                const flyer_code = document.getElementById('flyerCode').value;
                const amount = document.getElementById('amount').value;

                if(!seller_uid || !flyer_code || !amount) { 
                    alert('모든 정보를 입력해주세요.'); 
                    return; 
                }

                const res = await fetch('/api/create-link', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({seller_uid, flyer_code, amount})
                });
                const data = await res.json();
                const linkDiv = document.getElementById('linkResult');
                linkDiv.style.display = 'block';
                
                if(data.success) {
                    linkDiv.className = 'result';
                    linkDiv.innerHTML = '<b>링크 생성 성공!</b><br>코드: ' + data.flyer_code + '<br><a href="' + data.claim_link + '" target="_blank">' + data.claim_link + '</a>';
                } else {
                    linkDiv.className = 'result error';
                    linkDiv.innerHTML = '오류: ' + data.error;
                }
            }
        </script>
    </body>
    </html>
    """
    return render_template_string(html_content)


# 2. 전단지 코드 기반 링크 생성 API (관리자 전용)
@app.route("/api/create-link", methods=["POST"])
def create_link():
    data = request.json
    seller_uid = data.get("seller_uid")
    flyer_code = data.get("flyer_code")
    amount = int(data.get("amount", 0))

    if not seller_uid or not flyer_code or amount <= 0:
        return jsonify({"error": "잘못된 입력 데이터입니다."}), 400

    try:
        # 중복 코드 확인
        existing = (
            supabase.table("transactions")
            .select("*")
            .eq("payment_code", flyer_code)
            .execute()
        )
        if existing.data:
            return jsonify({"error": "이미 존재하는 전단지 코드입니다."}), 400

        # 거래 내역에 대기 상태로 등록 (송금자 UID 대신 판매자 UID를 sender 또는 receiver로 유연하게 처리)
        supabase.table("transactions").insert(
            {
                "payment_code": flyer_code,
                "sender_uid": seller_uid,  # 판매자 UID
                "receiver_uid": seller_uid,  # 임시 매칭
                "amount": amount,
                "status": "PENDING",
            }
        ).execute()

        claim_link = f"{RENDER_EXTERNAL_URL}/claim?code={flyer_code}"

        return jsonify(
            {
                "success": True,
                "flyer_code": flyer_code,
                "claim_link": claim_link,
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 3. 링크 접속 시 누구나 UID를 입력해 결제/수령하는 화면
@app.route("/claim", methods=["GET", "POST"])
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
            return "존재하지 않거나 만료된 전단지 코드입니다.", 404

        tx = tx_res.data[0]
        if tx["status"] == "COMPLETED":
            return render_template_string(
                """
                <div style="font-family: Arial; padding: 40px; text-align: center;">
                    <h2 style="color: #d32f2f;">이미 사용 완료된 전단지 코드입니다.</h2>
                    <p>코드: <b>{{ code }}</b></p>
                </div>
            """,
                code=payment_code,
            )

        # POST 요청 시 (사용자가 자신의 UID를 입력하고 결제 요청할 때)
        if request.method == "POST":
            buyer_uid = request.form.get("buyer_uid")
            if not buyer_uid:
                return "UID를 입력해주세요.", 400

            amount = tx["amount"]

            # 구매자(결제자) 포인트 차감 또는 검증 로직 수행 가능
            # 여기서는 전단지 코드를 통한 포인트 적립/결제 처리를 반영합니다.
            supabase.table("transactions").update(
                {"status": "COMPLETED", "receiver_uid": buyer_uid}
            ).eq("payment_code", payment_code).execute()

            receipt_html = """
            <div style="font-family: Arial; padding: 30px; max-width: 450px; margin: 40px auto; border: 2px solid #4CAF50; border-radius: 12px; background: #f9f9f9;">
                <h2 style="color: #2e7d32; text-align: center;">&#127881; 포인트 결제 완료 확인증</h2>
                <hr style="border: 0; border-top: 1px solid #ddd;">
                <p><b>전단지 코드:</b> {{ code }}</p>
                <p><b>결제 금액:</b> {{ amount }} 원</p>
                <p><b>결제자 UID:</b> {{ buyer_uid }}</p>
                <p><b>처리일시:</b> {{ date }}</p>
                <hr style="border: 0; border-top: 1px solid #ddd;">
                <p style="color: #555; font-size: 13px; text-align: center;">정상적으로 결제 처리되었습니다.</p>
            </div>
            """
            return render_template_string(
                receipt_html,
                code=payment_code,
                amount=amount,
                buyer_uid=buyer_uid,
                date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )

        # GET 요청 시: 사용자 UID 입력 폼 제공
        claim_form_html = """
        <!DOCTYPE html>
        <html lang="ko">
        <head>
            <meta charset="UTF-8">
            <title>포인트 결제 확인</title>
            <style>
                body { font-family: 'Malgun Gothic', sans-serif; background: #f4f7f6; margin: 0; padding: 40px; display: flex; justify-content: center; }
                .container { width: 100%; max-width: 400px; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); text-align: center; }
                input { width: 100%; padding: 10px; margin: 15px 0; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; }
                button { width: 100%; padding: 12px; background: #4CAF50; color: white; border: none; border-radius: 6px; font-size: 16px; font-weight: bold; cursor: pointer; }
            </style>
        </head>
        <body>
            <div class="container">
                <h2>전단지 코드 결제</h2>
                <p>코드: <b>{{ code }}</b></p>
                <p>결제 금액: <b>{{ amount }} 원</b></p>
                <form method="POST">
                    <input type="text" name="buyer_uid" placeholder="본인의 UID를 입력하세요" required>
                    <button type="submit">포인트 결제하기</button>
                </form>
            </div>
        </body>
        </html>
        """
        return render_template_string(
            claim_form_html, code=payment_code, amount=tx["amount"]
        )

    except Exception as e:
        return f"처리 중 오류가 발생했습니다: {str(e)}", 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
