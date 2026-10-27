# 部署上線（GitHub + Vercel）

一次設定，之後每次更新只要「跑一次、推一次」，Vercel 自己重新部署。

```
本機 collect.py  →  git push  →  Vercel 自動建置（約 30 秒）  →  網址更新
```

---

## 你會得到什麼

- 一個 `https://你的專案名.vercel.app` 的網址（免費、不用買域名）
- 手機、群裡、電腦都能開
- 每次推新數據，30 秒後自動生效，不用手動上傳

**不會得到**：大陸一定能打開（見最後一節）。

---

## 一次性設定

### ① 裝 Git（約 5 分鐘）

下載 <https://git-scm.com/download/win>，一路按「下一步」就好。
裝完之後，**把電腦整個重開機**（不然新視窗才認得 `git` 這個指令）。

### ② 建一個空的 GitHub 倉庫

1. 打開 <https://github.com/new>
2. Repository name 填 `fish-radar`
3. 選 **Public**（Vercel 免費版要公開倉庫）
4. **不要**勾「Add a README file」「Add .gitignore」——空著就好
5. 按 Create repository，把頁面上那串 `https://github.com/你的帳號/fish-radar.git` 記下來

### ③ 把專案推上去

在 `fish-radar` 資料夾裡打開終端機（資料夾空白處右鍵 → Open Git Bash here），貼這五行：

```bash
git init -b main
git add .
git commit -m "first deploy"
git remote add origin https://github.com/你的帳號/fish-radar.git
git push -u origin main
```

第一次 push 會跳出視窗要你登入 GitHub，照著點就好。

> ⚠️ 一定要在 **fish-radar 這個資料夾裡**執行。在外層的 `default-workspace` 執行會把
> `ai-film-radar` 和別的專案一起推上去。

### ④ 接上 Vercel

1. <https://vercel.com> → Continue with GitHub
2. Add New… → Project → 選 `fish-radar` → Import
3. 設定全部留預設（Framework Preset 選 **Other**，Build Command 留空，Output Directory 留空）
4. Deploy

30 秒後你會拿到網址，長得像 `https://fish-radar-xxxx.vercel.app`。

### ⑤ 把網址寫進分享卡（不然發到群裡是白板）

```bash
python set_og.py https://fish-radar-xxxx.vercel.app
```

然後再 `git add . && git commit -m "og" && git push` 一次。

---

## 以後每次更新

```bash
# 1. 抓新數據（也可以直接雙擊 更新數據.bat）
python collect.py

# 2. 推上去
git add data/
git commit -m "data: 2026-10-25"
git push
```

或者直接雙擊 **`發布.bat`**（它會幫你做完第 2 步）。

30 秒後刷新網頁就是新的。

---

## 出問題怎麼看

| 症狀 | 原因 | 怎麼辦 |
|---|---|---|
| 網頁打開是 404 | Vercel 的 Output Directory 被填了東西 | 改成留空 |
| 頁面還是舊數據 | 部署有延遲 + 瀏覽器緩存 | 等 30 秒，Ctrl+F5 |
| `git push` 被拒絕 | 沒登入、或遠端有別的提交 | 重新 push，會彈登入視窗 |
| `git` 不是指令 | 裝完沒重開機 / 沒加進 PATH | 重開機；還不行就重裝並勾選 PATH |
| `Recv failure: Connection was reset` | Git 沒走代理，直連 github.com 被重置 | 見下面「代理」一節 |
| `schannel: SEC_E_NO_CREDENTIALS` | 拿不到 Windows 憑證（常見於沙箱／受限帳號） | 用普通帳號開終端，不要用服務身分跑 |

### 代理（大陸網路必看）

Git **不會讀** Windows 的系統代理，瀏覽器能開不代表 Git 能推。這個倉庫已經在 `.git/config` 裡配好：

```
http.proxy  = http://127.0.0.1:7897
https.proxy = http://127.0.0.1:7897
```

`7897` 是 Clash Verge 的預設端口。**換了代理軟體或改了端口，要跟著改這裡**，
否則 push 會卡住或報 `Connection was reset`。

改的方法（在 `fish-radar` 資料夾裡）：

```bash
git config http.proxy http://127.0.0.1:新端口
git config https.proxy http://127.0.0.1:新端口
```

> ⚠️ 配了代理之後，**代理軟體沒開就推不上去**。要臨時直連，先 `git config --unset http.proxy`。
> 怎麼查自己的端口：Windows「設定 → 網路和網際網路 → Proxy」，或看代理軟體的設定頁。
| 手機能開、電腦不能 | 見下一節 | |

---

## 關於大陸訪問（重要）

`*.vercel.app` 在大陸**經常打不開或很慢**，這不是你的站壞了，是域名本身。

上線後先做一件事：**找 3–5 個不同運營商的朋友（移動／聯通／電信各一兩個）點一下**，
記下誰打不開。如果比例很高，再考慮換國內方案（騰訊雲 COS／阿里雲 OSS 靜態託管），
那個不用翻牆，但要實名 + 備案，個人備案大概 2–3 週。

---

## GitHub 為什麼不放公開頁（2026-10-27 起）

先講清楚一件事，因為很容易搞混：

| 東西 | 在大陸 | 對本站的影響 |
|---|---|---|
| `github.com` 的倉庫頁 | **多數能開，但慢、時好時壞** | 卡片上的 GitHub 連結會偶爾失效 |
| `raw.githubusercontent.com`、`*.github.io` | 幾乎不可用 | 我們沒用到 |
| X / 推特 | **完全打不開** | 本站從沒接入，沒有死鏈 |
| `*.vercel.app` | 被 IP 級封鎖 | 影響的是**整個站**，不是單條連結 |

所以「GitHub 能不能放」是**要不要留一排大概率打不開的連結**的問題。
決定是：**不放。** 公開頁只有 B 站。

### 現在的狀態（已經設好了，不用再改）

`config.json`：

```json
"hide_platforms": ["github"],
```

改完要跑一次：

```bash
python split_posts.py
```

它會做四件事：

1. 把 GitHub 的條目從 `posts_top.js` / `posts_rest.js` 拿掉（頁面上就沒有那排連結了）
2. `meta.total` 改成屏蔽後的數字（644，不是 703）
3. 連 `meta.platforms` 裡沒接入過的紅書／推特／小黑盒也一併清掉
4. 另外生一份 **`data/github_local.js`**，給本機的 `本機-GitHub.html` 看

**不用重新抓數據。** 數據本身還在 `posts.json` 裡（59 條 GitHub 都在），
想恢復公開顯示，把那一行改回 `[]` 再 split 一次就好。

### 本機那一頁

`本機-GitHub.html` 雙擊就能開，讀 `data/github_local.js`，列表可以搜尋。
它帶 `noindex`，而且 `build.sh` 不會把它放進 `dist/`——所以 **Cloudflare 上沒有這一頁**。
更新方式跟看板一樣：雙擊 `更新數據.bat` 就會順手刷新。

如果你之後在國內備案，這一條基本上必須做——鏈接境外平台是備案站被要求整改的第一批項目。
這件事現在已經做完了。

---

## 倉庫裡什麼會被推上去

```
推：index.html  method.html  data/  assets/  promos.js  og-cover.jpg
    collect.py  config.json  seeds.txt  等腳本（留著方便換電腦）
不推：__pycache__  *.tmp  _dryrun/  _t/   （.gitignore 已經擋掉）
```

`data/` 一定要推——它就是網站顯示的內容。
