import requests
from bs4 import BeautifulSoup

# url = "https://hk.finance.yahoo.com/quote/TLT/history/?period1=1116374400&period2=1747526400"
# url= "https://hk.finance.yahoo.com/quote/SPY/history/?period1=1116374400&period2=1747556014"
url = "https://hk.finance.yahoo.com/quote/SHY/history/?period1=1116374400&period2=1747556692"
headers = {"User-Agent": "Mozilla/5.0"}

resp = requests.get(url, headers=headers)
soup = BeautifulSoup(resp.text, "html.parser")

# 用一條 Selector 抓到 <div class="table-container yf-1jecxey"> 底下那張 table 的 tbody
tbody = soup.select_one(
    "div.table-container.yf-1jecxey "
    "> table.table.yf-1jecxey.noDl.hideOnPrint "
    "> tbody"
)

# 確認拿到了
print(tbody)           # 如果不是 None，就代表成功定位到
print(len(tbody))      # 內部節點數量，通常是多個 <tr>

# 接下來就可以拿 tr
for tr in tbody.select("tr.yf-1jecxey"):
    cols = [td.get_text(strip=True) for td in tr.select("td")]
    with open("ishare1_3.csv", "a", encoding="UTF-8") as f:
            f.write(f"{cols}" + "\n")

print("Done")
