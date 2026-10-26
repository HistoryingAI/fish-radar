# 託管路線：定案（2026-10-26）

這一頁取代舊的第 9 節。舊的第 9 節有兩條結論是**錯的**，照著做會白忙一晚。

---

## 一句話

**Vercel 整條路都封死了，不是域名的問題，是 IP。** 走 **D：自定義域名 + Cloudflare Pages**。
域名 `fishradar.vip` 已買（阿里雲，2026-10-26），今晚 1 小時能通。

---

## 一、舊第 9 節錯在哪（兩條）

### ① 「被牆的是 `*.vercel.app` 泛域名，自己的域名指過去就行」——錯

同一個 IP，**大陸出口被切、境外出口正常**，這叫 IP 級封鎖。換什麼域名指向它都一樣：

| 目標 IP | 直連（大陸線路） | 走代理（境外出口） |
|---|---|---|
| `76.76.21.21` | ECONNRESET 314ms | **TLS OK、HTTP 200、server: Vercel** |
| `216.198.79.1` | ECONNRESET 279ms | **TLS OK、HTTP 200、server: Vercel** |
| `76.76.21.61`（www 的 CNAME 目標） | ECONNRESET 1436ms | — |
| `66.33.60.130`（同上） | ECONNRESET 1454ms | — |
| `76.76.21.9` | ECONNRESET 1397ms | — |

而且**換 SNI 也一樣**——拿 `baidu.com` 當 SNI 去連 `76.76.21.21`，照樣被切。
所以不是「認得 vercel 這幾個字」，是整段 IP 被處理掉了。

**推論**：`fishradar.vip` 的 A 記錄指到 Vercel → DNS 解析會成功 → TCP 握手會成功 →
**TLS 在 0.3 秒被切斷** → 用戶看到「轉圈然後失敗」。比現在的 21 秒超時好不到哪去。

> 這條推論如果有人不信，可以自己驗：同一個 IP 直連掛、開代理通，就是被牆。

### ② 「反例 `蓝色大肥鱼.com` 在 Cloudflare 後面」——錯

實測：`server: Caddy`、**沒有 `cf-ray` 標頭**、Let's Encrypt 證書、
IP `104.247.81.99`、TTFB 273ms。它是**自建的 Caddy 伺服器**（大概香港 VPS），不是 Cloudflare。
（現在對 `/` 回 **410 Gone** 而且是空的——站主可能自己關了，不影響「連得通」這個結論。）

所以它證明的是「**自有域名 + 境外自建伺服器**可行」——那是方案 C，
不是「Cloudflare 可行」。（Cloudflare 可行是另一組證據，見下。）

---

## 二、實測：大陸直連到底哪些能用（2026-10-26 20:20）

| 目標 | 結果 | TTFB |
|---|---|---|
| `www.baidu.com`（基線） | 200 | **57ms** |
| `www.cloudflare.com` | 200，cf-ray 落在 **LAX** | 1065ms |
| `developers.cloudflare.com` | 200 | 596ms |
| `pages.dev` | 301 | 910ms |
| `github.io`（GitHub Pages） | 301 | 502ms |
| `www.netlify.com` | 200 | 1021ms |
| `raw.githubusercontent.com` | **ECONNRESET** | 封 |
| `*.vercel.app` | **DNS 污染**（回 31.13.67.33 / 69.171.247.71 / 174.36.196.242） | 20 秒超時 |

兩個要記住的點：

- **Cloudflare 能連**，但回源 PoP 是**洛杉磯（LAX）不是香港**，所以是「能開，但不快」。
- `*.vercel.app` 是 **DNS 污染 + IP 封鎖**，兩層都中。

---

## 三、四個選項重新評分

| 選項 | 原估 | 實測後 | 判定 |
|---|---|---|---|
| **A** 維持 Vercel | 0 元 | 大陸 0%（污染 + IP 封鎖） | **死路，必須搬** |
| **D** 域名 + Cloudflare Pages | ¥60 / 1 小時 | CF 直連 0.6–1.1 秒，可行 | ✅ **今晚做這個** |
| **C** 香港 VPS + 域名 | ¥300 / 1 天 | 參照 273ms，最快 | 兩週後再看要不要 |
| **B** 備案 + 國內託管 | ¥60 / 2–3 週 | 30–50ms，最快最穩 | **不建議先做**，見下 |

### B 有一個舊文件沒寫的風險

本站 703 條裡有 **59 條是 GitHub 連結**，而整個站的價值就是「連回境外原帖」。
可是備案網站「鏈接境外平台」正是第一批被要求整改的項目——`DEPLOY.md` 第 167 行自己寫過。

所以 B 不是「花三週就一勞永逸」，很可能是「花三週，然後被要求把 GitHub 那一欄砍掉」。
本站的內容結構天生跟備案審核不合。**等真的有人用了再說。**

---

## 四、為什麼是 D，而且順序不能反

1. **域名已經買了**（沉沒成本已付）——而它是 B / C / D 三個方案的共同前提，先買不會錯。
2. Cloudflare Pages 免費、接 GitHub、**push 即部署**，跟你現在的 Vercel 流程一模一樣，行為不用改。
3. 1 小時能驗證；不行再換後端，**域名不用重買**。
4. 兩週後如果發現大家真的在用、而且嫌慢 → 同一個域名的 A 記錄指到香港 VPS（C），半小時的事。

**買域名在阿里雲是對的**：境外註冊商（Cloudflare Registrar、Namecheap）註冊的域名
**不能直接備案**，要轉入境內服務商才行（[騰訊雲備案文檔](https://cloud.tencent.com.cn/document/product/243/18905)）。
`.vip` 在工信部批覆後綴之列，B 的門還開著——但真要備案前，用
[工信部域名公示](https://domain.miit.gov.cn/) 再確認一次。

---

## 五、今晚的操作順序（有一個坑）

> ⚠️ **坑：域名現在是 `client hold`。**
> RDAP 查到：註冊時間 2026-10-26 09:22，狀態含 `client hold`，
> NS 還是 `dns1/dns2.hichina.com`，`fishradar.vip` 目前 **完全沒有 A 記錄**。
>
> `client hold` 多半是**實名認證還沒過**（新註冊的域名在阿里雲常見）。
> **在認證通過前改 NS，改了也不生效**，Cloudflare 會一直顯示「pending nameserver update」。
> 先去阿里雲控制台看域名狀態是不是「正常」——不是就先做認證（支付寶人臉約 10 分鐘，生效 0–24 小時）；
> 如果顯示已經實名，那可能只是變更還沒同步，等幾小時再看。

1. **阿里雲**：完成域名實名認證，等到狀態「正常」。
2. **Cloudflare**：Add a domain → `fishradar.vip` → 選 Free。
3. **阿里雲**：域名 → 管理 → DNS 修改 → 換成 Cloudflare 給的兩個 NS。
4. **Cloudflare**：Workers & Pages → Create → Pages → Connect to Git → `HistoryingAI/fish-radar`。
   - Build command **留空**，Build output directory 填 **`/`**。

   > 💡 **省 20 分鐘的技巧**：部署完會給你一個 `xxx.pages.dev` 的臨時地址。
   > 網上有人說這地址在大陸也被牆——**實測沒有**，`pages.dev` 直連 301、910ms，能開。
   > 所以**不用等域名生效**，先用手機打開那個 `pages.dev` 地址，
   > 確認網頁、圖片、載入更多都正常。站本身有問題就先修，別把 DNS 和內容問題混在一起查。

5. **Cloudflare**：Custom domains → 加 `fishradar.vip`（再加一次 `www.fishradar.vip`）。
6. 等證書變 Active（5–30 分鐘）。
7. **雙擊 `換網址.bat`**——把 `og:image` / `canonical` 改成 `https://fishradar.vip` 並推上去。
8. 手機**關 Wi-Fi、開 4G**、打開 `https://fishradar.vip/`。再雙擊 `測速.bat` 看數字。

### 有一句話要反過來

網上那份教學說「CNAME 要設成**灰雲**（僅 DNS），橙雲會干擾驗證」——**剛好相反**。

Cloudflare Pages 綁自定義域名時，那條 CNAME **必須是橙雲（已代理）**：
證書是 Cloudflare 邊緣簽的。設成灰雲會直接拿到 `pages.dev` 的證書，
瀏覽器報憑證錯誤（`ERR_CERT_COMMON_NAME_INVALID`）。

灰雲那條建議適用的是「用 Cloudflare 純做 DNS、後端自己管」的情況，不是 Pages。

---

## 六、這次搬遷要動到的檔案（已經準備好）

| 檔案 | 做什麼 |
|---|---|
| `_headers` | Cloudflare 版的 `vercel.json`：`data/` 只快取 5 分鐘，首頁不快取 |
| `.assetsignore` | 別把 `*.py` / `*.bat` / `*.md` / `vendor/` / `logs/` 公開出去 |
| `換網址.bat` | 雙擊改 og:image + canonical 並推送 |
| `測速.bat` / `測速.js` | 直連測速，對照「百度 / 你的網址 / 舊 Vercel」 |

`vercel.json` **留著**，Vercel 部署不用關——境外用戶走 `vercel.app` 比較快，兩個入口各司其職。

---

## 七、風險（誠實版）

- Cloudflare 免費版在大陸**時快時慢**，移動 4G 可能還是要轉幾秒。能開，但不是「秒開」。
- 域名若被舉報，也可能被牆。**只有備案是真正穩的**，這是 D 的代價。
- 所以：先上，**兩週後用真實反饋決定**要不要升 C（快）或 B（穩）。

---

## 八、怎麼重新驗證（以後懷疑的時候）

1. 雙擊 `測速.bat` — 看你的網址是不是 ✅、幾秒。
2. 手機關 Wi-Fi 用 4G 開一次 — 這是唯一有意義的用戶測試。
3. 想看「是不是被牆」→ 同一個 IP，直連掛、開代理通，就是被牆。

---

## 九、目前進度（2026-10-26 21:15）

| 項目 | 狀態 |
|---|---|
| 域名 | `fishradar.vip`，阿里雲註冊，**2027-10-26 到期**（記得開自動續費） |
| 阿里雲狀態 | **`client hold`**（實名認證未完成）→ 公網 `ENOTFOUND` |
| Cloudflare 帳號 | 已建立，`fishradar.vip` **已成功加入**（zone 已在 CF 上生效） |
| Cloudflare 給的 NS | `coraline.ns.cloudflare.com` ／ `milan.ns.cloudflare.com` |
| 阿里雲目前的 NS | 仍是 `dns1.hichina.com` ／ `dns2.hichina.com` ← **還沒改** |
| GitHub | `2e992d2` ← `bb479ef`（含 `_headers`、`.assetsignore`）**還沒推上去** |

**怎麼確認 Cloudflare 那邊真的加好了**：直接問那兩個 NS「有沒有這個 zone」。
兩個都回 SOA 同一個序列號，就代表 zone 建好了：

```
coraline.ns.cloudflare.com → SOA primary=coraline.ns.cloudflare.com  serial=2418506097
milan.ns.cloudflare.com    → SOA primary=coraline.ns.cloudflare.com  serial=2418506097
```

（`108.162.x` / `162.159.x` / `172.64.x` 這三段都是 Cloudflare 自己的 NS 網段，不是假冒。）

**接下來**：推送 → 等實名短信 → 阿里雲改 NS → CF Pages 連倉庫 → 綁域名 → `換網址.bat` → 手機 4G 驗。
