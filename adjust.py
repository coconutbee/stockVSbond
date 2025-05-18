import csv

name = "spy"
input_path  = f"{name}.csv"
output_path = f"{name}_c.csv"

# 用 dict 暂存每个日期的数据
# 结构： { date_str: {"price": ..., "dividend": ...} }
data_map = {}

# 读取输入，将价格和红利分别存入 data_map
with open(input_path, "r", newline="", encoding="utf-8") as fin:
    reader = csv.reader(fin)
    for parts in reader:
        # 清理字段左右的方括号
        date = parts[0].lstrip("[").rstrip("]")
        if len(parts) > 5:
            price = parts[5]
            entry = data_map.setdefault(date, {})
            entry["price"] = price
        elif len(parts) == 2:
            dividend = parts[1].lstrip("[").rstrip("]")
            entry = data_map.setdefault(date, {})
            entry["dividend"] = dividend.replace("股息", "")

# 写入输出：一次性写入日期 + price + dividend
with open(output_path, "w", newline="", encoding="utf-8") as fout:
    writer = csv.writer(fout)
    # 写表头
    writer.writerow(["Date", "Price", "Dividend"])

    for date, entry in sorted(data_map.items()):
        price    = entry.get("price", "")
        dividend = entry.get("dividend", "")
        writer.writerow([date, price, dividend])

print("Done")
