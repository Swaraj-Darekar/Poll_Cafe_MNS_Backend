import urllib.request, json
def get_stats():
    res = urllib.request.urlopen('http://localhost:8000/superadmin/stats')
    return json.loads(res.read())

def test():
    try:
        s1 = get_stats()
        w1 = s1['wallet_balance']
        print(f"Initial Wallet: {w1}")

        # 1. Test Takeaway (Should NOT deduct)
        url = 'http://localhost:8000/takeaway/pay'
        data = json.dumps({'total_amount': 50, 'payment_method': 'cash'}).encode()
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req)
        
        s2 = get_stats()
        w2 = s2['wallet_balance']
        print(f"Wallet after Takeaway: {w2} (Diff: {w2-w1})")

        # 2. Test Table Session (Should deduct)
        url_start = 'http://localhost:8000/start-table'
        data_start = json.dumps({'table_id': 1, 'customer_name': 'Test User', 'customer_phone': '1234567890'}).encode()
        req_start = urllib.request.Request(url_start, data_start, headers={'Content-Type': 'application/json'})
        session = json.loads(urllib.request.urlopen(req_start).read())
        sid = session['id']

        url_pay = f'http://localhost:8000/{sid}/pay'
        data_pay = json.dumps({'total_amount': 100, 'gross_amount': 100, 'commission_amount': 5, 'duration_minutes': 60, 'payment_method': 'cash'}).encode()
        req_pay = urllib.request.Request(url_pay, data_pay, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req_pay)
        
        s3 = get_stats()
        w3 = s3['wallet_balance']
        print(f"Wallet after Table: {w3} (Diff: {w3-w2})")

        if w1 == w2 and w3 < w2:
            print("VERIFICATION SUCCESSFUL!")
        else:
            print("VERIFICATION FAILED!")
            
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == '__main__':
    test()
