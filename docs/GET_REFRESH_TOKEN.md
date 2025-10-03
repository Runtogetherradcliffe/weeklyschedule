# One-time: get a Strava refresh token (no ongoing login required)

1) Create a Strava API app (https://www.strava.com/settings/api). Note the **Client ID** and **Client Secret**.
2) Authorize your account once to get a short-lived `code` (replace YOUR_CLIENT_ID and redirect with your own):
```
https://www.strava.com/oauth/authorize?client_id=YOUR_CLIENT_ID&response_type=code&redirect_uri=http://localhost/exchange_token&approval_prompt=auto&scope=read,read_all
```
After you approve, Strava will redirect to your URL with `?code=XXXX`.

3) Exchange the `code` for tokens (the response includes a **refresh_token**):
```bash
curl -X POST https://www.strava.com/oauth/token   -d client_id=YOUR_CLIENT_ID   -d client_secret=YOUR_CLIENT_SECRET   -d code=THE_CODE_YOU_GOT   -d grant_type=authorization_code
```
4) In your GitHub repo → **Settings → Secrets and variables → Actions**, add:
- `STRAVA_CLIENT_ID`
- `STRAVA_CLIENT_SECRET`
- `STRAVA_REFRESH_TOKEN`  (from the curl step)

That’s it. The GitHub Action can now refresh an access token **without you logging in** each time and fetch routes on a schedule.
