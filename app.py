import os
import uuid
from datetime import datetime
from flask import Flask, jsonify, render_template_string, request
from supabase import Client, create_client

app = Flask(__name__)

# Supabase URL 및 키 설정 (※ Render 환경 변수나 아래에 정확한 값을 확인해주세요)
SUPABASE_URL = os.environ.get("https://ylaopptsqknjlttcvqti.supabase.co")
SUPABASE_KEY = os.environ.get("sb_secret_e1rBcLppys8nZzav1XZilw_c6kZD5UM")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Render 외부 URL 자동 인식
RENDER_EXTERNAL_URL = os.environ.get(
    "RENDER_EXTERNAL_URL", "http://localhost:5000"
)


# 1. 메인 화면 (로그인 및 관리자 대시보드: 링크 생성, 내역 조회, 삭제)
@app.route("/", methods=["GET"])
def index():
    html_content = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>전단지 포인트 결제 관리자 대시보드</title>
        <style>
            body { font-family: 'Malgun Gothic', sans-serif; background: #f4f7f6; margin: 0; padding: 40px; display: flex; justify-content: center; }
            .container { width: 100%; max-width: 600px; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
            h2 { color: #333; text-align: center; margin-bottom: 20px; }
            .section { margin-bottom: 25px; padding: 20px; background: #fafafa; border-radius: 8px; border: 1px solid #eee; }
            label { display: block; margin-bottom: 8px; font-weight: bold; color: #555; }
            input { width: 100%; padding: 10px; margin-bottom: 12px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; }
            button { width: 100%; padding: 12px; background: #4CAF50; color: white; border: none; border-radius: 6px; font-size: 16px; font-weight: bold; cursor: pointer; }
            button:hover { background: #45a049; }
            .result { margin-top: 15px; padding: 12px; background: #e8f5e9; border: 1px solid #c8e6c9; border-radius: 6px; word-break: break-all; font-size: 14px; display: none; }
            .error { background: #ffebee; border-color: #ffcdd2; color: #c62828; }
            #dashboard { display: none; }
            table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }
            th { background-color: #f2f2f2; }
            .del-btn { background: #e53935; padding: 5px 10px; font-size: 12px; }
            .del-btn:hover { background: #c62828; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>전단지 포인트 관리 시스템</h2>
            
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

            <!-- 대시보드 (로그인 후 표시) -->
            <div id="dashboard">
                <div class="section" style="background: #e8f5e9; text-align: center; font-weight: bold; color: #2e7d32;">
                    관리자 모드 활성화됨
                </div>
                
                <!-- 링크 생성 섹션 -->
                <div class="section">
                    <h3>전단지 송금 링크 생성</h3>
                    <label>수익 받을 판매자 UID</label>
                    <input type="text" id="sellerUid" placeholder="판매자 UID 입력">
                    
                    <label>전단지 코드 (Code)</label>
                    <input type="text" id="flyerCode" placeholder="예: FLYER-01">
                    
                    <label>결제 금액 (원)</label>
                    <input type="number" id="amount" placeholder="금액 입력">
                    
                    <button onclick="createLink()" style="background: #2196F3;">링크 생성하기</button>
                    <div id="linkResult" class="result"></div>
                </div>

                <!-- 거래 내역 및 삭제 섹션 -->
                <div class="section">
                    <h3>생성된 링크 및 거래 내역</h3>
                    <button onclick="loadTransactions()" style="background: #607D8B; margin-bottom: 10px;">내역 새로고침</button>
                    <div style="overflow-x:auto;">
                        <table>
                            <thead>
                                <tr>
                                    <th>코드</th>
                                    <th>판매자UID</th>
                                    <th>금액</th>
                                    <th>상태</th>
                                    <th>관리</th>
                                </tr>
                            </thead>
                            <tbody id="txTableBody">
                                <tr><td colspan="5">내역 고침 버튼을 눌러주세요.</td></tr>
                            </tbody>
                        </table>
                    </div>
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
                    loadTransactions();
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
                    loadTransactions();
                } else {
                    linkDiv.className = 'result error';
                    linkDiv.innerHTML = '오류: ' + data.error;
                }
            }

            async function loadTransactions() {
                const res = await fetch('/api/transactions');
                const data = await res.json();
                const tbody = document.getElementById('txTableBody');
                
                if(data.success && data.transactions.length > 0) {
                    let html = '';
                    data.transactions.forEach(tx => {
                        html += `<tr>
                            <td>${tx.payment_code}</td>
                            <td style="font-size:11px;">${tx.sender_uid}</td>
                            <td>${tx.amount}원</td>
                            <td><b>${tx.status}</b></td>
                            <td><button class="del-btn" onclick="deleteTx('${tx.payment_code}')">삭제</button></td>
                        </tr>`;
                    });
                    tbody.innerHTML = html;
                } else {
                    tbody.innerHTML = '<tr><td colspan="5">생성된 내역이 없습니다.</td></tr>';
                }
            }

            async function deleteTx(code) {
                if(!confirm(code + ' 링크를 삭제하시겠습니까?')) return;

                const res = await fetch('/api/delete-link', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({payment_code: code})
                });
                const data = await res.json();
                if(data.success) {
                    alert('삭제되었습니다.');
                    loadTransactions();
                } else {
                    alert('오류: ' + data.error);
                }
            }
        </script>
    </body>
    </html>
    """
    return render_template_string(html_content)


# 2. 링크 생성 API
@app.route("/api/create-link", methods=["POST"])
def create_link():
    data = request.json
    seller_uid = data.get("seller_uid")
    flyer_code = data.get("flyer_code")
    amount = int(data.get("amount", 0))

    if not seller_uid or not flyer_code or amount <= 0:
        return jsonify({"error": "잘못된 입력 데이터입니다."}), 400

    try:
        existing = (
            supabase.table("transactions")
            .select("*")
            .eq("payment_code", flyer_code)
            .execute()
        )
        if existing.data:
            return jsonify({"error": "이미 존재하는 전단지 코드입니다."}), 400

        supabase.table("transactions").insert(
            {
                "payment_code": flyer_code,
                "sender_uid": seller_uid,  # 판매자 UID 저장
                "receiver_uid": "NONE",
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


# 3. 거래 내역 조회 API
@app.route("/api/transactions", methods=["GET"])
def get_transactions():
    try:
        res = (
            supabase.table("transactions")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        return jsonify({"success": True, "transactions": res.data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 4. 링크(전단지 코드) 삭제 API
@app.route("/api/delete-link", methods=["POST"])
def delete_link():
    data = request.json
    payment_code = data.get("payment_code")
    if not payment_code:
        return jsonify({"error": "코드가 필요합니다."}), 400

    try:
        supabase.table("transactions").delete().eq(
            "payment_code", payment_code
        ).execute()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 5. 링크 접속 시 결제 및 판매자 포인트 적립 처리
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

        if request.method == "POST":
            buyer_uid = request.form.get("buyer_uid")
            if not buyer_uid:
                return "UID를 입력해주세요.", 400

            seller_uid = tx["sender_uid"]
            amount = tx["amount"]

            # 판매자 현재 포인트 조회 후 금액 적립
            seller_res = (
                supabase.table("users")
                .select("points")
                .eq("id", seller_uid)
                .execute()
            )
            if not seller_res.data:
                return "판매자 계정을 찾을 수 없습니다.", 404

            current_points = seller_res.data[0]["points"]
            new_points = current_points + amount

            # 판매자 계정 포인트 업데이트
            supabase.table("users").update({"points": new_points}).eq(
                "id", seller_uid
            ).execute()

            # 거래 상태 완료로 변경 및 구매자 UID 기록
            supabase.table("transactions").update(
                {"status": "COMPLETED", "receiver_uid": buyer_uid}
            ).eq("payment_code", payment_code).execute()

            receipt_html = """
            <div style="font-family: Arial; padding: 30px; max-width: 450px; margin: 40px auto; border: 2px solid #4CAF50; border-radius: 12px; background: #f9f9f9;">
                <h2 style="color: #2e7d32; text-align: center;">&#127881; 포인트 결제 및 수익 적립 완료</h2>
                <hr style="border: 0; border-top: 1px solid #ddd;">
                <p><b>전단지 코드:</b> {{ code }}</p>
                <p><b>결제 금액:</b> {{ amount }} 원</p>
                <p><b>판매자 UID:</b> {{ seller_uid }}</p>
                <p><b>결제자 UID:</b> {{ buyer_uid }}</p>
                <hr style="border: 0; border-top: 1px solid #ddd;">
                <p style="color: #555; font-size: 13px; text-align: center;">판매자 계정으로 수익이 정상 적립되었습니다.</p>
            </div>
            """
            return render_template_string(
                receipt_html,
                code=payment_code,
                amount=amount,
                seller_uid=seller_uid,
                buyer_uid=buyer_uid,
            )

        claim_form_html = """
        <!DOCTYPE html>
        <html lang="ko">
        <head>
            <meta charset="UTF-8">
            <title>전단지 코드 결제</title>
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
