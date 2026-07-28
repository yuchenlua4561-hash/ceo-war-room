# CEO 戰情室

正式版單頁市場儀表板。前端每 60 分鐘重新取得 `dashboard.json`，支援瀏覽器快取回退、資料新鮮度、風險燈號、列印 / PDF 與手機版。

內容亦包含液冷幫浦監控與競爭對手動態。更新資料時請維護 `liquid_cooling_pumps` 與 `competitors` 陣列，並為每筆情報提供可驗證的官方 `url`。

## 機密資料部署警告

本套件若含公司機密，不可直接發布為公開 GitHub Pages。請使用私有儲存庫，並以身分驗證保護整個正式網址。瀏覽器錯誤回退只使用 `sessionStorage`，關閉分頁後即清除，不將戰情資料長期保存於 `localStorage`。完整控制要求見 `SECURITY.md`，維運責任見 `OPERATIONS.md`。

## 本機預覽

請勿直接雙擊 `index.html`（瀏覽器通常會阻擋本機 JSON 請求）。在資料夾內啟動靜態網站伺服器：

```bash
python -m http.server 8000
```

再開啟 `http://localhost:8000/`。

## 部署

整個資料夾可部署至 GitHub Pages、Cloudflare Pages、Netlify、S3 或公司內部靜態網站。網站根目錄須同時包含 `index.html` 與 `dashboard.json`。

若使用免費 GitHub Pages，網站與儲存庫內容會公開給網際網路上的任何人。請只在確認所有內容皆可公開後啟用。

## 每小時資料更新

`.github/workflows/update-dashboard.yml` 每小時第 5 分鐘執行。請在 GitHub repository secrets 設定：

- `MARKET_API_KEY`
- `NEWS_API_KEY`

`scripts/update_dashboard.py` 是安全的整合骨架：它會驗證必要欄位，但不假裝提供免費即時 LME/ICE 資料；未設定 API 時也不會改寫更新時間。請在 `collect()` 串接已獲授權的資料供應商，並保留每筆資料的 `source`、`source_url`、`as_of`、`price_type` 與 `price_label`。前端只會把有效的 `http` 或 `https` 網址呈現為按鈕；缺少或格式錯誤的網址會顯示「尚無連結」。

> GitHub 排程可能因平台負載而延遲，不保證整點執行。若需要嚴格 SLA，請改用雲端排程器或公司內部工作排程。

## 價格標籤

- `live` / `牌告`：來源當下提供的牌告或即時值
- `delay` / `延遲`：延遲報價
- `close` / `收盤`：前一交易日正式收盤或結算值

範例數字僅為介面示意，不可視為真實即時行情。
