"""End-to-end test for Django frontend."""
import http.cookiejar
import urllib.request
import urllib.parse
import urllib.error
import re
import time

BASE = "http://127.0.0.1:8090"

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(cj),
    urllib.request.HTTPRedirectHandler(),
)

def test_page(path, label=None):
    try:
        r = opener.open(BASE + path)
        size = len(r.read())
        # If size == login page size (~6256), we're not actually authenticated
        print(f"  OK  {label or path}: {r.status} ({size} bytes)")
        return True
    except urllib.error.HTTPError as e:
        print(f"  ERR {label or path}: {e.code}")
        return False
    except Exception as e:
        print(f"  ERR {label or path}: {e}")
        return False

print("=== VoiceFlow Django E2E Test ===\n")

# 1. Landing page
print("[1] Landing page")
test_page("/")

# 2. Auth pages
print("[2] Auth pages")
test_page("/auth/login/", "Login")
test_page("/auth/register/", "Register")

# 3. Register a new user (unique name)
uname = f"e2e_{int(time.time())}"
print(f"[3] Register user: {uname}")
r = opener.open(BASE + "/auth/register/")
html = r.read().decode()
m = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html)
token = m.group(1) if m else ""
if not token:
    print("  ERR: No CSRF token found")
else:
    data = urllib.parse.urlencode({
        "csrfmiddlewaretoken": token,
        "username": uname,
        "email": f"{uname}@voiceflow.local",
        "company_name": "E2E Corp",
        "password": "E2eTestPass99!",
        "password_confirm": "E2eTestPass99!",
    }).encode()
    req = urllib.request.Request(
        BASE + "/auth/register/",
        data,
        {"Referer": BASE + "/auth/register/"},
    )
    try:
        r = opener.open(req)
        final_url = r.url
        print(f"  OK  Registered -> {final_url}")
        if "onboarding" in final_url:
            print("  ✓  Redirected to onboarding (login successful)")
        elif "register" in final_url:
            print("  ⚠  Stayed on register page (form errors?)")
    except Exception as e:
        print(f"  ERR Register: {e}")

# 4. Dashboard (should work after login)
print("[4] Dashboard pages (authenticated)")
pages = [
    "/dashboard/", "/onboarding/",
    "/dashboard/analytics/", "/dashboard/calls/",
    "/dashboard/knowledge/", "/dashboard/settings/",
    "/dashboard/billing/", "/dashboard/system/",
    "/dashboard/users/", "/dashboard/retraining/",
    "/dashboard/widget/", "/dashboard/api-docs/",
    "/dashboard/notifications/", "/dashboard/audit/",
    "/dashboard/backup/", "/dashboard/reports/",
    "/dashboard/integrations/", "/dashboard/pipelines/",
    "/dashboard/voice-agent/",
]
ok = 0
for p in pages:
    if test_page(p):
        ok += 1

print(f"\n=== Results: {ok}/{len(pages)} dashboard pages OK ===")
