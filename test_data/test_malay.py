import json, sys, urllib.request, mimetypes, os, uuid

# Helper to upload files and run analysis
def analyze(instruction, file_paths):
    boundary = uuid.uuid4().hex
    lines = []
    # Add instruction field
    lines.append(f"--{boundary}".encode())
    lines.append(b'Content-Disposition: form-data; name="instruction"')
    lines.append(b"")
    lines.append(instruction.encode())
    # Add files
    for fp in file_paths:
        fn = os.path.basename(fp)
        with open(fp, "rb") as f:
            data = f.read()
        lines.append(f"--{boundary}".encode())
        lines.append(f'Content-Disposition: form-data; name="files"; filename="{fn}"'.encode())
        lines.append(f"Content-Type: {mimetypes.guess_type(fn)[0] or 'application/octet-stream'}".encode())
        lines.append(b"")
        lines.append(data)
    lines.append(f"--{boundary}--".encode())
    lines.append(b"")
    body = b"\r\n".join(lines)
    req = urllib.request.Request(
        "http://localhost:5000/api/analyze",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())

base = r"C:\Users\HP\WorkBuddy AI\2026-10-10-15-52-22\richbuddy\test_data"
files = [os.path.join(base, "invois_melayu.csv"), os.path.join(base, "transaksi_melayu.csv")]

tests = [
    ("Analisa keseluruhan perniagaan saya", "Overall Performance (Malay)"),
    ("Bandingkan prestasi setiap kawasan", "Regional Comparison (Malay)"),
    ("Produk mana yang untung dan rugi?", "Profit/Loss Products (Malay)"),
]

for instruction, label in tests:
    print(f"\n{'='*60}")
    print(f"TEST: {label}")
    print(f"Instruction: {instruction}")
    print(f"{'='*60}")
    try:
        data = analyze(instruction, files)
        print(f"Intent: {data.get('intent','?')}, Confidence: {data.get('confidence','?')}")
        print(f"Matched keywords: {data.get('matched_keywords',[])}")
        print(f"Description: {data.get('description','?')}")
        dq = data.get("findings",{}).get("data_quality",{})
        print(f"Data Quality: {dq.get('score',0)}/100 (Grade {dq.get('grade','?')})")
        si = data.get("smart_insights",[])
        print(f"Smart Insights: {len(si)}")
        for ins in si:
            print(f"  [{ins.get('priority','?')}] {ins.get('title','?')} ({ins.get('category','?')})")
        reg = data.get("findings",{}).get("regional_analysis",{})
        if reg:
            print("Regional Analysis: FOUND")
            for r in reg.get("by_region",[]):
                print(f"  {r.get('region','?')}: Rev RM{r.get('total_revenue',0)}, Exp RM{r.get('total_expenses',0)}, Net RM{r.get('net_profit',0)}")
        else:
            print("Regional Analysis: None")
        pbc = data.get("findings",{}).get("profit_by_category",{})
        if pbc:
            print("Profit by Category (top 3):")
            for p in pbc.get("categories",[])[:3]:
                print(f"  {p.get('category','?')}: Rev RM{p.get('revenue',0)}, Profit RM{p.get('profit',0)}, Margin {p.get('margin_pct',0)}%")
        ps = data.get("pipeline_steps",[])
        print("Pipeline:")
        for s in ps:
            print(f"  Step {s['step']}: {s['name']} - {s.get('detail','')}")
        print(f"CSVs: {len(data.get('csv_downloads',[]))} files")
        print(f"Report: {data.get('report_download','None')}")
    except Exception as e:
        print(f"ERROR: {e}")
