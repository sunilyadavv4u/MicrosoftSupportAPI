"""Run after starting API: python tests/smoke_test.py"""
import requests
BASE="http://localhost:8000"
KEY="change-me-local-api-key"
def check(method,path,expected,**kwargs):
    r=requests.request(method,BASE+path,timeout=60,**kwargs)
    print(method,path,r.status_code)
    assert r.status_code==expected,(r.status_code,r.text[:500])
    return r

health=check("GET","/health",200).json()
assert health["total_records"]==964481,health
assert len(health["tables"])==8,health
check("GET","/api/apikey/labor-transaction?page=1&page_size=5",200,headers={"x-api-key":KEY})
check("GET","/api/apikey/kb-article?page=1&page_size=5",200,headers={"x-api-key":KEY})
check("GET","/api/basic/labor-approval?page=1&page_size=2",200,auth=("adf_user","ChangeThis_Basic_123!"))
check("GET","/api/bearer/timesheet-entry?page=1&page_size=2",200,headers={"Authorization":"Bearer change-me-static-bearer-token"})
check("GET","/api/apikey/labor-transaction",401)
token=check("POST","/oauth/token",200,data={
    "grant_type":"client_credentials","client_id":"adf-spn-client",
    "client_secret":"ChangeThis_OAuth_Secret_123!"
}).json()["access_token"]
check("GET","/api/oauth/labor-transaction?page=1&page_size=5",200,headers={"Authorization":f"Bearer {token}"})
check("GET","/api/errors/429",429,headers={"x-api-key":KEY})
print("SMOKE TESTS PASSED")
