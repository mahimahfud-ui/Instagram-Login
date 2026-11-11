from flask import Flask, render_template_string
import random

app = Flask(__name__)

# ================= Login Page HTML (Instagram UI) =================
LOGIN_PAGE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Instagram UI Demo</title>
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
    display: block;
    width: 100%;
    margin-top: 12px;
    padding: 12px 12px;
    background: #0095f6;
    color: #fff;
    border: none;
    border-radius: 24px;
    font-size: 15px;
    font-weight: 600;
    line-height: 1.35;
    text-align: center;
    text-decoration: none;
    cursor: pointer;
}

.demo-notice {
    margin: 0 auto 18px;
    padding: 12px 14px;
    border: 1px solid #f0c36d;
    border-radius: 10px;
    background: #fff8e8;
    color: #684b13;
    font-size: 12px;
    line-height: 1.5;
    text-align: left;
}

.demo-open {
    margin-top: 12px;
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
            <img src="https://upload.wikimedia.org/wikipedia/commons/a/a5/Instagram_icon.png" alt="Instagram-inspired demo icon">
        </div>

        <div class="demo-notice" role="note">
            UNOFFICIAL DEMO — This page is not Instagram or Meta. No real account sign-in is available. Do not enter account credentials.
        </div>

        <a class="login-btn demo-open" href="/dashboard">Open demo dashboard</a>
        <div class="forgot">Sample activity only · No Instagram account is connected</div>
    </div>

    <div class="bottom">
        <div class="meta">
            <span>Demo</span>
            <span>Preview</span>
        </div>

        <div class="footer">
            Unofficial interface demonstration · Not affiliated with Instagram or Meta
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
<title>Activity Dashboard Demo</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
<style>
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
    font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
}

html {
    min-height: 100%;
}

body {
    min-height: 100vh;
    min-height: 100svh;
    display: flex;
    flex-direction: column;
    overflow-x: hidden;
    background: #f5f5f7;
    color: #333;
}

.header {
    width: 100%;
    min-height: clamp(82px, 14vh, 120px);
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 12px 16px;
    background: linear-gradient(180deg, #fff 0%, #e9ecef 100%);
}

.insta-logo {
    font-size: clamp(34px, 7vw, 48px);
    font-weight: bold;
    font-family: "Billabong", cursive;
    background: linear-gradient(45deg, #f58529, #dd2a7b, #8134af, #515bd4);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-align: center;
}

.demo-banner {
    width: 100%;
    padding: 9px 14px;
    background: #fff8e8;
    border-top: 1px solid #f0d69b;
    border-bottom: 1px solid #f0d69b;
    color: #684b13;
    font-size: 12px;
    line-height: 1.4;
    text-align: center;
}

.top-nav {
    width: 100%;
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 4px;
    padding: 12px 8px;
    background: #fff;
    border-bottom: 1px solid #ddd;
    text-align: center;
}

.nav-item {
    min-width: 0;
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 5px;
    padding: 2px 4px;
    color: #444;
    font-size: 13px;
    font-weight: 600;
    line-height: 1.25;
    overflow-wrap: anywhere;
}

.nav-item i {
    color: #222;
    font-size: 20px;
}

.badge {
    position: absolute;
    top: -5px;
    right: 18%;
    padding: 2px 5px;
    border: 2px solid #fff;
    border-radius: 10px;
    background: #ff4757;
    color: #fff;
    font-size: 10px;
    line-height: 1.2;
}

.dashboard-main {
    width: 100%;
    max-width: 780px;
    flex: 1 0 auto;
    margin: 14px auto 18px;
    padding: 0 16px;
}

.list-container {
    width: 100%;
    margin: 0;
    overflow: hidden;
    border-radius: 12px;
    background: #fff;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
}

.list-item {
    display: flex;
    align-items: center;
    gap: 10px;
    min-height: 58px;
    padding: 13px 16px;
    border-bottom: 1px solid #f1f1f1;
    transition: background 0.2s;
}

.list-item:last-child {
    border-bottom: none;
}

.list-item:active {
    background: #f0f0f0;
}

.icon-box {
    position: relative;
    display: flex;
    flex: 0 0 35px;
    align-items: center;
    justify-content: center;
    font-size: 18px;
}

.item-text {
    flex: 1 1 auto;
    min-width: 0;
    font-size: 15px;
    font-weight: 500;
    line-height: 1.35;
    overflow-wrap: anywhere;
}

.count {
    flex: 0 0 auto;
    margin-left: auto;
    color: #555;
    font-weight: bold;
    white-space: nowrap;
}

.arrow {
    flex: 0 0 auto;
    color: #ccc;
    font-size: 14px;
}

.trusted-footer {
    width: 100%;
    margin-top: auto;
    padding: 10px 14px calc(10px + env(safe-area-inset-bottom));
    background: #fff;
    color: #555;
    box-shadow: 0 -1px 5px rgba(0, 0, 0, 0.05);
    font-size: 12px;
    line-height: 1.4;
    text-align: center;
}

@media (max-width: 480px) {
    .top-nav {
        padding: 10px 5px;
    }

    .nav-item {
        font-size: 11px;
    }

    .nav-item i {
        font-size: 18px;
    }

    .dashboard-main {
        margin-top: 12px;
        padding: 0 12px;
    }

    .list-item {
        gap: 8px;
        min-height: 54px;
        padding: 11px 12px;
    }

    .icon-box {
        flex-basis: 28px;
        font-size: 16px;
    }

    .item-text {
        font-size: 14px;
    }

    .count {
        font-size: 13px;
    }
}

@media (max-height: 620px) {
    .header {
        min-height: 76px;
    }

    .list-item {
        min-height: 50px;
        padding-top: 9px;
        padding-bottom: 9px;
    }
}
</style>
</head>
<body>

<div class="header">
    <div class="insta-logo">Instagram</div>
</div>

<div class="demo-banner" role="status">
    DEMO PREVIEW · Sample activity only · Not connected to Instagram or Meta
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

<main class="dashboard-main">
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
</main>

<div class="trusted-footer">
    Demo interface · Sample statistics only · Not affiliated with Instagram or Meta
</div>

</body>
</html>
"""

# ================= Flask Routes =================
@app.route("/")
def index():
    return render_template_string(LOGIN_PAGE_HTML)


@app.route("/dashboard")
def dashboard():
    # All figures are synthetic demo values; no account data is requested or accessed.
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
